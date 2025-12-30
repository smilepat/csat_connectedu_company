# app/specs/rc24_title.py

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, validator

from app.specs.base import ItemSpec, GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like
import re

class RC24Model(BaseModel):
    question: str
    passage: str
    options: list[str] = Field(min_length=5, max_length=5)
    correct_answer: str
    explanation: str

    @validator("question", "passage", "explanation", pre=True)
    def _strip(cls, v):
        return (v or "").strip()


class RC24Spec(ItemSpec):
    id = "RC24"

    def system_prompt(self) -> str:
        return (
            "CSAT English RC24 (Title). "
            "Return ONLY JSON matching the schema. "
            "Use ONLY the provided passage. Do NOT invent or substitute a new passage."
        )

    def build_prompt(self, ctx: GenContext) -> str:
        return PromptManager.generate(
            item_type=self.id,
            difficulty=(ctx.get("difficulty") or "medium"),
            topic_code=(ctx.get("topic") or "random"),
            passage=(ctx.get("passage") or ""),
        )

    def normalize(self, data: dict) -> dict:
        """
        - 필드 별칭 흡수: stimulus→passage, question_stem→question
        - passage 줄바꿈/중복 공백 정리
        - correct_answer 교정(①~⑤, 1~5, 또는 정답이 보기 텍스트인 경우 인덱스로)
        - 옵션 5개로 고정
        - 스키마 외 필드 제거
        """
        x = coerce_mcq_like(data)

        # --- 1) 필드 별칭 흡수 ---
        # passage 비어있고 stimulus가 있으면 사용
        if not (x.get("passage") or "").strip():
            stim = (data.get("stimulus") or "").strip()
            if stim:
                x["passage"] = stim

        # question 비어있고 question_stem이 있으면 사용, 여전히 없으면 기본 발문
        if not (x.get("question") or "").strip():
            qstem = (data.get("question_stem") or "").strip()
            x["question"] = qstem or "다음 글의 제목으로 가장 적절한 것은?"

        # --- 2) passage 정리 (\n, \r → 공백; 중복 공백 축소) ---
        passage = (x.get("passage") or "").strip()
        passage = re.sub(r"[\r\n]+", " ", passage)
        passage = re.sub(r"\s{2,}", " ", passage).strip()
        x["passage"] = passage

        # --- 3) 옵션 정리: 정확히 5개만 사용 ---
        opts = list(x.get("options") or [])[:5]
        # 번호/불릿 제거(안전)
        def _strip_marker(s: str) -> str:
            s = str(s or "").strip()
            s = re.sub(r"^\s*(?:[①-⑤]|[1-5][\.\)\-:]?)\s*", "", s)
            return re.sub(r"\s{2,}", " ", s).strip()
        opts = [_strip_marker(o) for o in opts]
        x["options"] = opts

        # --- 4) correct_answer 교정 ---
        raw = str(x.get("correct_answer", "")).strip()
        MAP = {"①":"1","②":"2","③":"3","④":"4","⑤":"5",
               "1":"1","2":"2","3":"3","4":"4","5":"5"}
        ca = MAP.get(raw, raw)

        if ca not in {"1","2","3","4","5"}:
            # 정답이 보기 텍스트인 경우 인덱스로
            target = raw.lower()
            idx = next((i+1 for i, o in enumerate(opts)
                        if str(o or "").strip().lower() == target), None)
            if idx is not None:
                ca = str(idx)

        x["correct_answer"] = ca

        # --- 5) 스키마 외 필드 제거 (item 내부에 붙는 잡필드 정리) ---
        for k in ["vocabulary_difficulty", "low_frequency_words", "rationale", "stimulus", "question_stem"]:
            x.pop(k, None)

        return x

    def validate(self, data: dict):
        RC24Model(**data)
        if data.get("correct_answer") not in {"1","2","3","4","5"}:
            raise ValueError("correct_answer must be a string in '1'..'5'")

    def json_schema(self) -> dict:
        return RC24Model.model_json_schema()

    def repair_budget(self) -> dict:
        return {"fixer": 1, "regen": 1, "timeout_s": 15}
