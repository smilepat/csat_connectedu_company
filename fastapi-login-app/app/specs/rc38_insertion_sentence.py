from __future__ import annotations
import re
from typing import Dict
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.specs.base import GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like

_CIRCLED_TO_DIGIT: Dict[str, str] = {"①":"1","②":"2","③":"3","④":"4","⑤":"5"}

class RC38Model(BaseModel):
    """
    RC38: 문장 삽입 (①~⑤ 위치 선택)
    - given_sentence(필수) + passage(①~⑤ 마커 포함) + options=①~⑤ + correct_answer("1"~"5")
    """
    model_config = ConfigDict(extra="ignore")  # 여분 필드는 무시

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


class RC38Spec:
    id = "RC38"

    def system_prompt(self) -> str:
        # JSON 규격을 명시적으로 강제하여 JSONDecodeError 발생 가능성 최소화
        return (
            "CSAT English RC38 (Sentence Insertion, ①~⑤ markers).\n"
            "Return ONLY a single JSON object with fields:\n"
            "{"
            "\"question\": \"글의 흐름으로 보아, 주어진 문장이 들어가기에 가장 적절한 곳은?\", "
            "\"given_sentence\": \"<the sentence to insert>\", "
            "\"passage\": \"<text containing markers ( ① )...( ⑤ )>\", "
            "\"options\": [\"①\",\"②\",\"③\",\"④\",\"⑤\"], "
            "\"correct_answer\": \"1|2|3|4|5\", "
            "\"explanation\": \"<why the position fits>\""
            "}\n"
            "Rules: No markdown, no code fences, no comments, no trailing commas; strings must be valid JSON strings. "
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
        if s in _CIRCLED_TO_DIGIT: return _CIRCLED_TO_DIGIT[s]
        if s in {"1","2","3","4","5"}: return s
        m = re.search(r"[①②③④⑤]", s)
        if m: return _CIRCLED_TO_DIGIT[m.group(0)]
        m2 = re.search(r"\b([1-5])\b", s)
        return m2.group(1) if m2 else s

    def _has_all_markers(self, passage: str) -> bool:
        # ①~⑤ 모두 존재해야 함 (괄호 유무는 허용)
        return all(mark in passage for mark in ["①","②","③","④","⑤"])

    # ---------- normalize ----------
    def normalize(self, data: dict) -> dict:
        d = coerce_mcq_like(data or {})

        # 필드 정리
        d["question"] = str(d.get("question") or "").strip()
        d["given_sentence"] = str(d.get("given_sentence") or "").strip()
        d["passage"] = str(d.get("passage") or "").strip()
        d["explanation"] = str(d.get("explanation") or "").strip()

        # 보기 강제: 무조건 표준 세트
        d["options"] = ["①","②","③","④","⑤"]

        # 정답 표준화
        d["correct_answer"] = self._answer_to_index(d.get("correct_answer"))

        # 지문 내 마커 주변 공백/괄호 변형 허용: 별도 정규화는 불필요, 검증에서 존재만 확인
        return d

    # ---------- validate ----------
    def validate(self, data: dict):
        m = RC38Model.model_validate(data)

        if not m.given_sentence or len(m.given_sentence) < 3:
            raise ValueError("RC38 requires a non-empty given_sentence.")

        if not self._has_all_markers(m.passage):
            raise ValueError("RC38 passage must contain all position markers ①~⑤.")

        if m.options != ["①","②","③","④","⑤"]:
            raise ValueError("RC38 options must be exactly ['①','②','③','④','⑤'].")

        if m.correct_answer not in {"1","2","3","4","5"}:
            raise ValueError("RC38 correct_answer must be one of '1','2','3','4','5'.")

        return m

    def json_schema(self) -> dict:
        return RC38Model.model_json_schema()

    def repair_budget(self) -> dict:
        # JSON 파싱 실패를 줄이기 위해 재시도 여유를 소폭 확대해도 좋습니다.
        return {"fixer": 1, "regen": 2, "timeout_s": 15}
