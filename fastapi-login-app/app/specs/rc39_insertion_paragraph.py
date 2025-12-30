from __future__ import annotations
import re
from typing import Dict
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.specs.base import GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like

_C2D: Dict[str, str] = {"①":"1","②":"2","③":"3","④":"4","⑤":"5"}

class RC39Model(BaseModel):
    """
    RC39: 문장 삽입(고난도) — 주어진 문장을 ①~⑤ 중 가장 적절한 위치에 삽입
    """
    model_config = ConfigDict(extra="ignore")

    question: str
    given_sentence: str
    passage: str
    options: list[str] = Field(min_length=5, max_length=5)
    correct_answer: str
    explanation: str

    @field_validator("question", "given_sentence", "passage", "explanation", "correct_answer", mode="before")
    @classmethod
    def _strip(cls, v): return str(v or "").strip()

    @field_validator("options", mode="before")
    @classmethod
    def _opts(cls, v): return [str(o).strip() for o in (v or [])]


class RC39Spec:
    id = "RC39"

    def system_prompt(self) -> str:
        return (
            "CSAT English RC39 (Advanced Sentence Insertion with ①~⑤ markers).\n"
            "Return ONLY one JSON object with fields:\n"
            "{"
            "\"question\": \"글의 흐름으로 보아, 주어진 문장이 들어가기에 가장 적절한 곳은? [3점]\", "
            "\"given_sentence\": \"<the sentence to insert>\", "
            "\"passage\": \"<text containing ( ① )...( ⑤ )>\", "
            "\"options\": [\"①\",\"②\",\"③\",\"④\",\"⑤\"], "
            "\"correct_answer\": \"1|2|3|4|5\", "
            "\"explanation\": \"<why that position fits (cohesion, reference, discourse markers, cause/effect, etc.)>\""
            "}\n"
            "Rules: JSON only; no markdown/code fences/comments; no trailing commas; valid JSON strings. "
            "Use ONLY the provided passage. Do NOT invent or substitute a new passage."
        )

    def build_prompt(self, ctx: GenContext) -> str:
        item_type = (ctx.get("item_id") or self.id)
        return PromptManager.generate(
            item_type=item_type,
            difficulty=(ctx.get("difficulty") or "medium"),
            topic_code=(ctx.get("topic") or "random"),
            passage=(ctx.get("passage") or "")
        )

    # ---------- helpers ----------
    def _answer_to_index(self, a: str) -> str:
        s = str(a or "").strip()
        if s in _C2D: return _C2D[s]
        if s in {"1","2","3","4","5"}: return s
        m = re.search(r"[①②③④⑤]", s)
        if m: return _C2D[m.group(0)]
        m2 = re.search(r"\b([1-5])\b", s)
        return m2.group(1) if m2 else s

    def _has_all_markers(self, passage: str) -> bool:
        return all(mark in (passage or "") for mark in ["①","②","③","④","⑤"])

    # ---------- normalize ----------
    def normalize(self, data: dict) -> dict:
        d = coerce_mcq_like(data or {})
        # 텍스트 필드 정리
        for k in ("question","given_sentence","passage","explanation"):
            d[k] = str(d.get(k) or "").strip()
        # 보기 고정
        d["options"] = ["①","②","③","④","⑤"]
        # 정답 표준화
        d["correct_answer"] = self._answer_to_index(d.get("correct_answer"))
        return d

    # ---------- validate ----------
    def validate(self, data: dict):
        m = RC39Model.model_validate(data)

        if not m.given_sentence or len(m.given_sentence) < 3:
            raise ValueError("RC39 requires a non-empty given_sentence.")

        if not self._has_all_markers(m.passage):
            raise ValueError("RC39 passage must contain all position markers ①~⑤.")

        if m.options != ["①","②","③","④","⑤"]:
            raise ValueError("RC39 options must be exactly ['①','②','③','④','⑤'].")

        if m.correct_answer not in {"1","2","3","4","5"}:
            raise ValueError("RC39 correct_answer must be one of '1','2','3','4','5'.")

        return m

    def json_schema(self) -> dict:
        return RC39Model.model_json_schema()

    def repair_budget(self) -> dict:
        return {"fixer": 1, "regen": 2, "timeout_s": 15}
