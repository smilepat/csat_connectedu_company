from __future__ import annotations

from typing import Optional, Tuple
import re
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.specs.base import GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like


class RC40Model(BaseModel):
    """
    RC40 (요약문 완성) - 단순화 스키마
    필수: question, passage, summary_template, options(5), correct_answer("1"~"5"), explanation
    선택: summary_A, summary_B (존재 시에만 가볍게 품질 체크)
    """
    model_config = ConfigDict(extra="ignore")  # rationale 등 여분 필드는 무시

    # 필수 MCQ 필드
    question: str
    passage: str
    summary_template: str
    options: list[str] = Field(min_length=5, max_length=5)
    correct_answer: str  # "1"~"5"
    explanation: str

    # 선택 필드 (모델이 생략해도 OK)
    summary_A: Optional[str] = None
    summary_B: Optional[str] = None

    @field_validator(
        "question","passage","summary_template","explanation","correct_answer",
        "summary_A","summary_B", mode="before"
    )
    @classmethod
    def _strip_text(cls, v):
        return (v or "").strip() if v is not None else v

    @field_validator("options", mode="before")
    @classmethod
    def _opts(cls, v):
        return [str(o).strip() for o in (v or [])]


class RC40Spec:
    id = "RC40"

    def system_prompt(self) -> str:
        # 출력 완결과 스키마 최소화 안내
        return (
            "CSAT English RC40 (Summary Completion). "
            "Return ONLY a syntactically complete JSON object with fields: "
            "{question, passage, summary_template, options[5], correct_answer('1'..'5'), explanation}. "
            "summary_A and summary_B are OPTIONAL helper fields; include them only if useful. "
            "Use ONLY the provided passage. Do NOT truncate arrays or leave dangling commas/quotes. "
            "correct_answer MUST be one of '1','2','3','4','5' (a string)."
        )

    def build_prompt(self, ctx: GenContext) -> str:
        item_type = (ctx.get("item_id") or self.id)
        return PromptManager.generate(
            item_type=item_type,
            difficulty=(ctx.get("difficulty") or "medium"),
            topic_code=(ctx.get("topic") or "random"),
            passage=(ctx.get("passage") or ""),
        )

    # ----------------------- helpers -----------------------
    def _answer_to_index(self, answer: str, options: list[str]) -> str:
        """정답을 항상 '1'~'5' 문자열로 수렴."""
        if answer is None:
            return ""
        a = str(answer).strip()
        if a in {"1","2","3","4","5"}:
            return a
        if a.isdigit() and 1 <= int(a) <= 5:
            return str(int(a))
        # 선택지 문자열로 온 경우
        try:
            idx = options.index(a)
            return str(idx + 1)
        except Exception:
            return a  # 검증에서 걸리게 둠

    def _split_ab_from_option(self, opt: str) -> Tuple[str, str]:
        """옵션 문자열에서 (A)/(B) 파트를 분리."""
        s = (opt or "").strip()
        m = re.search(r"\(A\)\s*:?\s*(.*?)\s*[-–—]\s*\(B\)\s*:?\s*(.*)$", s)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        parts = re.split(r"\s*[-–—]\s*", s, maxsplit=1)
        if len(parts) == 2:
            def _clean(x: str) -> str:
                x = x.strip()
                x = re.sub(r"^\(A\)\s*:?\s*", "", x)
                x = re.sub(r"^\(B\)\s*:?\s*", "", x)
                return x.strip()
            A = _clean(parts[0]); B = _clean(parts[1])
            if A and B:
                return A, B
        return "", ""

    def _is_core_incomplete(self, d: dict) -> bool:
        """핵심 필수 필드 기반으로만 미완성 출력 감지 (단순화)."""
        required = ["question", "passage", "summary_template", "options", "correct_answer", "explanation"]
        for k in required:
            if k not in d:
                return True
            if isinstance(d[k], str) and not d[k].strip():
                return True
        if not isinstance(d.get("options"), list) or len(d["options"]) != 5:
            return True
        return False

    # ----------------------- normalize -----------------------
    def normalize(self, data: dict) -> dict:
        d = coerce_mcq_like(data)

        # 정답을 '1'~'5'로 강제
        if d.get("options") and d.get("correct_answer") is not None:
            d["correct_answer"] = self._answer_to_index(d["correct_answer"], d["options"])

        # summary_A/B 없으면 "보조적으로만" 복원 시도 (없어도 실패 X)
        has_a = bool(str(d.get("summary_A") or "").strip())
        has_b = bool(str(d.get("summary_B") or "").strip())
        if (not has_a or not has_b) and d.get("options") and str(d.get("correct_answer") or "").isdigit():
            idx = int(d["correct_answer"]) - 1
            if 0 <= idx < len(d["options"]):
                a, b = self._split_ab_from_option(d["options"][idx])
                if not has_a and a:
                    d["summary_A"] = a
                if not has_b and b:
                    d["summary_B"] = b

        # 핵심 필드 기준으로만 미완성 판정
        if self._is_core_incomplete(d):
            raise ValueError("INCOMPLETE_OUTPUT_REGEN")

        return d

    # ----------------------- validate -----------------------
    def validate(self, data: dict):
        m = RC40Model.model_validate(data)

        # 옵션 중복 방지
        if len(set(o.lower() for o in m.options)) < 5:
            raise ValueError("RC40 options must be distinct (avoid near duplicates).")

        # 정답 형식 확인
        ca = str(m.correct_answer).strip()
        if ca not in {"1","2","3","4","5"}:
            raise ValueError("RC40 correct_answer must be one of '1','2','3','4','5'.")

        # 요약 A/B는 선택: 있으면만 간단 품질 체크(너무 짧은 단어 지양)
        if (m.summary_A and len(m.summary_A.split()) < 1) or (m.summary_B and len(m.summary_B.split()) < 1):
            raise ValueError("RC40 summary_A/summary_B, if present, should be meaningful terms/phrases.")

        return m

    def json_schema(self) -> dict:
        return RC40Model.model_json_schema()

    def repair_budget(self) -> dict:
        # truncation 대비 재생성 여유는 유지
        return {"fixer": 2, "regen": 3, "timeout_s": 28}
