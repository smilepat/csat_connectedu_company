# app/specs/rc_set.py
from .base import ItemSpec, GenContext  # GenContext는 TypedDict라고 가정
from .utils import tidy_options, standardize_answer
from app.schemas.items_rc_set import RCSetModel

class RCSetSpec(ItemSpec):
    id = "RC_SET"
    
    def system_prompt(self) -> str:
        # 필요 시 조직 표준 시스템 프롬프트로 교체
        return (
            "You are an expert CSAT reading item generator. "
            "Return ONLY valid JSON that strictly matches the schema for RC set items. "
            "Do not include any extra keys or commentary."
        )
    
    def build_prompt(self, *args, **kwargs) -> str:
        """
        호환 시그니처:
        - build_prompt(ctx: GenContext)               # ctx는 TypedDict (isinstance 금지)
        - build_prompt(passage: str, difficulty: str = "medium", *, topic: str = "random", item_id: str = "RC41")
        """
        from app.prompts.prompt_manager import PromptManager

        # ---- ctx 형태 감지: isinstance(GenContext) 금지 → 덕 타이핑으로 판별 ----
        if args:
            first = args[0]
            # dict 또는 dict 유사 객체이면서 .get이 있고, 우리가 기대하는 키 중 하나라도 포함되면 ctx로 간주
            if hasattr(first, "get") and any(k in first for k in ("item_id", "difficulty", "topic", "passage")):  # ✅ passage 키도 확인
                ctx = first  # TypedDict이든 일반 dict든 .get 사용
                item_id    = ctx.get("item_id") or "RC41"
                difficulty = ctx.get("difficulty") or "medium"
                topic      = ctx.get("topic") or "random"
                passage    = ctx.get("passage")  # ✅ 추가: passage 전달

                # ✅ passage를 PromptManager로 넘김 (없으면 None이므로 내부 가드에 의해 미주입)
                return PromptManager.generate(item_id, difficulty, topic, passage=passage)

        # ---- (passage, difficulty) 형태 호환 ----
        # passage는 세트 프롬프트에서 직접 쓰지 않지만 인터페이스 통일을 위해 받습니다.
        passage    = args[0] if args else kwargs.get("passage")               # ✅ 그대로 전달
        difficulty = (args[1] if len(args) > 1 else kwargs.get("difficulty")) or "medium"
        topic      = kwargs.get("topic") or "random"
        item_id    = kwargs.get("item_id") or "RC41"

        # ✅ 여기서도 passage를 PromptManager로 넘김
        return PromptManager.generate(item_id, difficulty, topic, passage=passage)

    def normalize(self, data: dict) -> dict:
        d = dict(data or {})
        set_instruction = (d.get("set_instruction") or d.get("instruction") or "").strip() or None

        # passage or passage_parts 모두 수용
        passage = (d.get("passage") or "").strip() or None
        parts = d.get("passage_parts") or {}
        if isinstance(parts, dict):
            parts = {str(k).strip(): str(v).strip() for k, v in parts.items() if str(v).strip()}
        else:
            parts = {}

        qs_in = d.get("questions") or []
        qs_out = []
        for q in qs_in:
            qq = dict(q or {})
            qs_out.append({
                "question": (qq.get("question") or "").strip(),
                "options": tidy_options(qq.get("options") or []),
                "correct_answer": standardize_answer(qq.get("correct_answer") or qq.get("answer") or ""),
                "explanation": (qq.get("explanation") or qq.get("rationale") or "").strip() or None,
            })

        out = {
            "type": "RC_SET",
            "set_instruction": set_instruction,
            "questions": qs_out,
        }
        if parts:
            out["passage_parts"] = parts
        else:
            out["passage"] = passage or ""

        return out

    def validate(self, data: dict):
        return RCSetModel(**data)

    def json_schema(self) -> dict:
        try:
            return RCSetModel.model_json_schema()
        except Exception:
            return RCSetModel.schema()

    def repair_budget(self) -> dict:
        return {"fixer": 1, "regen": 1, "timeout_s": 15}
