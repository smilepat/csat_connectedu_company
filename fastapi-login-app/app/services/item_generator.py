# app/services/item_generator.py
import asyncio
import json
import logging
import re
import time
from typing import Any
from pydantic import ValidationError
import inspect

from fastapi import HTTPException  # (현재는 사용 안 하지만, 외부에서 참조할 수 있어 남겨둠)

from app.core import openai_config
from app.core.settings import settings
from app.prompts.prompt_manager import PromptManager
from app.prompts.prompt_data import ITEM_PROMPTS

# 레거시(MCQ) 폴백용 스키마
from app.schemas.items_mcq import MCQItem

# Spec 기반 파이프라인
from app.specs.registry import get_spec
from app.specs.utils import strip_code_fence

logger = logging.getLogger("service.item_generator")

# last_schema_errors = None

# =========================
# JSON/Parsing Utilities
# =========================

def pre_json_fix(text: str) -> str:
    """
    모델 출력에서 코드펜스/스마트쿼트/정답기호 등 자주 어긋나는 포맷을 1차 교정.
    """
    s = (text or "").strip()
    s = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", s, flags=re.IGNORECASE)
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    # 정답 기호가 ①~⑤인데 따옴표가 누락된 경우를 방어
    s = re.sub(r'("correct_answer"\s*:\s*)([①②③④⑤])', r'\1"\2"', s)
    return s.strip()


def _json_schema_of(model_cls) -> dict:
    """
    Pydantic v2 / v1 호환 스키마 추출
    """
    try:
        return model_cls.model_json_schema()  # v2
    except Exception:
        return model_cls.schema()             # v1


def _parse_json_loose(s: str) -> dict:
    """
    JSON 본문 앞뒤에 잡소리가 섞인 경우, 마지막 닫는 괄호까지를 찾아 파싱.
    - ✅ 빈 응답 / 닫는 괄호 없음 케이스를 명확히 구분해 예외 메시지 부여
    """
    s = (s or "").strip()  # ✅
    if not s:
        # 빈 문자열은 상위에서 즉시 재생성 루프로 가도록 명확한 예외 부여
        raise json.JSONDecodeError("empty_response", "", 0)  # ✅
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        m = re.search(r'\{[\s\S]*\}\s*$', s)
        if not m:
            # 닫는 괄호 자체가 없으면 상위에서 재생성
            raise json.JSONDecodeError("no_closing_brace_found", s[:80], 0)  # ✅
        return json.loads(m.group(0))


def _validate_mcq(data: dict) -> MCQItem:
    """
    레거시 MCQ 스키마 검증 (실패 시 ValidationError)
    """
    return MCQItem(**data)


def _ensure_plain_dict(obj: Any) -> dict:
    """
    Pydantic BaseModel 또는 기타 객체를 항상 plain dict로 변환.
    """
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump()
        except Exception:
            pass
    if hasattr(obj, "dict"):
        try:
            return obj.dict()
        except Exception:
            pass
    return obj  # dict가 아닐 수도 있으나, 호출부에서 다시 보정


def _is_blank(s: Any) -> bool:
    """✅ 문자열이 비어있거나 공백뿐인지 확인."""
    return (not isinstance(s, str)) or (not s.strip())


# =========================
# Model Call Wrapper
# =========================

async def _call_chat(messages: list[dict[str, str]], trace_id: str | None, timeout_s: float) -> str:
    """
    openai_config.chat_completion 을 sync/async 모두 호환하게 호출.
    """
    try:
        maybe = openai_config.chat_completion(messages=messages, trace_id=trace_id, timeout_s=timeout_s)
    except TypeError:
        # 구버전 시그니처 호환
        maybe = openai_config.chat_completion(messages)

    if asyncio.iscoroutine(maybe):
        return await asyncio.wait_for(maybe, timeout=timeout_s)

    loop = asyncio.get_running_loop()
    return await asyncio.wait_for(loop.run_in_executor(None, lambda: maybe), timeout=timeout_s)


# =========================
# Safe Validator Wrapper
# =========================

