# app/specs/generate_with_retry.py

from __future__ import annotations
import json
import logging
import random
from typing import Any, Dict, Tuple, Optional

from app.prompts.prompt_manager import PromptManager
from app.specs.registry import get_spec
from app.specs.validators import validate_item as run_validator

log = logging.getLogger("item_generator")

# (예시) LLM 클라이언트 어댑터 — 실제 프로젝트의 클라이언트로 교체
class LLMClient:
    def __init__(self, model: str = "gpt-5"):
        self.model = model

    def complete(self, prompt: str, *, temperature: float = 0.7, seed: Optional[int] = None, max_tokens: int = 1200) -> str:
        """
        실제 구현부: 사내 LLM/오픈AI 호출로 바꾸세요.
        여기는 인터페이스 예시만 제공합니다.
        """
        raise NotImplementedError("Wire this to your LLM provider")

def _safe_json_parse(txt: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        return json.loads(txt), None
    except Exception as e:
        return None, f"JSON parse error: {e}"

def _basic_schema_checks(obj: Dict[str, Any]) -> Tuple[bool, list[str]]:
    errs = []
    for k in ("question", "transcript", "options", "correct_answer", "explanation"):
        if k not in obj:
            errs.append(f"missing key: {k}")
    # correct_answer 1~5 / options length 5
    try:
        ca = int(obj.get("correct_answer"))
        if ca < 1 or ca > 5:
            errs.append("correct_answer must be 1..5")
    except Exception:
        errs.append("correct_answer must be an integer 1..5")
    if not isinstance(obj.get("options"), list) or len(obj["options"]) != 5:
        errs.append("options must be a list of length 5")
    return (len(errs) == 0), errs

def _mutate_params_for_retry(try_idx: int, base_temp: float, enable_overlay: bool) -> Tuple[float, bool, Optional[int]]:
    """
    간단한 재시도 전략:
    - 1회 실패: seed jitter
    - 2회 실패: temperature 약간 ↑
    - 3회 실패: overlay 끔
    """
    seed = random.randint(1, 10_000_000)
    temp = base_temp
    overlay = enable_overlay
    if try_idx == 1:
        temp = min(base_temp + 0.1, 1.0)
    elif try_idx >= 2:
        temp = min(base_temp + 0.2, 1.0)
        overlay = False
    return temp, overlay, seed

def generate_with_retries(
    llm: LLMClient,
    *,
    item_id: str,
    difficulty: str = "medium",
    topic_code: str = "random",
    passage: Optional[str] = None,
    vocab_profile: Optional[str] = None,
    max_retries: int = 3,
    base_temperature: float = 0.6,
) -> Dict[str, Any]:
    """
    1) PromptManager로 프롬프트 구성
    2) LLM 호출 → JSON 파싱
    3) Spec.normalize → Spec.validate → (추가) schema/정수 검증
    4) 실패 시 파라미터 변형하여 재시도
    """
    spec = get_spec(item_id)
    if not spec:
        raise ValueError(f"No spec found for item_id={item_id}")

    enable_overlay = True
    last_errors: list[str] = []
    result_obj: Optional[Dict[str, Any]] = None

    for attempt in range(max_retries + 1):
        # 프롬프트 빌드
        prompt = PromptManager.generate(
            item_type=item_id,
            difficulty=difficulty,
            topic_code=topic_code,
            passage=passage,
            vocab_profile=vocab_profile,
            enable_overlay=enable_overlay,
        )

        # 파라미터 조정
        temp, enable_overlay, seed = _mutate_params_for_retry(attempt, base_temperature, enable_overlay)
        log.info(f"[GenTry {attempt+1}/{max_retries+1}] id={item_id} temp={temp:.2f} overlay={enable_overlay} seed={seed}")

        # LLM 호출
        raw = llm.complete(prompt, temperature=temp, seed=seed)

        # JSON 파싱
        obj, jerr = _safe_json_parse(raw)
        if jerr:
            last_errors.append(jerr)
            continue

        # 정규화
        obj = spec.normalize(obj)

        # 최소 스키마 검사
        ok_schema, schema_errs = _basic_schema_checks(obj)
        if not ok_schema:
            last_errors.extend(schema_errs)
            continue

        # 스펙 밸리데이션 (LC06은 정수/마지막 두 턴/소수점 등 강검증)
        ok_spec, spec_errs = spec.validate(obj)
        if not ok_spec:
            last_errors.extend(spec_errs)
            continue

        # 최종 후처리(불필요 키 제거 등)
        result_obj = spec.postprocess(obj)
        break

    if result_obj is None:
        detail = "; ".join(dict.fromkeys(last_errors))[:2000]  # 중복 제거 + 길이 제한
        raise ValueError(f"Item generation failed after {max_retries+1} tries: {detail}")

    return result_obj
