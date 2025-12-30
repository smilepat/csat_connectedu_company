from __future__ import annotations

from typing import Union
from pydantic import BaseModel, Field, field_validator, model_validator
from app.specs.base import ItemSpec, GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like

CIRCLED_TO_DIGIT = {
    "①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5",
    "⑴": "1", "⑵": "2", "⑶": "3", "⑷": "4", "⑸": "5",
}

class MCQModel(BaseModel):
    question: str
    passage: str
    options: list[str] = Field(min_length=5, max_length=5)
    # ⬇️ 정수/문자 모두 허용하지만, 검증 후에는 int로 정규화합니다.
    correct_answer: Union[int, str]
    explanation: str

    @field_validator("question", "passage", "explanation", mode="before")
    @classmethod
    def _strip_text(cls, v):
        return (v or "").strip()

    @field_validator("options", mode="before")
    @classmethod
    def _strip_options(cls, v):
        return [str(o).strip() for o in (v or [])]

    @field_validator("correct_answer", mode="before")
    @classmethod
    def _coerce_correct_basic(cls, v):
        """
        1차 보정:
        - None → ""
        - 정수는 그대로 통과
        - 동그라미 숫자 → "1"~"5"
        - 그 외는 문자열로 트림
        """
        if v is None:
            return ""
        if isinstance(v, int):
            return v
        s = str(v).strip()
        if s in CIRCLED_TO_DIGIT:
            return CIRCLED_TO_DIGIT[s]
        return s

    @model_validator(mode="after")
    def _coerce_correct_with_options(self):
        """
        2차 보정(최종):
        - correct_answer가 "1"~"5" 문자열이면 int로 변환
        - correct_answer가 int면 1~5 범위 확인
        - 보기 텍스트와 정확 일치하면 해당 인덱스+1을 int로 설정
        - 그 외는 에러
        """
        ca = self.correct_answer

        # 숫자 문자열 → int
        if isinstance(ca, str) and ca.isdigit():
            if ca not in {"1", "2", "3", "4", "5"}:
                raise ValueError("correct_answer must be in 1-5.")
            self.correct_answer = int(ca)
            return self

        # 정수 → 범위 점검
        if isinstance(ca, int):
            if 1 <= ca <= 5:
                return self
            raise ValueError("correct_answer must be in 1-5.")

        # 보기 텍스트 매칭 → int 인덱스
        if isinstance(ca, str) and ca:
            try:
                idx = self.options.index(ca)  # 정확 일치
                self.correct_answer = idx + 1  # int 로 저장
                return self
            except ValueError:
                pass

        raise ValueError(
            "correct_answer must be 1-5 (int or '1'~'5') or exactly equal to an option text."
        )


class BaseMCQSpec:
    """
    RC26~RC30 공통 베이스: 동일 스키마(MCQ) + 유형별 추가검증 훅(extra_checks)
    """
    id = "RCXX"  # subclass에서 override

    def system_prompt(self) -> str:
        return (
            f"CSAT English {self.id}. "
            "Return ONLY JSON matching the schema. Use ONLY the provided passage. "
            "The field 'correct_answer' MUST be the option number (1-5). "
            "If you provide option text, it will be converted to the matching option number."
        )

    def build_prompt(self, ctx: GenContext) -> str:
        item_type = (ctx.get("item_id") or self.id)
        return PromptManager.generate(
            item_type=item_type,
            difficulty=(ctx.get("difficulty") or "medium"),
            topic_code=(ctx.get("topic") or "random"),
            passage=(ctx.get("passage") or ""),
        )

    def normalize(self, data: dict) -> dict:
        return coerce_mcq_like(data)

    def validate(self, data: dict):
        """
        1) Pydantic 스키마로 1차 보정/검증
           - correct_answer: int/문자형 숫자/보기 텍스트 → 최종적으로 int(1~5)로 정규화
        2) extra_checks로 유형 특화 검증
        3) 보정된 값을 상위로 반영
        """
        model = MCQModel(**data)
        fixed = model.model_dump()  # correct_answer는 int(1~5)로 들어있음
        self.extra_checks(fixed)
        return MCQModel(**fixed)

    def extra_checks(self, data: dict):
        return

    def json_schema(self) -> dict:
        return MCQModel.model_json_schema()

    def repair_budget(self) -> dict:
        return {"fixer": 1, "regen": 1, "timeout_s": 15}
