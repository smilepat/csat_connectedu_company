# app/specs/rc43_45_set.py
from __future__ import annotations
from typing import Any, Dict
from app.specs.base import ItemSpec, GenContext

class RC43_45SetSpec(ItemSpec):
    """
    RC43~RC45 세트 간단 버전 Spec.
    - 세트 문항 생성 (문단 순서, 지칭 추론, 내용 일치/불일치)
    - 복잡한 하드 밸리데이션 제거, 기본 필드만 체크
    """
    id = "RC43_45"

    def system_prompt(self) -> str:
        return (
            "You are generating a CSAT English RC43–RC45 (Long Reading Set). "
            "Return ONLY valid JSON with keys: item_type, set_instruction, passage_parts, questions. "
            "Include four paragraphs (A–D) and three questions (43,44,45). "
            "Options must be 5 choices each, correct_answer must be 1–5. "
        )

    # ---------- prompt ----------
    def build_prompt(self, ctx: GenContext) -> str:
        raw_passage = (ctx.get("passage") or "").strip()
        has_passage = bool(raw_passage)

        if has_passage:
            # 맞춤(지문 있음) → 편집형 프롬프트
            from app.prompts.prompt_manager import PromptManager
            from app.specs.passage_preprocessor import sanitize_user_passage
            cleaned = sanitize_user_passage(raw_passage)
            return PromptManager.generate(
                item_type="RC43_45_EDIT_ONE_FROM_CLEAN",
                difficulty=(ctx.get("difficulty") or "medium"),
                topic_code=(ctx.get("topic") or "random"),
                passage=cleaned,
            )

        # 일반(지문 없음) → 기본 세트 프롬프트
        from app.prompts.prompt_manager import PromptManager
        return PromptManager.generate(
            item_type=self.id,  # "RC43_45"
            difficulty=(ctx.get("difficulty") or "medium"),
            topic_code=(ctx.get("topic") or "random"),
            passage="",
        )

    # ---------- normalize ----------
    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        out["item_type"] = "RC_SET"
        out["set_instruction"] = data.get("set_instruction") or "[43~45] 다음 글을 읽고, 물음에 답하시오."
        out["passage_parts"] = data.get("passage_parts") or {"A": "", "B": "", "C": "", "D": ""}

        qs_in = data.get("questions") or []
        qs_out = []
        for i, q in enumerate(qs_in, start=43):
            if not isinstance(q, dict):
                continue
            qq = {
                "question_number": q.get("question_number") or i,
                "question": q.get("question") or "",
                "options": q.get("options") or ["1", "2", "3", "4", "5"],
                "correct_answer": str(q.get("correct_answer") or "1"),
                "explanation": q.get("explanation") or "",   # ✅ explanation 보장
            }
            qs_out.append(qq)

        out["questions"] = qs_out
        return out

    # ---------- validate ----------
    def validate(self, data: Dict[str, Any]):
        if not isinstance(data, dict):
            raise ValueError("Output must be a dict")
        if data.get("item_type") != "RC_SET":
            raise ValueError("item_type must be RC_SET")
        if "passage_parts" not in data:
            raise ValueError("Missing passage_parts")
        if "questions" not in data:
            raise ValueError("Missing questions")

        for q in data.get("questions", []):
            if "explanation" not in q:
                raise ValueError("Each question must include an explanation")

    def json_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "item_type": {"type": "string"},
                "set_instruction": {"type": "string"},
                "passage_parts": {"type": "object"},
                "questions": {"type": "array"},
            },
            "required": ["item_type", "set_instruction", "passage_parts", "questions"],
        }

    def repair_budget(self) -> dict:
        return {"fixer": 1, "regen": 1, "timeout_s": 15}