async def _spec_validate_safe(spec_obj, data, *, content_only_flag: bool):
    """
    스펙의 validate 호출을 안전하게 감싼다.
    - 스펙이 content_only 파라미터를 지원하면 전달
    - 지원하지 않으면 전달하지 않고 호출
    - sync/async 모두 처리
    """
    fn = getattr(spec_obj, "validate", None)
    if fn is None:
        return

    # 파라미터 수용 여부 확인
    try:
        sig = inspect.signature(fn)
        accepts_content_only = "content_only" in sig.parameters
    except Exception:
        accepts_content_only = False

    kwargs = {"content_only": content_only_flag} if accepts_content_only else {}

    if inspect.iscoroutinefunction(fn):
        return await fn(data, **kwargs)
    else:
        return fn(data, **kwargs)


# =========================
# Repair Helpers (schema_dict 버전)
# =========================

async def _fix_with_schema(raw: str, schema_dict: dict, trace_id: str | None, timeout_s: float) -> str:
    """
    Fixer: 임의 텍스트(raw)를 주어진 JSON 스키마에 '맞는' VALID JSON으로 변환만 수행.
    출력은 반드시 순수 JSON (코드펜스/설명 없음).
    """
    schema = json.dumps(schema_dict, ensure_ascii=False)
    messages = [
        {
            "role": "system",
            "content": (
                "You convert the user's text into VALID JSON strictly matching the provided JSON Schema. "
                "Output ONLY the JSON. No code fences, no prose."
            ),
        },
        {
            "role": "user",
            "content": f"JSON Schema:\n{schema}\n\nInput:\n{raw}",
        },
    ]
    return await _call_chat(messages, trace_id, timeout_s)


async def _regenerate_strict(prompt_str: str, schema_dict: dict, trace_id: str | None, timeout_s: float) -> str:
    """
    Strict Regeneration: 스키마를 강제하면서 처음부터 다시 생성.
    출력은 반드시 순수 JSON.
    """
    schema = json.dumps(schema_dict, ensure_ascii=False)
    messages = [
        {
            "role": "system",
            "content": (
                "CSAT English item generator. Return ONLY JSON strictly matching the provided JSON Schema. "
                "No code fences. No explanations. Korean content is allowed."
            ),
        },
        {
            "role": "user",
            "content": f"JSON Schema:\n{schema}\n\nNow generate according to this instruction:\n{prompt_str}",
        },
    ]
    return await _call_chat(messages, trace_id, timeout_s)


# =========================
# Public API
# =========================

