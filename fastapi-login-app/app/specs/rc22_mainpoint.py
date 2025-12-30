# app/specs/rc22_mainpoint.py
from __future__ import annotations
from pydantic import BaseModel, Field, validator

from app.specs.base import ItemSpec, GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like

class RC22Model(BaseModel):
    """
    RC22: 요지(Main Point) — 5지선다 MCQ
    """
    question: str
    passage: str
    options: list[str] = Field(min_length=5, max_length=5)
    correct_answer: str
    explanation: str

    @validator("question", "passage", "explanation", pre=True)
    def _strip(cls, v):
        return (v or "").strip()

class RC22Spec(ItemSpec):
    """
    RC22 전용 스펙: prompt_data.py 템플릿을 PromptManager.generate로 호출.
    passage는 스펙에서 직접 주입.
    """
    id = "RC22"

    def system_prompt(self) -> str:
        return (
            "CSAT English RC22 (Main Point). "
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
        return coerce_mcq_like(data)

    def validate(self, data: dict):
        RC22Model(**data)

    def json_schema(self) -> dict:
        return RC22Model.model_json_schema()

    def repair_budget(self) -> dict:
        return {"fixer": 1, "regen": 1, "timeout_s": 15}
