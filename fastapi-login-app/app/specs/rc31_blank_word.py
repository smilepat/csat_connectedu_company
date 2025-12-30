# app/specs/rc31_blank_word.py
from __future__ import annotations
import re
from typing import List
from pydantic import BaseModel, Field, field_validator
from app.specs.base import GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like

# ====== (RC30에서 사용했던 '최초 1회 치환' 안전함수) ======
def _replace_once(text: str, old: str, new: str) -> str:
    """
    본문에서 old를 new로 '최초 1회'만 치환.
    1차: 단어 경계, 대소문자 무시
    2차: 공백 느슨 매칭
    """
    if not old or not new:
        return text
    pat = re.compile(rf"\b({re.escape(old)})\b", re.I)
    out = pat.sub(lambda m: new, text, count=1)
    if out != text:
        return out
    loose = re.compile(rf"({re.escape(old).replace(r'\ ', r'\s+')})", re.I)
    return loose.sub(lambda m: new, text, count=1)

class RC31Model(BaseModel):
    question: str
    passage: str
    options: list[str] = Field(min_length=5, max_length=5)
    correct_answer: str
    explanation: str

    @field_validator("question", "passage", "explanation", "correct_answer", mode="before")
    @classmethod
    def _strip(cls, v): return (v or "").strip()

    @field_validator("options", mode="before")
    @classmethod
    def _opts(cls, v): return [str(o).strip() for o in (v or [])]

