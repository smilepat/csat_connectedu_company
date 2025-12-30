from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator
from app.specs.base import GenContext
from app.prompts.prompt_manager import PromptManager

# 표준 5패턴(실제 보기로 사용하는 패턴)
STANDARD_OPTIONS = [
    "(A)-(C)-(B)",
    "(B)-(A)-(C)",
    "(B)-(C)-(A)",
    "(C)-(A)-(B)",
    "(C)-(B)-(A)",
]
DIGITS = {"1", "2", "3", "4", "5"}
PART_KEYS = ("(A)", "(B)", "(C)")

# 논리적 순서 후보 6패턴 (진짜 자연스러운 순서는 여기서 선택)
ALL_PERMS_6 = [
    "(A)-(B)-(C)",
    "(A)-(C)-(B)",
    "(B)-(A)-(C)",
    "(B)-(C)-(A)",
    "(C)-(A)-(B)",
    "(C)-(B)-(A)",
]


class RC36Model(BaseModel):
    """
    RC36 — 순서 배열 (기본형, A/B/C 순서 맞추기)
    - question: "주어진 글 다음에 이어질 글의 순서로 가장 적절한 것은?"
    - intro_paragraph: 도입 문단
    - passage_parts: {"(A)": "...", "(B)": "...", "(C)": "..."}
    - options: 정확히 STANDARD_OPTIONS
    - correct_answer: "1".."5" (문자열 인덱스)
    - explanation: 필수, rationale: 선택
    """
    question: str
    intro_paragraph: str
    passage_parts: dict
    options: list[str] = Field(min_length=5, max_length=5)
    correct_answer: str
    explanation: str
    rationale: str | None = None

    @field_validator("question", "intro_paragraph", "explanation", "rationale", mode="before")
    @classmethod
    def _strip_text(cls, v):
        return (v or "").strip()

    @field_validator("options", mode="before")
    @classmethod
    def _opts(cls, v):
        return [str(o).strip() for o in (v or [])]

    @field_validator("correct_answer", mode="before")
    @classmethod
    def _coerce_ca(cls, v):
        return str(v).strip()

    @model_validator(mode="after")
    def _check_all(self):
        # 1) 질문 고정 문구(최소 일치: 공백 제거 비교)
        q = (self.question or "").replace(" ", "")
        must = "주어진글다음에이어질글의순서로가장적절한것은?"
        if q != must:
            raise ValueError("RC36 question must be exactly '주어진 글 다음에 이어질 글의 순서로 가장 적절한 것은?'")

        # 2) passage_parts 키 검사
        parts = self.passage_parts or {}
        if not all(k in parts for k in PART_KEYS):
            raise ValueError("RC36 passage_parts must include '(A)', '(B)', '(C)'.")
        # 최소 길이(너무 짧은 생성 방지)
        for k in PART_KEYS:
            if len((parts.get(k) or "").split()) < 5:
                raise ValueError(f"RC36 passage_parts[{k}] is too short (need ≥ 5 words).")

        # 3) options는 표준 5패턴과 동일해야 함
        if self.options != STANDARD_OPTIONS:
            raise ValueError("RC36 options must match the standard 5 patterns exactly.")

        # 4) 정답은 '1'..'5' 문자열
        if self.correct_answer not in DIGITS:
            raise ValueError("RC36 correct_answer must be a string digit from '1' to '5'.")
        return self


