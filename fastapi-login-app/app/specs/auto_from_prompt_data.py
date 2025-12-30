from __future__ import annotations
from typing import Iterable, Dict, Any, Optional

from pydantic import BaseModel, Field, validator

from app.specs.base import ItemSpec, GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like

# --- 공통 MCQ 스키마 ---
class _MCQModel(BaseModel):
    question: str
    passage: str
    options: list[str] = Field(min_length=5, max_length=5)
    correct_answer: str
    explanation: str

    @validator("question", "passage", "explanation", pre=True)
    def _strip(cls, v):
        return (v or "").strip()

# --- prompt_data.py를 참조하여 id별 설명/메타 가져오기 ---
def _load_prompt_meta(item_type: str) -> Dict[str, Any]:
    """
    prompt_data.py 의 ITEM_PROMPTS[item_type] 에서 가능한 메타 정보를 가져옵니다.
    존재하지 않는 키는 안전하게 무시합니다.
    """
    try:
        from app.prompts import prompt_data as PD  # prompt_data.py
    except Exception:
        return {}

    meta = {}
    try:
        raw = (PD.ITEM_PROMPTS or {}).get(item_type, {})
        if isinstance(raw, dict):
            meta.update(raw)
    except Exception:
        pass
    return meta

def _infer_description(item_type: str, meta: Dict[str, Any]) -> str:
    """
    system_prompt에 곁들일 간단 설명을 meta에서 추출.
    후보 키: desc, description, label, title, name
    없으면 item_type만 노출.
    """
    for k in ("desc", "description", "label", "title", "name"):
        v = meta.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return f"{item_type} item"

# --- 자동 스펙 ---
class _AutoSpec(ItemSpec):
    """
    prompt_data.py 의 ITEM_PROMPTS[item_type] 를 그대로 사용하여
    PromptManager.generate(...)를 호출하는 보일러플레이트 Spec.
    """
    def __init__(self, item_type: str, desc: str):
        self.id = item_type
        self._desc = desc

    # ItemSpec 인터페이스 구현
    def system_prompt(self) -> str:
        return (
            f"CSAT English {self.id} ({self._desc}). "
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
        return coerce_mcq_like(data)

    def validate(self, data: dict):
        _MCQModel(**data)

    def json_schema(self) -> dict:
        return _MCQModel.model_json_schema()

    def repair_budget(self) -> dict:
        # 필요시 튜닝하세요
        return {"fixer": 1, "regen": 1, "timeout_s": 15}

# --- 공개 팩토리: 특정 id들에 대해 Spec 딕셔너리 생성 ---
def build_auto_specs(item_ids: Iterable[str]) -> Dict[str, ItemSpec]:
    specs: Dict[str, ItemSpec] = {}
    for iid in item_ids:
        meta = _load_prompt_meta(iid)
        desc = _infer_description(iid, meta)
        specs[iid] = _AutoSpec(iid, desc)
    return specs
