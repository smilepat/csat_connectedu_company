from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator
from app.specs.base import GenContext
from app.prompts.prompt_manager import PromptManager

LABELS = ["①", "②", "③", "④", "⑤"]
DIGITS = {"1", "2", "3", "4", "5"}

class RC35Model(BaseModel):
    """
    RC35 — '그냥 생성' 전용 무관문장 스키마
    - question: 고정 문구 ("다음 글에서 전체 흐름과 관계 <u>없는</u> 문장은?")
    - passage: ①~⑤로 번호가 붙은 5문장 포함
    - options: ["①","②","③","④","⑤"] (정확히 이 형태)
    - correct_answer: "1".."5" 중 하나의 문자열 (반드시 숫자문자)
    - explanation: 필수
    - rationale: 선택(있으면 보존)
    """
    question: str
    passage: str
    options: list[str] = Field(min_length=5, max_length=5)
    correct_answer: str
    explanation: str
    rationale: str | None = None

    @field_validator("question", "passage", "explanation", "rationale", mode="before")
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
        v = str(v).strip()
        # ①~⑤로 들어오면 숫자문자 "1"~"5"로 변환
        if v in LABELS:
            return str(LABELS.index(v) + 1)
        return v

    @model_validator(mode="after")
    def _check_all(self):
        # 1) question 고정 문구(태그 포함) - 최소한의 일치만 강제
        q = (self.question or "").replace(" ", "")
        must = "다음글에서전체흐름과관계<u>없는</u>문장은?"
        if q.replace(" ", "") != must:
            raise ValueError("RC35 question must be exactly '다음 글에서 전체 흐름과 관계 <u>없는</u> 문장은?'")

        # 2) options 정확히 ①~⑤
        if self.options != LABELS:
            raise ValueError("RC35 options must be exactly ['①','②','③','④','⑤'].")

        # 3) correct_answer: 숫자문자 "1".."5"
        if self.correct_answer not in DIGITS:
            raise ValueError("RC35 correct_answer must be a string digit from '1' to '5'.")

        # 4) passage에 ①~⑤가 모두 1회 이상 존재(각각 등장)
        p = self.passage or ""
        if not all(lbl in p for lbl in LABELS):
            raise ValueError("RC35 passage must contain all numbered markers ①~⑤.")
        return self


