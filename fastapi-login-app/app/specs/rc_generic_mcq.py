# app/specs/rc_generic_mcq.py
from app.specs.base import ItemSpec, GenContext
from app.specs.utils import coerce_mcq_like
from app.schemas.items_rc34 import RC34Model  # 표준 MCQ 스키마

class RCGenericMCQSpec(ItemSpec):
    id = "RC_GENERIC"

    def build_prompt(self, ctx: GenContext) -> str:
        # ✅ 지연 임포트로 순환 참조 차단
        from app.prompts.prompt_manager import PromptManager
        # ✅ 하드코딩 대신 Path의 item_id를 넘겨 PromptManager에서 정규화(B안)
        item_code = (ctx.get("item_id") or "RC34")
        return PromptManager.generate(item_code, ctx.get("difficulty") or "medium", ctx.get("topic") or "random")

    def normalize(self, data: dict) -> dict:
        d = coerce_mcq_like(data)
        # rationale → explanation 호환
        if "explanation" not in d and "rationale" in d:
            d["explanation"] = (d.get("rationale") or "").strip()
            d.pop("rationale", None)
        return d

    def validate(self, data: dict):
        return RC34Model(**data)

    def json_schema(self) -> dict:
        return RC34Model.model_json_schema()

    def repair_budget(self) -> dict:
        return {"fixer": 1, "regen": 1, "timeout_s": 12}
