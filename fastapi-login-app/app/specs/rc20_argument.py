# app/specs/rc20_claim.py

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.specs.base import ItemSpec, GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like


class RC20Model(BaseModel):
    """
    RC20: 주장/의무(Claim/Obligation) 파악 — 5지선다 MCQ 공통 스키마
    """
    question: str
    passage: str
    options: List[str] = Field(min_length=5, max_length=5)
    correct_answer: int  # ← 숫자(1~5)로 통일 권장
    explanation: str

    model_config = ConfigDict(extra="ignore")  # 여분 키(어휘 등) 무시

    @field_validator("question", "passage", "explanation", mode="before")
    @classmethod
    def _strip(cls, v):
        return (v or "").strip()

    @field_validator("correct_answer", mode="before")
    @classmethod
    def _coerce_ca(cls, v):
        # "1"/"A"/0-index 등 다양한 입력을 1~5 정수로 보정
        if isinstance(v, bool):
            v = int(v)
        if isinstance(v, (int, float)):
            vi = int(v)
            # 0~4면 1~5로 보정
            if 0 <= vi <= 4:
                return vi + 1
            return vi
        if isinstance(v, str):
            s = v.strip().upper()
            if s in {"A","B","C","D","E"}:
                return "ABCDE".index(s) + 1
            try:
                return int(s)
            except Exception:
                return 1
        return 1


class RC20Spec(ItemSpec):
    """
    RC20 전용 스펙
    """
    id = "RC20"

    def system_prompt(self) -> str:
        return (
            "CSAT English RC20 (Claim/Obligation). "
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

    # ✅ 추가: LLM 출력 키를 표준 스키마로 보정
    def repair(self, raw: Dict[str, Any], passage_text: Optional[str] = None) -> Dict[str, Any]:
        d = dict(raw) if isinstance(raw, dict) else {}

        # 1) 키 매핑
        if "passage" not in d:
            if isinstance(d.get("stimulus"), str):
                d["passage"] = d.pop("stimulus")
            elif passage_text:
                d["passage"] = passage_text
            else:
                d["passage"] = ""

        if "question" not in d:
            if isinstance(d.get("question_stem"), str):
                d["question"] = d.pop("question_stem")
            elif isinstance(d.get("question_text"), str):
                d["question"] = d.pop("question_text")
            else:
                d["question"] = "다음 글에서 필자가 주장하는 바로 가장 적절한 것은?"

        # 2) 선지 정리(문자열화, 5개로 자르기)
        opts = d.get("options")
        if not isinstance(opts, list):
            opts = []
        opts = [str(o) for o in opts][:5]
        # 5개 미만이면 임시로 채움(검증에서 걸러질 수 있으므로 최소 안전판)
        while len(opts) < 5:
            opts.append(f"선지 {len(opts)+1}")
        d["options"] = opts[:5]

        # 3) 정답 보정(0-index → 1-index, 문자 → 숫자)
        ca = d.get("correct_answer", 1)
        # 모델의 field_validator가 최종 보정하므로 여기선 기본값만 방어
        if ca in (0, "0"):
            ca = 1
        d["correct_answer"] = ca

        # 4) 해설 기본값
        if not isinstance(d.get("explanation"), str) or not d["explanation"].strip():
            d["explanation"] = "글의 중심 주장(결론/권고)에 직접 해당하는 선택지를 고른다."

        return d

    def normalize(self, data: dict) -> dict:
        # 공통 정형화(선지 공백 제거 등)
        return coerce_mcq_like(data)

    def validate(self, data: dict):
        RC20Model(**data)

    def json_schema(self) -> dict:
        return RC20Model.model_json_schema()

    def repair_budget(self) -> dict:
        return {"fixer": 1, "regen": 1, "timeout_s": 15}