class RC35Spec:
    id = "RC35"

    def system_prompt(self) -> str:
        # '그냥 생성'에서도 passage를 반드시 만들어 ①~⑤ 번호문장 5개로 구성하도록 강하게 지시
        return (
            "CSAT English RC35 (irrelevant sentence: 5 numbered sentences). "
            "Create a passage consisting of EXACTLY five sentences labeled ① to ⑤. "
            "Write the question EXACTLY as: '다음 글에서 전체 흐름과 관계 <u>없는</u> 문장은?'. "
            "Set options EXACTLY to ['①','②','③','④','⑤']. "
            "Set correct_answer to a STRING digit '1'..'5' (NOT a label). "
            "Explain briefly why the chosen sentence is unrelated to the overall flow. "
            "Return ONLY JSON matching the schema."
        )

    def build_prompt(self, ctx: GenContext) -> str:
        """
        - '그냥 생성'일 때도 PromptManager.generate가 이 스펙의 규칙을 따르도록 함
        - passage가 비어있으면 프롬프트에서 새로 생성(①~⑤ 번호문장 5개)
        - passage가 주어져도 그대로 사용 가능(단, ①~⑤가 포함되어야 함)
        """
        item_type = (ctx.get("item_id") or self.id)
        return PromptManager.generate(
            item_type=item_type,
            difficulty=(ctx.get("difficulty") or "medium"),
            topic_code=(ctx.get("topic") or "random"),
            passage=(ctx.get("passage") or ""),  # 비었으면 템플릿이 생성하도록 지시
        )

    def normalize(self, data: dict) -> dict:
        """
        - correct_answer가 ①~⑤로 들어오면 숫자문자 '1'..'5'로 변환
        - options는 강제로 ①~⑤로 맞춤(혹시 공백/다른 라벨이 오면 에러 전 일단 보정)
        """
        d = dict(data or {})
        # question/explanation/rationale strip
        for k in ("question", "explanation", "rationale", "passage"):
            if k in d and isinstance(d[k], str):
                d[k] = d[k].strip()

        # options 보정
        d["options"] = LABELS.copy()

        # correct_answer 보정
        ca = str(d.get("correct_answer", "")).strip()
        if ca in LABELS:
            ca = str(LABELS.index(ca) + 1)
        d["correct_answer"] = ca

        return d

    def validate(self, data: dict):
        return RC35Model.model_validate(data)

    def json_schema(self) -> dict:
        return RC35Model.model_json_schema()

    def repair_budget(self) -> dict:
        # 라벨/정답 형식 불일치 시 1회 fixer 후 재생성 1회까지 허용
        return {"fixer": 1, "regen": 1, "timeout_s": 18}

    # =========================
    # ✅ 인용(quote) 모드용 훅 추가
    # =========================
    def has_quote_support(self) -> bool:
        """
        인용 모드 지원 여부 플래그.
        - 라우터/파이프라인에서 RC35가 인용 모드 대상인지 확인할 때 사용.
        """
        return True

    def quote_build_prompt(self, passage: str) -> str:
        """
        RC35 인용(quote) 모드 프롬프트 생성.

        요구사항(사용자 지침 반영):
        1) 지문을 그대로 이용한다. (문장/순서 삭제·재배열 금지)
        2) 연속된 5문장의 앞에 숫자 ①~⑤를 붙인다.
        3) ①~⑤ 중 하나의 문장을 '전체 흐름과 무관한 문장'이 되도록 내용만 변형한다.
        4) 변형된 문장이 정답이 되며, correct_answer는 1~5 중 하나의 문자열이다.
        5) question 문구, options 형식은 RC35 스펙을 따른다.
        """
        base_question = "다음 글에서 전체 흐름과 관계 <u>없는</u> 문장은?"

        return (
            "You will create a CSAT English RC35 item (irrelevant sentence) in QUOTE MODE.\n\n"
            "## ABSOLUTE RULES ABOUT THE PASSAGE\n"
            "- You MUST use the given PASSAGE exactly as it is.\n"
            "- Do NOT delete, reorder, or paraphrase sentences outside the 5 chosen ones.\n"
            "- Choose FIVE CONSECUTIVE sentences from the PASSAGE.\n"
            "- Prepend each of the chosen five sentences with a circled numeral label in order:\n"
            "  ①, ②, ③, ④, ⑤.\n"
            "- The sentences BEFORE or AFTER this block must remain unchanged (no labels).\n\n"
            "## HOW TO CREATE THE IRRELEVANT SENTENCE\n"
            "1) Among the five labeled sentences (①~⑤), modify the content of EXACTLY ONE sentence\n"
            "   so that it becomes IRRELEVANT to the overall flow and main topic of the passage.\n"
            "2) The modified sentence must still be grammatical and natural in isolation, but it should\n"
            "   break the logical flow, be off-topic, or contradict the main idea.\n"
            "3) The OTHER FOUR sentences should remain consistent with the original passage's topic and flow.\n"
            "4) Do NOT change the order of the five sentences; only content of one sentence is edited.\n\n"
            "## QUESTION & OPTIONS\n"
            f"- Use the question EXACTLY as: \"{base_question}\".\n"
            "- Set options EXACTLY to: ['①','②','③','④','⑤'].\n"
            "- Set correct_answer to a STRING digit '1'..'5' that matches the label number of the irrelevant sentence.\n\n"
            "## OUTPUT FORMAT (STRICT JSON ONLY)\n"
            "{\n"
            f"  \"question\": \"{base_question}\",\n"
            "  \"passage\": \"[full passage with the five labeled sentences ①~⑤ embedded in place]\",\n"
            "  \"options\": [\"①\",\"②\",\"③\",\"④\",\"⑤\"],\n"
            "  \"correct_answer\": \"1\"|\"2\"|\"3\"|\"4\"|\"5\",\n"
            "  \"explanation\": \"[Korean explanation why that sentence is unrelated]\",\n"
            "  \"rationale\": \"[optional short English or Korean notes on the construction, or empty string]\"\n"
            "}\n\n"
            "- Do NOT output anything outside this JSON object (no markdown, no comments).\n\n"
            "PASSAGE:\n" + (passage or "")
        )

    def quote_postprocess(self, passage: str, llm_json: dict) -> dict:
        """
        LLM이 반환한 JSON을 RC35 인용용 item 구조로 정리.
        - question/option 형식을 RC35 스펙에 맞게 강제 정규화.
        - correct_answer가 ①~⑤로 오면 '1'..'5'로 변환.
        - passage에는 ①~⑤가 모두 들어 있는지 확인.
        """
        base_question = "다음 글에서 전체 흐름과 관계 <u>없는</u> 문장은?"

        # ----- 필드 추출 및 정리 -----
        raw_passage = (llm_json.get("passage") or "").strip()
        if not raw_passage:
            # 만약 모델이 passage를 비워보내면, 원본을 그대로 사용 (이 경우 라벨이 없으면 validate에서 걸림)
            raw_passage = passage or ""

        # ①~⑤가 모두 들어 있는지 간단히 체크
        if not all(lbl in raw_passage for lbl in LABELS):
            raise ValueError("RC35(quote): passage must contain all labels ①~⑤ exactly once each block.")

        ca = str(llm_json.get("correct_answer") or "").strip()
        # ①~⑤로 들어오면 숫자문자 '1'..'5'로 변환
        if ca in LABELS:
            ca = str(LABELS.index(ca) + 1)

        explanation = (llm_json.get("explanation") or "").strip()
        rationale = (llm_json.get("rationale") or "").strip() or None

        item = {
            "question": base_question,
            "passage": raw_passage,
            "options": LABELS.copy(),
            "correct_answer": ca,
            "explanation": explanation,
            "rationale": rationale,
        }
        return item

    def quote_validate(self, item: dict) -> None:
        """
        인용 모드 결과도 RC35Model 스키마에 그대로 태우되,
        - question, options, correct_answer, passage의 기본 형식이 모두 맞는지 검증.
        """
        RC35Model.model_validate(item)
