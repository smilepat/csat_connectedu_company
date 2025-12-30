# app/specs/rc18_purpose.py
from __future__ import annotations
from pydantic import BaseModel, Field, validator

from app.specs.base import ItemSpec, GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like

class RC18Model(BaseModel):
    """
    RC18: 목적(purpose) 파악 — 5지선다 MCQ 공통 스키마
    """
    question: str
    passage: str
    options: list[str] = Field(min_length=5, max_length=5)
    correct_answer: str
    explanation: str

    @validator("question", "passage", "explanation", pre=True)
    def _strip(cls, v):
        return (v or "").strip()

class RC18Spec(ItemSpec):
    """
    RC18 전용 스펙: prompt_data.py 템플릿을 PromptManager.generate로 호출.
    - passage는 스펙에서 직접 주입(스펙 경로에서는 generate_item이 추가 주입하지 않음).
    """
    id = "RC18"

    def system_prompt(self) -> str:
        # 시스템 프롬프트: passage 고정 사용을 명시
        return (
            "CSAT English RC18 (Purpose). "
            "Return ONLY JSON matching the schema. "
            "Use ONLY the provided passage. Do NOT invent or substitute a new passage."
        )

    def build_prompt(self, ctx: GenContext) -> str:
        # BASE + RC18 템플릿 + 난이도/토픽 인스트럭션 + passage 주입 + OUTPUT RULES
        return PromptManager.generate(
            item_type=self.id,
            difficulty=(ctx.get("difficulty") or "medium"),
            topic_code=(ctx.get("topic") or "random"),
            passage=(ctx.get("passage") or ""),
        )

    # ---------- 품질 보정/검증 ----------
    def normalize(self, data: dict) -> dict:
        # 다양한 키 변형을 표준 MCQ 형태로 정규화
        x = coerce_mcq_like(data)
        return x

    def validate(self, data: dict):
        RC18Model(**data)

    def json_schema(self) -> dict:
        return RC18Model.model_json_schema()

    def repair_budget(self) -> dict:
        # 기본 예산: 1회 fixer, 1회 재생성, 15초 타임아웃
        return {"fixer": 1, "regen": 1, "timeout_s": 15}
