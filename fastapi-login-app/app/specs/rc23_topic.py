# app/specs/rc23_topic.py
from __future__ import annotations
from pydantic import BaseModel, Field, validator
from app.specs.base import ItemSpec, GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like
import re


class RC23Model(BaseModel):
    """
    RC23: 주제(topic) 파악 — 5지선다 MCQ 공통 스키마
    """
    question: str
    passage: str
    options: list[str] = Field(min_length=5, max_length=5)
    correct_answer: str
    explanation: str

    @validator("question", "passage", "explanation", pre=True)
    def _strip(cls, v):
        return (v or "").strip()


class RC23Spec(ItemSpec):
    """
    RC23 전용 스펙: PromptManager.generate 기반 '생성(generate)' 경로 + 인용(quote) 경로 분리.
    - generate: prompt_data.py 템플릿을 PromptManager.generate로 호출, passage는 스펙에서 직접 주입
    - quote: 주어진 PASSAGE를 수정하지 않고, 보기/정답/해설만 LLM이 JSON으로 반환 → 사후처리로 주입
    """
    id = "RC23"

    # ===== (기존) generate 경로용 설정 =====
    def system_prompt(self) -> str:
        return (
            "CSAT English RC23 (Topic). "
            "Return ONLY JSON matching the schema. "
            "Use ONLY the provided passage. Do NOT invent or substitute a new passage."
        )

    def build_prompt(self, ctx: GenContext) -> str:
        # PromptManager.generate: BASE + RC23 템플릿 + 난이도/주제 인스트럭션 + passage 주입 + OUTPUT RULES 구성
        return PromptManager.generate(
            item_type=self.id,
            difficulty=(ctx.get("difficulty") or "medium"),
            topic_code=(ctx.get("topic") or "random"),
            passage=(ctx.get("passage") or ""),
        )

    # ---------- 품질 보정/검증 ----------
    def normalize(self, data: dict) -> dict:
        """
        공통 정규화:
        - 다양한 키 변형을 표준 MCQ 형태로 정규화(coerce_mcq_like)
        - 옵션 5개로 절단 및 번호/불릿 제거
        - correct_answer 표준화(①~⑤, 1~5, 또는 텍스트→인덱스)
        - 불필요 부가 필드 제거(metadata 등)
        """
        x = coerce_mcq_like(data)

        # passage 보강: stimulus가 있고 passage 비면 채움
        if not (x.get("passage") or "").strip():
            stim = (data.get("stimulus") or "").strip()
            if stim:
                x["passage"] = stim

        # question 보강(기본 발문)
        if not (x.get("question") or "").strip():
            qstem = (data.get("question_stem") or "").strip()
            x["question"] = qstem or "다음 글의 주제로 가장 적절한 것은?"

        # 옵션 5개로 절단 + 번호/불릿 제거
        opts = list(x.get("options") or [])[:5]

        def _strip_marker(s: str) -> str:
            s = str(s or "").strip()
            s = re.sub(r"^\s*(?:[①②③④⑤]|[1-5][\.\)\-:]?)\s*", "", s)
            return re.sub(r"\s{2,}", " ", s).strip()

        opts = [_strip_marker(o) for o in opts]
        x["options"] = opts

        # correct_answer 표준화
        raw = str(x.get("correct_answer", "")).strip()
        MAP = {"①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5",
               "1": "1", "2": "2", "3": "3", "4": "4", "5": "5"}
        ca = MAP.get(raw, raw)
        if ca not in {"1", "2", "3", "4", "5"}:
            target = raw.lower()
            idx = next((i + 1 for i, o in enumerate(opts)
                        if str(o or "").strip().lower() == target), None)
            if idx is not None:
                ca = str(idx)
        x["correct_answer"] = ca

        # 불필요 부가 필드 제거
        for k in ["vocabulary_difficulty", "low_frequency_words", "rationale",
                  "stimulus", "question_stem", "metadata"]:
            x.pop(k, None)

        return x

    def validate(self, data: dict):
        # Pydantic 검증 + 추가 형식 점검
        RC23Model(**data)
        if data.get("correct_answer") not in {"1", "2", "3", "4", "5"}:
            raise ValueError("correct_answer must be a string in '1'..'5'")
        # 옵션 번호/불릿 금지
        for o in data.get("options", []):
            if re.match(r"^\s*(?:[①②③④⑤]|[1-5][\.\)\-:]?)\s*", o or ""):
                raise ValueError("options must NOT start with numbering/bullets for RC23")

    def json_schema(self) -> dict:
        return RC23Model.model_json_schema()

    def repair_budget(self) -> dict:
        # 기본 예산: 1회 fixer, 1회 재생성, 15초 타임아웃
        return {"fixer": 1, "regen": 1, "timeout_s": 15}

    # ===== (신규) quote 전용 훅들 =====
    def has_quote_support(self) -> bool:
        """
        인용(quote) 모드를 지원함을 알린다.
        generate 경로에는 영향 없음.
        """
        return True

    def quote_build_prompt(self, passage: str) -> str:
        """
        인용 모드 프롬프트:
        - PASSAGE는 절대 수정/재작성 금지.
        - LLM은 '주제 파악' 유형 정책을 따르며 보기 5개(영어, 번호/불릿 없음),
          정답("1"~"5"), 해설(한국어)만 JSON으로 반환.
        - RC23 지침(발문 한국어 고정, 옵션 번호/불릿 금지, 오답 유형 정책, 정답 문자열)을 반영.
        """
        return (
            "You are generating a CSAT-English RC23 (Topic Identification) item from the given PASSAGE.\n"
            "STRICT RULES:\n"
            "- DO NOT modify or rewrite the passage. Use it only to infer the overall topic.\n"
            "- Return JSON ONLY with keys: {\"question\",\"options\",\"correct_answer\",\"explanation\"}.\n"
            "- Do NOT include the passage in your JSON; it will be supplied externally.\n"
            "- question (Korean): exactly \"다음 글의 주제로 가장 적절한 것은?\".\n"
            "- options (5 items, ENGLISH): concise, topic/title-like statements WITHOUT any leading numbering or bullets "
            "(no ①~⑤, 1., -, (), etc.).\n"
            "- Distractors policy: include one too broad, one too narrow, one that is just a partial/example, "
            "and one that introduces a related-but-absent concept; ensure exactly one best overall topic.\n"
            "- correct_answer: a STRING among \"1\",\"2\",\"3\",\"4\",\"5\" (do NOT put option text).\n"
            "- explanation (Korean): briefly justify the correct topic with passage-based reasoning and provide 1–2-line eliminations for the distractors.\n"
            "OUTPUT: JSON only, no code fences, no extra text.\n"
            "PASSAGE (read only; DO NOT output or alter it):\n" + passage
        )

    def quote_postprocess(self, passage: str, llm_json: dict) -> dict:
        """
        인용 모드 사후처리:
        - LLM이 반환한 question/options/correct_answer/explanation을 가져오고,
          passage는 인자로 받은 원문을 주입.
        - normalize()를 통해 번호/불릿 제거 및 정답 보정.
        """
        item = {
            "passage": passage or "",
            "question": "다음 글의 주제로 가장 적절한 것은?",
            "options": list(llm_json.get("options") or []),
            "correct_answer": str(llm_json.get("correct_answer") or "").strip(),
            "explanation": (llm_json.get("explanation") or "").strip(),
        }
        item = self.normalize(item)
        return item

    def quote_validate(self, item: dict) -> None:
        """
        인용 모드 얇은 검증:
        - 옵션 정확히 5개 & 번호/불릿 없는지 확인
        - correct_answer ∈ {"1","2","3","4","5"}
        - passage 비어 있지 않음(외부 주입)
        """
        RC23Model(**item)
        if item.get("correct_answer") not in {"1", "2", "3", "4", "5"}:
            raise AssertionError("RC23(quote): correct_answer must be '1'..'5'")
        if not (item.get("passage") or "").strip():
            raise AssertionError("RC23(quote): passage must not be empty")
        if len(item.get("options") or []) != 5:
            raise AssertionError("RC23(quote): exactly 5 options required")
        for o in item.get("options", []):
            if re.match(r"^\s*(?:[①②③④⑤]|[1-5][\.\)\-:]?)\s*", o or ""):
                raise AssertionError("RC23(quote): options must NOT start with numbering/bullets")
