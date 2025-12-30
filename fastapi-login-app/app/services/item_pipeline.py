# app/services/item_pipeline.py
from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
import random
import os
import json

from app.services.llm_client import call_llm_json
from app.services.validators import validate_with_model
from app.services.postprocess import sanitize_html
from app.specs.registry import get_spec
from app.specs.helpers import make_prompt_with_passage, default_system_prompt
from app.prompts.type_mapping import resolve_item_id_from_type
from app.prompts.prompt_data import ITEM_PROMPTS
from app.specs.passage_preprocessor import retarget_for_item


# -----------------------------
# Small helpers (debug-friendly)
# -----------------------------
def _clip(s: str, n: int = 2000) -> str:
    try:
        return s if len(s) <= n else (s[:n] + "...<clipped>")
    except Exception:
        return str(s)

def _pp_json(obj: Any, n: int = 2000) -> str:
    try:
        return _clip(json.dumps(obj, ensure_ascii=False, indent=2), n)
    except Exception:
        return _clip(str(obj), n)


# -----------------------------
# Router / system prompt helpers
# -----------------------------
DEFAULT_SYSTEM_PROMPT = (
    "You are a routing assistant for CSAT Reading item types. "
    "Your ONLY job is to analyze the given passage and propose suitable item types with confidence scores. "
    "Use ONLY the provided passage. Do NOT invent, alter, or substitute any passage content. "

    "OUTPUT RULES (must follow all): "
    "- Return JSON ONLY. No markdown, no code fences, no commentary. "
    "- JSON shape: { \"candidates\": [ "
    "{\"type\": \"<RC_CODE>\", \"fit\": <float 0..1>, \"reason\": \"<=120 chars\", \"prep_hint\": \"<string or '-'>\" }, ... ] } "
    "- \"type\" must be one of: "
    "[\"RC18\",\"RC19\",\"RC20\",\"RC21\",\"RC22\",\"RC23\",\"RC24\",\"RC25\",\"RC26\",\"RC27\",\"RC28\","
    "\"RC29\",\"RC30\",\"RC31\",\"RC32\",\"RC33\",\"RC36\",\"RC37\",\"RC38\",\"RC39\",\"RC40\","
    "\"RC41\",\"RC42\",\"RC43\",\"RC44\",\"RC45\"]. "
    "- Produce 5–10 unique candidates, sorted by \"fit\" descending. "
    "- \"fit\" is confidence in [0,1]; use at most 2 decimals. Lower fit (0.3–0.6) is allowed if only content suggests possibility. "
    "- \"reason\": concise rationale (<=120 chars). No line breaks or internal quotes. "
    "- \"prep_hint\": brief solving strategy, or '-' if none. "
    "- No extra keys, no trailing commas, no NaN/Infinity. "

    "SCORING GUIDANCE (for reasoning only, not output): "
    "Expository/explanatory passages → RC22/RC23/RC24/RC31/RC32/RC33/RC40. "
    "Tables/figures/stats (%/ratio/rank) → RC25. "
    "Biographical/timeline (born/awarded/career) → RC26. "
    "Notices/forms (Title:/Date:/Location:) → RC27/RC28. "
    "Letter format (Dear, Sincerely/Regards) → RC18. "
    "Attitude/emotion (feel, anxious, excited, etc.) → RC19. "
    "Claims/obligation (should/must/need to) → RC20. "
    "Labeled chunks (A)(B)(C) → RC36/RC37 (ordering). Even if explicit markers are missing, "
    "if the passage clearly describes a sequence or process, consider RC36/RC37 with lower fit (0.4–0.6). "
    "Insertion markers (①~⑤) → RC38/RC39. "
    "Bullets ①~⑤ with underlines → RC29/RC30 (grammar/lexis). "

    "HARD CONSTRAINTS: "
    "No explanations outside JSON. Never output text other than the JSON object. "
    "If uncertain, still return best-effort candidates with lower fit."
)