async def generate_item(item_id: str, payload: Any, *, trace_id: str | None = None) -> dict:
    """
    Spec 기반 파이프라인:
      1) spec이 있으면 spec.normalize/validate/json_schema/repair_budget 사용
      2) 없으면 레거시(MCQItem) 경로로 폴백
      3) 항상 Envelope 응답 형태 반환:
         - 성공: {"ok": True, "item": <dict>, "meta": {...}}
         - 실패: {"ok": False, "error": {...}, "meta": {...}}
    """
    logger.info("item_generator LOADED v2025-10-15-L2")
    # ---------- 입력 컨텍스트 ----------
    schema_errors = None

    difficulty = getattr(payload, "difficulty", None) or (payload.get("difficulty") if isinstance(payload, dict) else None)
    topic = getattr(payload, "topic", None) or (payload.get("topic") if isinstance(payload, dict) else None)
    passage_text = getattr(payload, "passage", None) or (payload.get("passage") if isinstance(payload, dict) else None)
    passage_text = (passage_text or "").strip()

    # (SIMPLE) vocab_profile은 항상 프롬프트에 있다고 가정하고 거기서만 추출
    def _vocab_from_prompt(_item_id: str) -> str:
        content = ITEM_PROMPTS.get(_item_id, {}).get("content", "") or ""
        m = re.search(r'"vocabulary_difficulty"\s*:\s*"([^"]+)"', content)
        if not m:
            # 프롬프트에 반드시 있다고 가정하므로, 없으면 명확히 실패시켜 원인 노출
            raise ValueError(f'vocabulary_difficulty not found in prompt content for item_id={_item_id}')
        return m.group(1).strip()

    vocab_profile = _vocab_from_prompt(item_id)

    # enable_overlay는 기존 로직 유지
    enable_overlay = getattr(payload, "enable_overlay", None) if not isinstance(payload, dict) else payload.get("enable_overlay")
    if enable_overlay is None:
        enable_overlay = getattr(settings, "USE_PROMPT_OVERLAY", True)

    t0 = time.perf_counter()
    meta_base = {
        "trace_id": trace_id, "item_id": item_id,
        "difficulty": difficulty, "topic": topic,
        "has_passage": bool(passage_text), "passage_len": len(passage_text),
        "vocab_profile": vocab_profile, "enable_overlay": enable_overlay,
    }
    logger.info("generate_start", extra=meta_base)

    # ✅ 공통 컨텍스트를 선행 생성: content-first/공용 경로/프롬프트 빌드에서 일관 사용
    ctx = {
        "item_id": item_id,
        "difficulty": difficulty or "medium",
        "topic": topic or "random",
        "passage": passage_text or "",
        "vocab_profile": vocab_profile,
        "enable_overlay": bool(enable_overlay),
    }
    

    # ---------- Spec 조회 ----------
    spec = get_spec(item_id)
    is_rc25 = (item_id == "RC25")

    # Helper: sync/async 함수 모두 안전 호출
    async def _maybe_call(fn, *args, **kwargs):
        if inspect.iscoroutinefunction(fn):
            return await fn(*args, **kwargs)
        return fn(*args, **kwargs)

    # - 이미 passage가 있을 때만 spec.build_prompt를 사용
    # - 그 외(일반 생성)는 항상 PromptManager.generate 사용
    # - build_prompt가 없거나 비어 있으면 즉시 PM 경로로 폴백
    try:
        if spec and passage_text and hasattr(spec, "build_prompt"):
            print("인용", item_id)
            prompt_str = await _maybe_call(spec.build_prompt, ctx)
            # build_prompt가 비어있으면 PM 경로로 폴백
            if not isinstance(prompt_str, str) or not prompt_str.strip():
                logger.warning("prompt_not_available", extra={**meta_base})
                print("생성(폴백)", item_id)
                prompt_str = PromptManager.generate(
                    item_type=item_id,
                    difficulty=ctx["difficulty"],
                    topic_code=ctx["topic"],
                    passage=ctx["passage"],
                    vocab_profile=ctx["vocab_profile"],
                    enable_overlay=ctx["enable_overlay"],
                )
        else:
            print("생성", item_id)
            prompt_str = PromptManager.generate(
                item_type=item_id,
                difficulty=ctx["difficulty"],
                topic_code=ctx["topic"],
                passage=ctx["passage"],
                vocab_profile=ctx["vocab_profile"],
                enable_overlay=ctx["enable_overlay"],
            )
    except Exception as e:
        logger.exception("prompt_build_failed", extra=meta_base)
        return {
            "ok": False,
            "error": {"type": "PromptError", "message": str(e)},
            "meta": {**meta_base, "phase": "prompt_build"},
        }

    if isinstance(prompt_str, str):
        logger.info("prompt_ready", extra={**meta_base, "prompt_len": len(prompt_str)})
    else:
        logger.warning("prompt_not_available", extra={**meta_base})

    # 타임아웃/리페어 예산
    timeout_s = max(1.0, settings.REQUEST_TIMEOUT_MS / 1000)
    fixer_allowed = True
    regen_rounds = 1

    if spec:
        budget = spec.repair_budget() or {}
        timeout_s = budget.get("timeout_s", timeout_s)
        fixer_allowed = budget.get("fixer", 1) > 0
        regen_rounds = budget.get("regen", 1)

    # 🔹 RC25 전용: Fixer 비활성화(내용오류에 비효율) + Regenerate 우선
    if is_rc25:
        fixer_allowed = False
        regen_rounds = max(regen_rounds, 2)

    # ---------- 검증 래퍼 ----------
    async def _validate_any(text: str, spec_obj, has_spec: bool) -> tuple[dict, str]:
        cleaned_local = strip_code_fence(pre_json_fix(text))
        print("🔍 [item_generator] raw model output =", text[:400])
        print("🔍 [item_generator] cleaned =", cleaned_local[:400])
        data_local = _parse_json_loose(cleaned_local)

        if has_spec:
            data_local = spec_obj.normalize(data_local)
            # 🔹 RC25: 먼저 빠른 예비검사(fast_precheck)로 저렴하게 탈락시킨 뒤,
            #          본 검증은 호출부(성공 경로)에서 엄격모드로 수행
            if is_rc25 and hasattr(spec_obj, "fast_precheck"):
                ok_fast, reason = spec_obj.fast_precheck(data_local)
                if not ok_fast:
                    # 예비검사 즉시 실패 → Fixer 생략, 재생성 단계로 이동
                    raise ValueError(f"fast_precheck_failed:{reason}")
            elif not is_rc25:
                # 비 RC25 문항은 종전 로직 유지
                await _spec_validate_safe(spec_obj, data_local, content_only_flag=False)
        else:
            _validate_mcq(data_local)

        return data_local, cleaned_local

    phase = "primary"
    attempts = 0

    # ---------- 1) 1차 생성 ----------
    # RC25 전용: 스펙 내부 content-first 루프를 호출해 생성/검증을 끝낸다.
    if spec and is_rc25 and hasattr(spec, "content_first_generate"):
        phase = "primary"
        attempts = 1
        try:
            data = await spec.content_first_generate(ctx)   # ✅ 스펙 내부 루프 활용
            # ✅ 규칙 강제: 여기서도 엄격 검증(content_only=False)으로 확정
            #   - 거짓 개수 ≠ 1 → 예외 → 아래 except에서 공용 경로 폴백 → Regenerate
            #   - 거짓 1개 & 정답 불일치 → auto-fix(정답/해설 보정)
            await _spec_validate_safe(spec, data, content_only_flag=False)
            dt = int((time.perf_counter() - t0) * 1000)
            logger.info("generate_success_primary", extra={**meta_base, "phase": phase, "attempts": attempts, "duration_ms": dt})
            return {"ok": True, "item": _ensure_plain_dict(data), "meta": {**meta_base, "phase": phase, "attempts": attempts, "duration_ms": dt}}
        except Exception as e:
            # ❗ content-first 실패 시: 즉시 에러 반환하지 말고 공용 경로로 폴백
            logger.warning("rc25_content_first_failed_fallback_to_common", extra={**meta_base, "error": str(e)})

    # ---------- 1) 1차 생성 (공용 경로) ----------
    try:
        attempts += 1
        system_msg = "CSAT English item generator"
        if passage_text:
            system_msg += " — Use ONLY the provided passage. Do NOT invent or substitute a new passage."

        raw = await _call_chat(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt_str},
            ],
            trace_id=trace_id,
            timeout_s=timeout_s,
        )
        # ✅ 빈 응답 1회 재시도 (일시적 필터/네트워크/서버상태)
        if _is_blank(raw):
            logger.warning("empty_model_response_primary_retry", extra={**meta_base})  # ✅
            raw = await _call_chat(
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt_str},
                ],
                trace_id=trace_id,
                timeout_s=timeout_s,
            )
            if _is_blank(raw):
                raise ValueError("empty_model_response_primary")  # ✅

        data, cleaned = await _validate_any(raw, spec, has_spec=bool(spec))
        # 🔹 RC25는 예비검사 통과 후 여기서 ‘엄격 검증(content_only=False)’ 수행
        if spec and is_rc25:
            await _spec_validate_safe(spec, data, content_only_flag=False)
        dt = int((time.perf_counter() - t0) * 1000)
        logger.info("generate_success_primary", extra={**meta_base, "phase": phase, "attempts": attempts, "duration_ms": dt})
        return {"ok": True, "item": data, "meta": {**meta_base, "phase": phase, "attempts": attempts, "duration_ms": dt}}

    except ValidationError as ve:
        # ✅ pydantic v1/v2 모두 호환
        try:
            schema_errors = ve.errors()
        except Exception:
            schema_errors = str(ve)
        logger.warning("validation_failed", extra={**meta_base, "errors": schema_errors})
    except Exception as e1:
        logger.warning("primary_failed", extra={**meta_base, "error": str(e1)})

    # ---------- 2) Fixer ----------
    if fixer_allowed:
        try:
            attempts += 1
            schema_dict = spec.json_schema() if spec else _json_schema_of(MCQItem)
            fixed = await _fix_with_schema(
                raw if "raw" in locals() else "",
                schema_dict=schema_dict,
                trace_id=trace_id,
                timeout_s=timeout_s,
            )
            # ✅ Fixer 결과 빈 응답 방어
            if _is_blank(fixed):
                raise ValueError("empty_fixer_response")  # ✅

            data = _parse_json_loose(pre_json_fix(fixed))
            if spec:
                data = spec.normalize(data)
                await _spec_validate_safe(spec, data, content_only_flag=False)
            else:
                _validate_mcq(data)

            phase = "fixed"
            dt = int((time.perf_counter() - t0) * 1000)
            logger.info("generate_success_fixed", extra={**meta_base, "phase": phase, "attempts": attempts, "duration_ms": dt})
            return {"ok": True, "item": data, "meta": {**meta_base, "phase": phase, "attempts": attempts, "duration_ms": dt}}
        except ValidationError as ve2:
            try:
                schema_errors = ve2.errors()
            except Exception:
                schema_errors = str(ve2)
            logger.warning("fixer_validation_failed", extra={**meta_base, "errors": schema_errors})
        except Exception as e2:
            logger.warning("fixer_failed", extra={**meta_base, "error": str(e2)})

    # ---------- 3) Regenerate (N회) ----------
    for i in range(max(1, regen_rounds)):
        try:
            attempts += 1
            schema_dict = spec.json_schema() if spec else _json_schema_of(MCQItem)
            regen = await _regenerate_strict(
                prompt_str,
                schema_dict=schema_dict,
                trace_id=trace_id,
                timeout_s=timeout_s,
            )
            # ✅ 리젠 결과 빈 응답이면 즉시 다음 라운드로
            if _is_blank(regen):
                logger.warning("empty_model_response_regen", extra={**meta_base, "round": i + 1})  # ✅
                raise ValueError("empty_model_response_regen")  # ✅ -> except에서 잡히고 다음 라운드 진행

            data = _parse_json_loose(pre_json_fix(regen))
            if spec:
                data = spec.normalize(data)
                await _spec_validate_safe(spec, data, content_only_flag=False)
            else:
                _validate_mcq(data)

            phase = f"regenerated_{i+1}"
            dt = int((time.perf_counter() - t0) * 1000)
            logger.info("generate_success_regenerated", extra={**meta_base, "phase": phase, "attempts": attempts, "duration_ms": dt})
            return {"ok": True, "item": data, "meta": {**meta_base, "phase": phase, "attempts": attempts, "duration_ms": dt}}
        except ValidationError as ve3:
            try:
                schema_errors = ve3.errors()
            except Exception:
                schema_errors = str(ve3)
        except Exception as e3:
            logger.warning("regenerate_failed", extra={**meta_base, "round": i + 1, "error": str(e3)})

    # ---------- 4) 최종 실패 ----------
    snippet = (locals().get("cleaned") if "cleaned" in locals() else (locals().get("raw") or ""))[:1000]
    dt = int((time.perf_counter() - t0) * 1000)
    logger.error(
        "generate_failed_final",
        extra={**meta_base, "attempts": attempts, "duration_ms": dt}
    )
    return {
        "ok": False,
        "error": {
            "type": "InvalidModelOutput",
            "message": "Model output invalid after repair/regeneration",
            "snippet": snippet,
            "schema_errors": schema_errors,  # ✅ 로컬 변수 사용
        },
        "meta": {**meta_base, "attempts": attempts, "duration_ms": dt},
    }