class RC31Spec:
    id = "RC31"

    # ---------- (생성 경로: 기존 유지) ----------
    def system_prompt(self) -> str:
        # 옵션은 가능하면 단어/짧은 구로. 빈칸은 반드시 한 번만 '_____' 로 표시하도록 강제.
        return (
            "CSAT English RC31 (단어 수준 빈칸 추론). "
            "Return ONLY JSON matching the schema. Use ONLY the provided passage. "
            "Insert exactly ONE visible blank marker as '_____'. Do not invent multiple blanks. "
            "Options should be mostly single words or short noun phrases (≤2–3 words)."
        )

    def build_prompt(self, ctx: GenContext) -> str:
        item_type = (ctx.get("item_id") or self.id)
        return PromptManager.generate(item_type=item_type,
                                      difficulty=(ctx.get("difficulty") or "medium"),
                                      topic_code=(ctx.get("topic") or "random"),
                                      passage=(ctx.get("passage") or ""))

    # ---------- (생성 경로 보조 유틸: 기존 유지) ----------
    _STOPWORDS = {"a","an","the","to","of","in","on","for","and","or","with","by","from"}

    def _answer_to_index(self, answer: str, options: List[str]) -> str:
        """정답을 '1'~'5' 문자열로 강제."""
        a = str(answer or "").strip()
        if a in {"1","2","3","4","5"}: return a
        if a.isdigit() and 1 <= int(a) <= 5: return str(int(a))
        try:
            return str(options.index(a) + 1)
        except ValueError:
            return a  # validate에서 잡히게 둠

    def _condense_option(self, opt: str, max_words: int = 3) -> str:
        s = (opt or "").strip()
        parts = re.split(r"\s*[:\-–—;]\s*", s)
        if len(parts) >= 2:
            s = parts[-1].strip()
        s = re.sub(r"[\"'“”‘’\(\)\[\]\{\}…\.]+", "", s)
        tokens = [t for t in re.split(r"\s+", s) if t]
        pruned = [t for t in tokens if t.lower() not in self._STOPWORDS] or tokens
        cut = pruned[:max_words]
        head = " ".join(cut).strip(" ,.-–—;:")
        return head or (tokens[0] if tokens else "")

    def _has_visible_blank(self, s: str) -> bool:
        if not isinstance(s, str): return False
        return ("_____" in s) or ("<blank>" in s)

    def _inject_blank_into_question(self, question: str) -> str:
        q = (question or "").strip()
        if not q:
            return "다음 글의 빈칸(_____)에 들어갈 말로 가장 적절한 것은?"
        if "빈칸" in q:
            return q.replace("빈칸", "빈칸(_____)")
        return (q.rstrip() + " (_____)").strip()

    # ---------- (생성 경로 normalize/validate: 기존 유지) ----------
    def normalize(self, data: dict) -> dict:
        d = coerce_mcq_like(data)
        if d.get("options") and d.get("correct_answer") is not None:
            d["correct_answer"] = self._answer_to_index(d["correct_answer"], d["options"])

        if isinstance(d.get("options"), list) and len(d["options"]) == 5:
            condensed = [self._condense_option(o, max_words=2) for o in d["options"]]
            if any(len(o.split()) > 2 for o in d["options"]) or len(set(condensed)) == 5:
                d["options"] = condensed

        pas = d.get("passage") or ""
        qst = d.get("question") or ""
        if not self._has_visible_blank(pas) and not self._has_visible_blank(qst):
            d["question"] = self._inject_blank_into_question(qst)

        q = d.get("question") or ""
        if isinstance(q, str):
            q = q.replace("<blank>", "_____")
            q = re.sub(r"_{6,}", "_____", q)
            if q.count("_____") > 1:
                first = q.replace("_____", "<KEEP_ONCE>", 1).replace("_____", "").replace("<KEEP_ONCE>", "_____")
            else:
                first = q
            d["question"] = first
        return d

    def extra_checks(self, data: dict):
        pas = (data.get("passage") or "").lower()
        qst = (data.get("question") or "").lower()
        if ("_____" not in pas and "<blank>" not in pas) and ("_____" not in qst and "<blank>" not in qst):
            raise ValueError("RC31 requires a visible blank marker (_____ or <blank>) in passage or question.")
        shortish = sum(len(o.split()) <= 2 for o in data.get("options", []))
        if shortish < 3:
            raise ValueError("RC31 options should be mostly single words or short phrases.")

    def validate(self, data: dict):
        m = RC31Model.model_validate(data)
        self.extra_checks(data)
        return m

    def json_schema(self) -> dict:
        return RC31Model.model_json_schema()

    def repair_budget(self) -> dict:
        return {"fixer": 2, "regen": 2, "timeout_s": 18}

    # ========== (여기부터 인용 전용: generate 경로에는 영향 없음) ==========
    def has_quote_support(self) -> bool:
        """
        인용(quote) 모드를 지원함을 알린다.
        generate 경로에는 영향 없음.
        """
        return True

    def quote_build_prompt(self, passage: str) -> str:
        """
        인용 모드 프롬프트:
        - passage는 수정 금지(LLM 단계). 표식 삽입 금지.
        - passage 안에서 '빈칸으로 뺄 대상'을 정확히 1개 고르고(blank_token),
          그 빈칸을 문맥상 완성할 5개 보기(options)와 정답 인덱스를 제시.
        - 보기들은 단어/짧은 구(2~3어 이내) 위주.
        """
        return (
            "You are generating a CSAT-English RC31 (blank inference, word/phrase) item from the given PASSAGE.\n"
            "RULES:\n"
            "- DO NOT modify the passage text. DO NOT insert any blank markers yourself.\n"
            "- Choose exactly ONE contiguous substring from the PASSAGE to blank out (call it blank_token).\n"
            "- blank_token MUST be a real substring (case-insensitive ok) present in the PASSAGE.\n"
            "- Produce 5 options (single words or short noun phrases ≤ 2–3 words). EXACTLY ONE option must correctly fill the blank.\n"
            "- Provide correct_answer as \"1\"..\"5\" (string). The correct option MUST equal blank_token (case-insensitive).\n"
            "- The explanation MUST be in Korean, explaining the logic of why the correct option fits best.\n"
            'Return JSON only with keys: {"question","options","blank_token","correct_answer","explanation"}.\n'
            '- "question" should be: "다음 글의 빈칸에 들어갈 말로 가장 적절한 것은?"\n'
            "- Do not include any HTML or underline tags in any field.\n"
            "PASSAGE:\n" + passage
        )

    def quote_postprocess(self, passage: str, llm_json: dict) -> dict:
        """
        인용 모드 사후처리:
        - passage 원문에서 blank_token을 '_____'로 '한 번만' 교체
        - options/정답 정규화(정답은 '1'~'5')
        - 보기들이 단어/짧은 구인지 가볍게 정리(과도한 문장형은 축약)
        - question은 고정형 문구 사용
        """
        # 1) 추출
        options = list((llm_json.get("options") or [])[:5])
        blank_tok = (llm_json.get("blank_token") or "").strip()
        ca = str(llm_json.get("correct_answer") or "").strip()
        exp = (llm_json.get("explanation") or "").strip()

        # 2) 기본 검증
        if len(options) != 5:
            raise ValueError("RC31(quote): options must have exactly 5 items")
        if ca not in {"1","2","3","4","5"}:
            # 혹시 숫자형으로 온 경우 관대 수용
            if ca.isdigit() and 1 <= int(ca) <= 5:
                ca = str(int(ca))
            else:
                raise ValueError("RC31(quote): correct_answer must be '1'..'5'")
        ci = int(ca) - 1
        if not blank_tok:
            raise ValueError("RC31(quote): blank_token is required")
        # 정답 옵션과 blank_token 일치(대소문 무시) 보장
        if options[ci].strip().lower() != blank_tok.lower():
            raise ValueError("RC31(quote): correct option must equal blank_token (case-insensitive)")

        # 3) passage에 '한 번만' 빈칸 삽입
        marked_passage = _replace_once(passage, blank_tok, "_____")

        # 4) 보기 축약(단어/짧은 구 위주)
        def _short(o: str) -> str:
            return self._condense_option(o, max_words=2)
        options = [_short(o) for o in options]

        # 5) 결과 구성
        item = {
            "passage": marked_passage,
            "question": "다음 글의 빈칸에 들어갈 말로 가장 적절한 것은?",
            "options": options,
            "correct_answer": str(ci + 1),
            "explanation": exp,
        }
        return item

    def quote_validate(self, item: dict) -> None:
        """
        인용 모드 얇은 검증:
        - passage 안의 '_____'가 정확히 1회 존재
        - options 5개, 정답 1~5
        - 정답 옵션이 실제로 존재
        - HTML 밑줄 금지(안전망)
        """
        pas = item.get("passage") or ""
        qst = item.get("question") or ""
        opts = item.get("options") or []
        ca = str(item.get("correct_answer") or "").strip()

        if pas.count("_____") != 1:
            raise AssertionError("RC31(quote): passage must contain exactly one blank (_____).")
        if not (isinstance(opts, list) and len(opts) == 5):
            raise AssertionError("RC31(quote): exactly five options are required.")
        if ca not in {"1","2","3","4","5"}:
            raise AssertionError("RC31(quote): correct_answer must be '1'..'5'.")

        # 보기 짧은지 가벼운 확인(≥3개는 2어 이하)
        shortish = sum(len(str(o).split()) <= 2 for o in opts)
        if shortish < 3:
            raise AssertionError("RC31(quote): options should be mostly single words or short phrases (≥3/5).")

        # HTML 밑줄 금지
        if re.search(r"</?(u|ins)\b", pas, flags=re.I) or re.search(r"</?(u|ins)\b", qst, flags=re.I):
            raise AssertionError("RC31(quote): HTML underline tags are not allowed.")