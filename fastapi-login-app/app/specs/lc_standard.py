# app/specs/lc_standard.py
from .base import ItemSpec, GenContext
from app.prompts.prompt_manager import PromptManager
from app.schemas.items_lc import (LCStandardModel, LCChartModel, LCSetModel, lc_union_json_schema)
from .utils import tidy_options, standardize_answer, coerce_transcript

class LCStandardSpec(ItemSpec):
    id = "LC_STANDARD"

    def build_prompt(self, ctx: GenContext) -> str:
        # PromptManager가 item_id를 정규화해서 적절한 템플릿을 고릅니다.
        from app.prompts.prompt_manager import PromptManager
        return PromptManager.generate(ctx.get("item_id") or self.id,
                                      ctx.get("difficulty"),
                                      ctx.get("topic"))

    def normalize(self, data: dict) -> dict:
        d = dict(data or {})
        # 공통 정규화
        norm = {
            "transcript": coerce_transcript(d.get("transcript")),
            "question": (d.get("question") or "").strip(),
            "options": tidy_options(d.get("options") or []),
            "correct_answer": standardize_answer(d.get("correct_answer") or d.get("answer") or ""),
            "explanation": (d.get("explanation") or d.get("rationale") or "").strip(),
            "audio_url": d.get("audio_url"),
        }
        # 형태 판정 (세트/차트/단일)
        if isinstance(d.get("questions"), list) and d["questions"]:
            qs = []
            for q in d["questions"]:
                qs.append({
                    "question": (q.get("question") or "").strip(),
                    "options": tidy_options(q.get("options") or []),
                    "correct_answer": standardize_answer(q.get("correct_answer") or q.get("answer") or ""),
                    "explanation": (q.get("explanation") or q.get("rationale") or "").strip(),
                })
            return {
                "type": "LC_SET",
                "set_instruction": (d.get("set_instruction") or d.get("instruction") or "").strip() or None,
                "transcript": norm["transcript"] or None,
                "questions": qs,
            }
        if d.get("chart_data") is not None:
            return {"type": "LC_CHART", **norm, "chart_data": d.get("chart_data")}
        return {"type": "LC_STANDARD", **norm}

    def validate(self, data: dict):
        t = (data or {}).get("type")
        if t == "LC_CHART":
            return LCChartModel(**data)
        if t == "LC_SET":
            return LCSetModel(**data)
        return LCStandardModel(**data)

    def json_schema(self) -> dict:
        return lc_union_json_schema()

    def repair_budget(self) -> dict:
        return {"fixer": 1, "regen": 1, "timeout_s": 12}