def _get_system_prompt(spec, passage: Optional[str] = None) -> str:
    """
    - spec.system_prompt() 또는 문자열 제공 시 우선 사용
    - 없으면 default_system_prompt() 사용
    - passage가 있으면 '제공된 지문만 사용' 제약 문구가 없을 때 보강
    """
    sp = getattr(spec, "system_prompt", None)
    if callable(sp):
        base = sp()
    elif isinstance(sp, str):
        base = sp
    else:
        base = default_system_prompt()

    if passage:
        guard = "Use ONLY the provided passage. Do NOT invent or substitute a new passage."
        if guard not in base:
            base = (base.rstrip() + "\n" + guard).strip()
    return base


# -----------------------------
# Prompt & pipeline helpers
# -----------------------------
def build_ctx_for_custom(item_id: str, passage: str, difficulty: Optional[str], topic: str) -> Dict[str, Any]:
    """
    전처리/리타깃팅(erase 모드 기본). 필요 시 fill_copy/fill_rule로 확장 가능.
    ※ 인용(quote) 전용 경로에서만 사용됨.
    """
    prepped = retarget_for_item(item_id, passage, fill_mode="erase")
    return {
        "mode": "custom_passage",
        "item_id": item_id,
        "passage": prepped,
        "difficulty": difficulty or "medium",
        "topic": topic or "random",
    }

def _build_prompt_compat(
    spec,
    passage: str,
    *,
    item_id: str,
    difficulty: Optional[str],
    topic: str = "random"
) -> str:
    """
    spec 구현체 간 시그니처 차이를 흡수하기 위한 호환 래퍼.
    1) build_prompt(ctx) 우선
    2) build_prompt(passage, difficulty)
    3) build_prompt(passage)
    (※ generate 경로 호환용. quote 전용 훅이 있으면 사용하지 않음)
    """
    ctx = {
        "item_id": item_id,
        "difficulty": (difficulty or "medium"),
        "topic": topic,
        "passage": passage,
    }
    # 1) ctx 기반
    try:
        return spec.build_prompt(ctx)
    except TypeError:
        pass
    except Exception:
        # 다른 예외는 상위에서 잡히도록 그대로 올림
        raise

    # 2) (passage, difficulty)
    try:
        return spec.build_prompt(passage, (difficulty or "medium"))
    except TypeError:
        pass
    except Exception:
        raise

    # 3) (passage)
    return spec.build_prompt(passage)

def _repair_compat(spec, raw: dict, passage: str) -> dict:
    """
    repair → normalize 순서로 호출. 없는 함수는 스킵.
    (※ generate 경로 호환용. quote 전용 훅이 있으면 사용하지 않음)
    """
    data = raw
    rep = getattr(spec, "repair", None)
    if callable(rep):
        try:
            data = rep(raw, passage)
        except Exception:
            data = raw

    norm = getattr(spec, "normalize", None)
    if callable(norm):
        try:
            data = norm(data)
        except Exception:
            pass
    return data

def _validate_compat(spec, data: dict) -> Tuple[bool, Optional[str]]:
    """
    1) spec.model() 있으면 validate_with_model 사용
    2) spec.validate(data) 있으면 예외 여부로 판정
    3) 둘 다 없으면 True
    (※ generate 경로 호환용. quote 전용 훅이 있으면 사용하지 않음)
    """
    model_fn = getattr(spec, "model", None)
    if callable(model_fn):
        try:
            ok, err = validate_with_model(model_fn(), data)
            return bool(ok), (str(err) if err else None)
        except Exception as e:
            return False, f"model/validation error: {e}"

    validate_fn = getattr(spec, "validate", None)
    if callable(validate_fn):
        try:
            validate_fn(data)  # Pydantic 인스턴스 생성 등
            return True, None
        except Exception as e:
            return False, str(e)

    return True, None

def _self_checks_compat(spec, data: dict, passage: str) -> List[str]:
    fn = getattr(spec, "self_checks", None)
    if callable(fn):
        try:
            issues = fn(data, passage)
            return issues or []
        except Exception:
            return ["self_checks raised an exception"]
    return []


