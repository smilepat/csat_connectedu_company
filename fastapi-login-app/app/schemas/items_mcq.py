# app/schemas/items_mcq.py
from typing import Literal, Any, List, Optional
from pydantic import BaseModel, Field

# 버전 감지
try:
    from pydantic import model_validator  # v2
    V2 = True
except ImportError:
    from pydantic import root_validator   # v1
    V2 = False

Choice = Literal["1","2","3","4","5"]  # ← 표준화


class MCQItem(BaseModel):
    passage: Optional[str] = None
    script: Optional[str] = None

    question: str = Field(min_length=5)
    options: List[str] = Field(min_length=5, max_length=5)
    correct_answer: Choice
    explanation: Optional[str] = None

    # --- 레거시 입력 하위호환 (rationale→explanation, 정답 표기 통일) ---
    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy(cls, data: Any):
        """
        레거시 입력 호환:
        - rationale → explanation
        - correct_answer 정규화 (①~⑤, A~E, 숫자형 → "1"~"5")
        """
        if isinstance(data, dict):
            if "explanation" not in data and "rationale" in data:
                data["explanation"] = data.get("rationale")

            ca = data.get("correct_answer")
            if ca is not None:
                data["correct_answer"] = cls._normalize_answer(ca)
        return data

    @staticmethod
    def _normalize_answer(val: Any) -> str:
        s = str(val).strip().upper()
        circled = {"①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5"}
        alpha = {"A": "1", "B": "2", "C": "3", "D": "4", "E": "5"}
        if s in circled: return circled[s]
        if s in alpha: return alpha[s]
        if s.isdigit() and 1 <= int(s) <= 5: return s
        return "1"  # fallback

    @model_validator(mode="after")
    def _at_least_one_context(self):
        if not (self.passage or self.script):
            raise ValueError("Either 'passage' or 'script' must be provided.")
        return self