class RC36Spec:
    id = "RC36"

    # ============================
    # 기본 생성(system) 프롬프트
    # ============================
    def system_prompt(self) -> str:
        # 생성 모드는 지금도 natural_order를 쓰도록 유지할 수 있지만
        # 인용 모드가 문제의 핵심이라, 여기서는 간단히 둡니다.
        return (
            "CSAT English RC36 (ordering: arrange A/B/C after the intro).\n"
            "If NO passage is provided, CREATE:\n"
            "- an intro_paragraph (40–70 words),\n"
            "- three continuation parts labeled (A), (B), (C) (each 35–70 words).\n"
            "Set options EXACTLY to: ['(A)-(C)-(B)','(B)-(A)-(C)','(B)-(C)-(A)','(C)-(A)-(B)','(C)-(B)-(A)'].\n"
            "Set correct_answer to a STRING digit '1'..'5' (index of the correct option).\n"
            "Return ONLY JSON with fields: question, intro_paragraph, passage_parts, options, "
            "correct_answer, explanation[, rationale]."
        )

    def build_prompt(self, ctx: GenContext) -> str:
        item_type = (ctx.get("item_id") or self.id)
        return PromptManager.generate(
            item_type=item_type,
            difficulty=(ctx.get("difficulty") or "medium"),
            topic_code=(ctx.get("topic") or "random"),
            passage=(ctx.get("passage") or ""),
        )

    # ============================
    # 공통 normalize
    # ============================
    def normalize(self, data: dict) -> dict:
        d = dict(data or {})
        # trim
        for k in ("question", "intro_paragraph", "explanation", "rationale"):
            if isinstance(d.get(k), str):
                d[k] = d[k].strip()

        # passage_parts 키/값 공백 정리
        pp = d.get("passage_parts") or {}
        fixed_pp = {}
        for k in PART_KEYS:
            fixed_pp[k] = str(pp.get(k, "")).strip()
        d["passage_parts"] = fixed_pp

        # options 표준화
        d["options"] = STANDARD_OPTIONS.copy()

        # correct_answer가 패턴 문자열로 왔을 경우 보정
        ca = str(d.get("correct_answer", "")).strip()
        if ca in STANDARD_OPTIONS:
            d["correct_answer"] = str(STANDARD_OPTIONS.index(ca) + 1)
        else:
            d["correct_answer"] = ca  # 이미 "1".."5"면 그대로

        return d

    # ============================
    # 기본 validate / schema / repair
    # ============================
    def validate(self, data: dict):
        return RC36Model.model_validate(data)

    def json_schema(self) -> dict:
        return RC36Model.model_json_schema()

    def repair_budget(self) -> dict:
        return {"fixer": 1, "regen": 1, "timeout_s": 18}

    # ============================
    # 인용(quote) 모드 지원
    # ============================
    def has_quote_support(self) -> bool:
        return True

    def quote_build_prompt(self, passage: str) -> str:
        """
        RC36 QUOTE MODE (지문 재구성 허용 버전)

        - LLM은 PASSAGE를 바탕으로 intro_paragraph + (A)(B)(C) 3단락을
          '의미는 유지하되, 시험용 RC36 구조에 맞게' 재구성할 수 있다.
        - 최종적으로 (A)(B)(C)의 가장 자연스러운 순서를
          5개 보기 패턴 중 하나로 맞추도록 한다.
        """

        base_question = "주어진 글 다음에 이어질 글의 순서로 가장 적절한 것은?"
        # 시험에서 실제로 사용하는 5개 보기 패턴
        opts_str = (
            '["(A)-(C)-(B)", "(B)-(A)-(C)", "(B)-(C)-(A)", '
            '"(C)-(A)-(B)", "(C)-(B)-(A)"]'
        )

        return (
            "You will create a CSAT English RC36 item (paragraph ordering) in QUOTE MODE.\n\n"
            "=============================\n"
            "OVERALL GOAL\n"
            "=============================\n"
            "You are given a PASSAGE. Your task is to RECONSTRUCT it into:\n"
            "- one introductory paragraph (intro_paragraph), and\n"
            "- three continuation paragraphs labeled (A), (B), (C).\n\n"
            "You MAY lightly rewrite, merge, or split sentences to improve coherence,\n"
            "as long as you PRESERVE the original meaning and key information.\n"
            "Do NOT invent clearly new facts that contradict the passage.\n\n"
            "=============================\n"
            "RULES ABOUT RECONSTRUCTION\n"
            "=============================\n"
            "1) Read the PASSAGE and understand its main topic and logical flow.\n"
            "2) Construct an intro_paragraph that sets up the topic and context of the passage.\n"
            "   - You may copy, reorder, or lightly paraphrase sentences from the beginning of the PASSAGE.\n"
            "   - The intro_paragraph should be 40–80 words in English.\n"
            "3) Construct three continuation paragraphs (A), (B), (C):\n"
            "   - Each paragraph should be 35–80 words in English.\n"
            "   - You may reorganize sentences from the PASSAGE, merge or split them,\n"
            "     and adjust connectors so that each paragraph is coherent.\n"
            "   - You MUST preserve the overall meaning and important details of the PASSAGE.\n"
            "4) You are ALLOWED to slightly rearrange the order of information across (A), (B), (C)\n"
            "   so that there is a SINGLE most natural logical order among the three.\n\n"
            "IMPORTANT:\n"
            "- Do NOT simply copy the original paragraph boundaries if that makes only (A)-(B)-(C) natural.\n"
            "- Instead, adjust which ideas go into (A), (B), (C) so that exactly ONE of the 5 patterns\n"
            "  below is clearly the most natural logical order.\n\n"
            "=============================\n"
            "NATURAL ORDER (5 patterns ONLY)\n"
            "=============================\n"
            "You MUST choose the SINGLE most natural logical order of (A), (B), (C)\n"
            "from the following 5 patterns ONLY:\n"
            f"  {opts_str}\n\n"
            "Call this 'gold_order'. It MUST be one of those 5 patterns.\n"
            "- Do NOT use '(A)-(B)-(C)' as gold_order.\n"
            "- If your reconstruction would make '(A)-(B)-(C)' the best order,\n"
            "  you MUST modify the paragraph boundaries or sentence order so that\n"
            "  one of the 5 patterns above becomes clearly the most natural order.\n\n"
            "=============================\n"
            "QUESTION FORMAT\n"
            "=============================\n"
            f"- question MUST be exactly: \"{base_question}\"\n"
            f"- options MUST be EXACTLY: {opts_str}\n"
            "- explanation MUST explain in Korean why your gold_order is logically correct.\n"
            "- rationale is optional (can be an empty string).\n\n"
            "=============================\n"
            "STRICT JSON OUTPUT FORMAT\n"
            "=============================\n"
            "{\n"
            f"  \"question\": \"{base_question}\",\n"
            "  \"intro_paragraph\": \"[Introductory paragraph in English]\",\n"
            "  \"passage_parts\": {\n"
            "    \"(A)\": \"[Paragraph A in English]\",\n"
            "    \"(B)\": \"[Paragraph B in English]\",\n"
            "    \"(C)\": \"[Paragraph C in English]\"\n"
            "  },\n"
            f"  \"options\": {opts_str},\n"
            "  \"gold_order\": \"(A)-(C)-(B)\" | \"(B)-(A)-(C)\" | \"(B)-(C)-(A)\" | "
            "\"(C)-(A)-(B)\" | \"(C)-(B)-(A)\",\n"
            "  \"explanation\": \"[Korean explanation of the logical order]\",\n"
            "  \"rationale\": \"[optional or empty string]\"\n"
            "}\n\n"
            "- Output ONLY this JSON object. No extra text.\n\n"
            "PASSAGE:\n" + (passage or "")
        )

    def quote_postprocess(self, passage: str, llm_json: dict) -> dict:
        """
        QUOTE MODE 후처리 (재구성 허용 버전)

        1) LLM이 재구성한 intro_paragraph / passage_parts를 받아서 정리한다.
        2) gold_order가 STANDARD_OPTIONS 중 하나인지 확인한다.
        3) 해당 패턴의 index를 이용해 correct_answer를 계산한다.
        """

        base_question = "주어진 글 다음에 이어질 글의 순서로 가장 적절한 것은?"

        intro = (llm_json.get("intro_paragraph") or "").strip()
        raw_pp = llm_json.get("passage_parts") or {}
        fixed_pp = {k: str(raw_pp.get(k, "")).strip() for k in PART_KEYS}

        explanation = (llm_json.get("explanation") or "").strip()
        rationale_raw = (llm_json.get("rationale") or "").strip()
        rationale = rationale_raw or None

        gold = llm_json.get("gold_order")
        if not isinstance(gold, str):
            raise ValueError("RC36 quote_mode requires 'gold_order' as a string.")

        gold_compact = gold.replace(" ", "")
        matched_opt = None
        for opt in STANDARD_OPTIONS:
            if opt.replace(" ", "") == gold_compact:
                matched_opt = opt
                break

        if matched_opt is None:
            raise ValueError(
                f"RC36 quote_mode: gold_order must be one of STANDARD_OPTIONS {STANDARD_OPTIONS}, "
                f"got: {gold}"
            )

        correct_answer = str(STANDARD_OPTIONS.index(matched_opt) + 1)

        item = {
            "question": base_question,
            "intro_paragraph": intro,
            "passage_parts": fixed_pp,
            "options": STANDARD_OPTIONS.copy(),
            "correct_answer": correct_answer,
            "explanation": explanation,
            "rationale": rationale,
        }
        return item


    def quote_validate(self, item: dict) -> None:
        RC36Model.model_validate(item)