# -----------------------------
# Global key coercion (Emergency/Safety Net)
# -----------------------------
def _coerce_common_keys(raw: Any, passage_text: Optional[str] = None) -> Any:
    """
    응급/겸용안(재귀 적용):
    - 어느 깊이에 있든 stimulus/question_stem을 표준 스펙 키(passage, question)로 매핑한다.
    - 검증 전(스펙 repair 호출 전) 한 번 적용.
    """
    # dict: 키 치환 + 값 재귀
    if isinstance(raw, dict):
        out: Dict[str, Any] = {}
        for k, v in raw.items():
            new_k = k
            if k == "stimulus":
                new_k = "passage"
            elif k == "question_stem":
                new_k = "question"
            out[new_k] = _coerce_common_keys(v, passage_text)
        # 백스톱: passage 누락 시 상위에서 받은 지문 보강
        if "passage" not in out and passage_text:
            out["passage"] = passage_text
        return out

    # list/tuple: 요소 재귀
    if isinstance(raw, list):
        return [_coerce_common_keys(x, passage_text) for x in raw]

    # 기타 스칼라: 그대로
    return raw


# -----------------------------
# Public API (QUOTE-ONLY PIPELINE)
# -----------------------------
def generate_multi_from_passage(
    passage: str,
    types: List[str],
    n_per_type: int = 1,
    difficulty: Optional[str] = None,
    seed: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    인용(quote) 기반 생성 파이프라인.
    - generate(생성) 경로에는 영향 없음 (generate.py 별도).
    - 문항 단위로 예외를 분리 처리하여 일부 실패해도 다른 문항은 정상 반환.

    반환 형식:
    [
      { "ok": True,  "item": {...}, "meta": {"type": "RC33", "seed": ..., "item_id": "RC33"} },
      { "ok": False, "message": "잘못된 생성입니다. 다시 생성해 주세요",
        "error": {"detail": "...(최대 300자)"}, "meta": {"type": "...", "seed": ..., "item_id": "..."} }
    ]
    """
    if seed is not None:
        random.seed(seed)

    results: List[Dict[str, Any]] = []
    item_prompt_keys = set(ITEM_PROMPTS.keys())
    FAIL_MSG = "잘못된 생성입니다. 다시 생성해 주세요"

    def _append_fail(t: str, item_id: str, seed_val: Optional[int], detail: Optional[str] = None) -> None:
        results.append({
            "ok": False,
            "message": FAIL_MSG,
            "error": {"detail": (detail or "")[:300]},
            "meta": {"type": t, "seed": seed_val, "item_id": item_id},
        })

    for t in types:
        # 1) type → item_id 해석
        try:
            item_id = resolve_item_id_from_type(t, item_prompts_keys=item_prompt_keys)
        except Exception as e:
            _append_fail(t, "UNKNOWN", seed, f"type resolve error: {e}")
            continue

        # 2) spec 확보
        spec = get_spec(item_id)
        if spec is None:
            _append_fail(t, item_id, seed, f"unknown type: {t}")
            continue

        # 3) 전처리/리타깃팅 (인용 전용, 항목 단위 실패 처리)
        try:
            ctx_pre = build_ctx_for_custom(item_id, passage, difficulty, "random")
            prepped_passage = ctx_pre["passage"]
        except Exception as e:
            _append_fail(t, item_id, seed, f"preprocess error: {e}")
            continue

        # 4) n_per_type 만큼 생성
        for _ in range(max(1, n_per_type)):
            try:
                # ============== QUOTE vs (legacy) GENERATE 분기 ==============
                has_quote = getattr(spec, "has_quote_support", lambda: False)()
                if has_quote:
                    # --- QUOTE 전용 흐름 (스펙 훅 사용) ---
                    # 4-1) 프롬프트 구성
                    try:
                        prompt = spec.quote_build_prompt(prepped_passage)
                    except Exception as e:
                        _append_fail(t, item_id, seed, f"quote_build_prompt error: {e}")
                        continue

                    # 4-2) LLM 호출 (메타 JSON만 수신)
                    #     quote 프롬프트가 충분히 강하므로 system은 최소한으로 유지
                    raw = call_llm_json(
                        system="You are a careful JSON-only generator. Return JSON only.",
                        user=prompt,
                        temperature=0.2,
                        max_tokens=1200,
                        timeout_s=18,
                        retries=0,
                    )
                    if not raw or (isinstance(raw, dict) and raw.get("ok") is False):
                        _append_fail(t, item_id, seed, "llm returned no valid JSON (quote)")
                        continue

                    # 4-3) (선택) 글로벌 키 보정 — passage 보강 외에는 영향 없음
                    raw = _coerce_common_keys(raw, prepped_passage)

                    # 4-4) 스펙 사후처리(결정론적 표식 삽입) + 검증
                    try:
                        data_item = spec.quote_postprocess(prepped_passage, raw)
                    except Exception as e:
                        _append_fail(t, item_id, seed, f"quote_postprocess error: {e}")
                        continue

                    try:
                        spec.quote_validate(data_item)
                    except Exception as e:
                        _append_fail(t, item_id, seed, f"quote_validate error: {e}")
                        continue

                    # 4-5) HTML 위생 처리
                    data_item = sanitize_html(data_item)

                    results.append({
                        "ok": True,
                        "item": data_item,
                        "meta": {"type": t, "seed": seed, "item_id": item_id, "mode": "quote"},
                    })
                    continue  # quote 분기 종료

                # --- (Fallback) 기존 호환 흐름 (일부 스펙이 quote 훅 없을 때) ---
                prompt = _build_prompt_compat(
                    spec, prepped_passage, item_id=item_id, difficulty=difficulty, topic="random"
                )
                # 지문 삽입이 누락되어 있으면 보강
                if (
                    prepped_passage and prepped_passage.strip()
                    and ("```passage" not in prompt) and ("<PASSAGE>" not in prompt)
                ):
                    prompt = make_prompt_with_passage(prompt, prepped_passage.strip())

                # 세트형(장문 세트) 분기: RC41/RC42/RC41_42 는 더 타이트한 예산 사용
                is_set_type = item_id in ("RC41", "RC42", "RC41_42")

                # 응답 지연을 줄이기 위한 예산 조정
                llm_max_tokens = 1000 if is_set_type else 1500
                llm_timeout_s  = 16  if is_set_type else 18

                raw = call_llm_json(
                    system=_get_system_prompt(spec, prepped_passage),
                    user=prompt,
                    temperature=0.2,
                    max_tokens=llm_max_tokens,
                    timeout_s=llm_timeout_s,
                    retries=0,                 # 🟢 재시도 끔: 문항 단위로 빨리 실패-수거
                )

                # 유효성 1차 확인
                if not raw or (isinstance(raw, dict) and raw.get("ok") is False):
                    _append_fail(t, item_id, seed, "llm returned no valid JSON")
                    continue

                # ✅ 응급/겸용안: 글로벌 키 보정 (stimulus/question_stem → passage/question), 재귀 적용
                raw = _coerce_common_keys(raw, prepped_passage)

                # repair/normalize (스펙별 보정)
                data = _repair_compat(spec, raw, prepped_passage)

                # validate (모델/함수)
                ok, err = _validate_compat(spec, data)
                if not ok:
                    # 마지막 보정 시도
                    data = _repair_compat(spec, data, prepped_passage)
                    ok, err = _validate_compat(spec, data)

                if ok:
                    data = sanitize_html(data)

                # self checks
                issues = _self_checks_compat(spec, data, prepped_passage)

                if ok and not issues:
                    results.append({
                        "ok": True,
                        "item": data,
                        "meta": {"type": t, "seed": seed, "item_id": item_id, "mode": "compat"},
                    })
                else:
                    detail = f"validation: {err}; issues: {issues}"
                    _append_fail(t, item_id, seed, detail)

            except (json.JSONDecodeError, ValueError) as e:
                # LLM JSON 파싱/스키마류 실패 → 해당 문항만 실패
                _append_fail(t, item_id, seed, f"json/validation error: {e}")
                continue
            except Exception as e:
                # 그 외 모든 예외도 해당 문항만 실패
                _append_fail(t, item_id, seed, f"unhandled: {e}")
                continue

    return results
