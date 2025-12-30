# app/specs/lc06_payment_amount.py

from __future__ import annotations
import re
from typing import Tuple, List, Dict, Any
from app.specs.base import ItemSpec

# -------------------------------------------------
# 최소 검증(보강): 결과에 '소수점'이 한 글자라도 보이면 실패 처리 → 재생성 유도
# - 케이스: 0.8, 8.0, .5, $8.80, 1,234.50 등 모두 탐지
# -------------------------------------------------
# 설명:
# - \d+\.\d+ : 일반 소수 (e.g., 8.8, 123.50)
# - (?<!\d)\.\d+ : 리딩 제로 없는 소수 (.5)
# - 콤마나 통화기호가 앞뒤에 있어도 경계에서 매칭되도록 비단어 경계 사용
_DECIMAL_RE = re.compile(r"(?:\d+\.\d+|(?<!\d)\.\d+)")

def _as_str(x: Any) -> str:
    return "" if x is None else str(x)

class LC06Spec(ItemSpec):
    """
    LC06 — Listening Payment Amount (소수점 차단용 미니멀 밸리데이터)
    - 산출물 어딘가에 소수점 수치가 등장하면 실패 → 상위 파이프라인에서 재생성
    - (다른 규칙은 프롬프트/상위 스펙에서 유도)
    """
    type: str = "listening_payment_amount"

    def title(self) -> str:
        return "LC06 - Payment Amount (Decimal-Free Minimal Validator, v2)"

    def normalize(self, item: Dict[str, Any]) -> Dict[str, Any]:
        obj = dict(item or {})
        # 정답 인덱스는 int로 캐스팅(가능하면)
        try:
            if isinstance(obj.get("correct_answer"), str):
                obj["correct_answer"] = int(obj["correct_answer"])
        except Exception:
            pass
        # 보기 문자열 트리밍
        if isinstance(obj.get("options"), list):
            obj["options"] = [str(o).strip() for o in obj["options"]]
        return obj

    def _contains_decimal(self, text: str) -> bool:
        if not text:
            return False
        # 통화기호/콤마 유무에 관계없이 소수부(.)가 있으면 매칭
        return bool(_DECIMAL_RE.search(text))

    def validate(self, item: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        # 1) transcript / explanation
        tr = _as_str(item.get("transcript")).strip()
        ex = _as_str(item.get("explanation")).strip()
        if self._contains_decimal(tr):
            errors.append("Transcript contains a decimal number (소수점 금지, 재생성).")
        if self._contains_decimal(ex):
            errors.append("Explanation contains a decimal number (소수점 금지, 재생성).")

        # 2) question
        q = _as_str(item.get("question")).strip()
        if self._contains_decimal(q):
            errors.append("Question contains a decimal number (소수점 금지, 재생성).")

        # 3) options
        opts = item.get("options") or []
        for idx, opt in enumerate(opts, start=1):
            s = _as_str(opt).strip()
            if self._contains_decimal(s):
                errors.append(f"Option #{idx} contains a decimal number (소수점 금지, 재생성): {s}")

        return (len(errors) == 0), errors

    def postprocess(self, item: Dict[str, Any]) -> Dict[str, Any]:
        obj = dict(item or {})
        obj.pop("audio_url", None)
        return obj
