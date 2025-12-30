# app/specs/rc21_underlined_inference.py
from __future__ import annotations
from typing import Any
import re

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from app.specs.base import ItemSpec, GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like  # ✅ 표준화(라벨→숫자 문자열 등) 1차 처리


class RC21Model(BaseModel):
    """
    RC21: 함의/추론(Inference) — 5지선다 MCQ
    """
    question: str
    passage: str
    options: list[str] = Field(min_items=5, max_items=5)
    correct_answer: Any
    explanation: str

    # 🔹 추가: 어휘 정보 필드 (선택적)
    vocabulary_difficulty: str | None = None
    low_frequency_words: list[str] | None = None

    # v2: Config → model_config
    # 🔹 extra는 이제 forbid 말고 ignore 로 두는 걸 권장 (앞으로 필드 늘려도 안 터지게)
    model_config = ConfigDict(extra="ignore")

    @field_validator("question", "passage", "explanation", mode="before")
    @classmethod
    def _strip(cls, v):
        return (v or "").strip()

    @field_validator("correct_answer", mode="before")
    @classmethod
    def _coerce_numeric_like(cls, v):
        """
        - int면 그대로
        - "1"~"5" 같은 숫자 문자열이면 int로 변환
        - 그 외(보기 텍스트 가능)는 model_validator에서 처리
        """
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v

    # v2: @root_validator → @model_validator(mode="after")
    @model_validator(mode="after")
    def _finalize_answer(self):
        opts = list(self.options or [])
        ca = self.correct_answer

        # 보기 텍스트로 온 경우 → 인덱스(1-based)로 변환
        if not isinstance(ca, int):
            if isinstance(ca, str):
                try:
                    idx = opts.index(ca) + 1
                    ca = idx
                except ValueError:
                    raise ValueError(
                        "correct_answer must be numeric (1-5) or match one of the options exactly"
                    )
            else:
                raise ValueError(
                    "correct_answer must be an integer 1-5 or a numeric string '1'-'5'"
                )

        # 인덱스 범위 확인
        if not (1 <= int(ca) <= 5):
            raise ValueError("correct_answer must be in the range 1..5")

        # 간단한 옵션 포맷 수위 검증(번호·기호 접두 금지)
        bad_prefix = re.compile(r"^\s*(?:\(?\d+\)?[.)]|[①-⑤A-Ea-e])\s+")
        for o in opts:
            if bad_prefix.match(o or ""):
                raise ValueError("options_plain_text_only_violation")

        # v2에서는 self를 갱신하려면 copy(update=...)로 반환
        return self.model_copy(update={"correct_answer": int(ca)})


class RC21Spec(ItemSpec):
    """
    RC21 전용 스펙: PromptManager.generate 호출.
    passage는 스펙에서 직접 주입.
    """
    id = "RC21"

    def system_prompt(self) -> str:
        return (
            "CSAT English RC21 (Inference). "
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

    # ---------- 품질 보정/검증 ----------
    def normalize(self, data: dict) -> dict:
        """
        1) coerce_mcq_like: 필드명 표준화 + 라벨형 정답(①/A 등) → "1"~"5" 정규화
        2) correct_answer가 보기 텍스트면 → 1-based 인덱스로 치환
        3) "1"~"5" 문자열은 int로 변환
        4) 질문에 있는 <u>...</u> 대상 표현을 passage에도 반드시 밑줄로 싱크
        """
        x = coerce_mcq_like(data)  # question/options/correct_answer 1차 정규화

        # 보기 텍스트 → 인덱스
        ca = x.get("correct_answer")
        opts = x.get("options") or []
        if isinstance(ca, str) and not ca.isdigit() and opts:
            if ca in opts:
                x["correct_answer"] = opts.index(ca) + 1

        # 숫자 문자열 → int
        ca2 = x.get("correct_answer")
        if isinstance(ca2, str) and ca2.isdigit():
            x["correct_answer"] = int(ca2)

        # ── ★ 질문의 <u>...</u>를 passage에도 반영 ──
        q = x.get("question") or ""
        p = x.get("passage") or ""

        m = re.search(r"<u>(.*?)</u>", q)
        if m:
            target = (m.group(1) or "").strip()
            # 이미 passage에 <u>가 있으면 건드리지 않고,
            # 아직 밑줄이 없고, target 텍스트가 포함되어 있을 때만 첫 1회 치환.
            if target and "<u" not in p and target in p:
                x["passage"] = p.replace(target, f"<u>{target}</u>", 1)

        # 불필요 필드 제거
        x.pop("rationale", None)
        # 단어 정보 안 쓴다면 여기서 같이 제거해도 됨:
        # x.pop("vocabulary_difficulty", None)
        # x.pop("low_frequency_words", None)

        return x

    def validate(self, data: dict):
        RC21Model(**data)

    def json_schema(self) -> dict:
        return RC21Model.model_json_schema()

    def repair_budget(self) -> dict:
        return {"fixer": 1, "regen": 1, "timeout_s": 15}
