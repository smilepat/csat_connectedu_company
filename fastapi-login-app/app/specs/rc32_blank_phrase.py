from __future__ import annotations
import re
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from app.specs.base import GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like

class RC32Model(BaseModel):
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


class RC32Spec:
    id = "RC32"

    def system_prompt(self) -> str:
        return (
            "CSAT English RC32 (구/절 수준 빈칸). "
            "Return ONLY JSON matching the schema. Use ONLY the provided passage. "
            "Options should be phrase/clause-level (≈3–6 words), not single words."
        )

    def build_prompt(self, ctx: GenContext) -> str:
        item_type = (ctx.get("item_id") or self.id)
        return PromptManager.generate(
            item_type=item_type,
            difficulty=(ctx.get("difficulty") or "medium"),
            topic_code=(ctx.get("topic") or "random"),
            passage=(ctx.get("passage") or ""),
        )

    # ---------- helpers (공용) ----------
    def _answer_to_index(self, answer: str, options: List[str]) -> str:
        a = str(answer or "").strip()
        if a in {"1", "2", "3", "4", "5"}:
            return a
        if a.isdigit() and 1 <= int(a) <= 5:
            return str(int(a))
        try:
            return str(options.index(a) + 1)
        except ValueError:
            return a

    def _tidy_phrase(self, s: str) -> str:
        parts = re.split(r"\s*[:\-–—;]\s*", s.strip())
        if len(parts) >= 2:
            s = parts[-1].strip()
        s = re.sub(r"[\"'“”‘’\(\)\[\]\{\}…\.]+", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def normalize(self, data: dict) -> dict:
        d = coerce_mcq_like(data)
        if d.get("options") and d.get("correct_answer") is not None:
            d["correct_answer"] = self._answer_to_index(d["correct_answer"], d["options"])
        if isinstance(d.get("options"), list) and len(d["options"]) == 5:
            d["options"] = [self._tidy_phrase(o) for o in d["options"]]
        return d

    def validate(self, data: dict):
        m = RC32Model.model_validate(data)
        pas = (data.get("passage") or "").lower()
        if "_____" not in pas and "<blank>" not in pas:
            raise ValueError("RC32 requires a blank marker (_____ or <blank>).")
        opts = data.get("options", [])
        three_plus = sum(len(o.split()) >= 3 for o in opts)
        two_plus = sum(len(o.split()) >= 2 for o in opts)
        if not (three_plus >= 3 or (three_plus >= 2 and two_plus >= 4)):
            raise ValueError("RC32 options should include ≥3 phrase/clause-level candidates.")
        return m

    def json_schema(self) -> dict:
        return RC32Model.model_json_schema()

    def repair_budget(self) -> dict:
        return {"fixer": 2, "regen": 2, "timeout_s": 18}

    # =========================
    # 인용(quote) 전용 훅 — RC32 전용 (재작성)
    # =========================
    def has_quote_support(self) -> bool:
        return True

    def quote_build_prompt(self, passage: str) -> str:
        """
        RC32 인용(quote) 모드 프롬프트 생성

        요구사항:
        1) 전달 받은 지문을 그대로 이용한다.
        2) 첫 문장과 마지막 문장은 절대 건드리지 않는다.
        3) 가운데 문장들 중에서, 아래 세 패턴 중 하나에 해당하는 '이미 존재하는' 구/절을 그대로 골라
           그 부분만 빈칸(_____)으로 교체한다.

           [패턴 A] 3인칭 단수 동사 + 목적어/전치사구  → 완전한 절(평서문)
             - 예: "frees the plot of its familiarity"
                    "adds to an exotic musical experience"
                    "orients audiences to the film’s theme"

           [패턴 B] 동사(V) + 목적어 (실제는 복수 주어 생략된 평서문) → 완전한 절(평서문)
             - 예: "provide rich source materials for artists"
                    "offer the greatest exposure to other people"
                    "cause cultural conflicts among users of slang"

           [패턴 C] 명사구(NP) → 불완전절(구 수준)
             - 예: "coordination with traditional display techniques"
                    "prompt and full coverage of the latest issues"
                    "verbal and visual idioms or modes of address"

        4) 빈칸 처리된 부분(원래 지문에서 삭제한 구/절)을 정답으로 사용한다.
        5) 선택지는 정답과 동일한 문법적 특징(A/B/C)을 공유하면서, 의미상으로만 틀리게 만든 오답으로 구성한다.
        """
        return (
            "You will create a CSAT Reading Item 32 (Blank Inference - Phrase/Clause)\n"
            "in QUOTE MODE from the given PASSAGE.\n\n"
            "## ABSOLUTE RULES ABOUT THE PASSAGE\n"
            "- You MUST use the given PASSAGE exactly as it is.\n"
            "- DO NOT rewrite, paraphrase, reorder, add, or delete any sentences.\n"
            "- You may only replace ONE existing phrase/clause with a blank (_____).\n"
            "- The FIRST sentence and the LAST sentence must NEVER contain the blank.\n\n"
            "## HOW TO CHOOSE THE BLANK (A/B/C PATTERNS + DISCOURSE ROLE)\n"
            "1) Split the PASSAGE into sentences.\n"
            "2) If the passage has 5 or more sentences:\n"
            "   - You MUST choose the blank ONLY from the 3rd, 4th, or 5th sentence\n"
            "     (counting from the beginning: 1st, 2nd, 3rd, ...).\n"
            "   - Do NOT put the blank in the 1st or the last sentence.\n"
            "3) If the passage has fewer than 5 sentences:\n"
            "   - You MUST NOT put the blank in the 1st or the last sentence.\n"
            "4) From the allowed middle sentence(s), choose ONE phrase or clause that:\n"
            "   (a) ALREADY EXISTS VERBATIM in the passage, and\n"
            "   (b) plays a CLEAR DISCOURSE ROLE such as:\n"
            "       - CAUSE or REASON (e.g., \"because ~\", \"since ~\", \"as a result of ~\",\n"
            "         \"due to ~\", a clause that explains WHY something happens), or\n"
            "       - RESULT or CONSEQUENCE (e.g., \"so that ~\", \"as a result, ~\",\n"
            "         \"therefore ~\", \"thus ~\", \"this leads to ~\"), or\n"
            "       - CONTRAST / TURNING POINT / TRANSITION (e.g., \"however, ~\",\n"
            "         \"but ~\", \"on the other hand, ~\", \"instead, ~\", \"nevertheless, ~\").\n"
            "   In other words, the blanked phrase/clause should be located at a point\n"
            "   where the passage changes direction (contrast/turning) or connects cause\n"
            "   and effect.\n"
            "5) The chosen span must ALSO match exactly ONE of the surface PATTERNS below:\n"
            "\n"
            "   [PATTERN A: 3rd person singular finite clause]\n"
            "   - Form: a 3rd-person singular verb (V-s) + object and/or prepositional phrase.\n"
            "   - Example: \"frees the plot of its familiarity\" (result),\n"
            "              \"orients audiences to the film’s theme\" (effect).\n"
            "\n"
            "   [PATTERN B: bare verb phrase with object]\n"
            "   - Form: a lexical verb (bare form) + object and/or prepositional phrase.\n"
            "   - Often works as a predicate for a plural subject understood from context,\n"
            "     and expresses what happens (effect) or what some factors do.\n"
            "   - Example: \"provide rich source materials for artists\" (result of something),\n"
            "              \"cause cultural conflicts among users of slang\" (cause/effect).\n"
            "\n"
            "   [PATTERN C: noun phrase]\n"
            "   - Form: a noun phrase (NP) that names a cause, consequence, condition, or\n"
            "     transition idea (NOT a random concrete object or detail).\n"
            "   - Examples: \"coordination with traditional display techniques\" (condition),\n"
            "               \"prompt and full coverage of the latest issues\" (result/advantage),\n"
            "               \"verbal and visual idioms or modes of address\" (key concept).\n"
            "\n"
            "6) Replace ONLY that existing phrase/clause with exactly five underscores (_____).\n"
            "7) The removed phrase/clause (blank_text) will be the CORRECT option.\n"
            "## OPTIONS (5 CHOICES)\n"
            "- Provide exactly FIVE options.\n"
            "- ALL options (including the correct one and four distractors) MUST share the SAME\n"
            "  grammatical pattern type as blank_text:\n"
            "    · If blank_text is PATTERN A → every option must be a 3rd person singular\n"
            "      finite clause (V-s + object/PP).\n"
            "    · If blank_text is PATTERN B → every option must be a bare verb phrase\n"
            "      with an object (no explicit subject).\n"
            "    · If blank_text is PATTERN C → every option must be a noun phrase.\n"
            "- The CORRECT option MUST be (almost) exactly the same as blank_text\n"
            "  copied from the original passage (do NOT paraphrase).\n"
            "- The four WRONG options must be:\n"
            "    · grammatically compatible with the local sentence frame, and\n"
            "    · logically wrong, less appropriate, or contextually inconsistent.\n"
            "- Do NOT use proper names, dates, or raw numbers as options.\n\n"
            "## OUTPUT FORMAT (STRICT JSON ONLY)\n"
            "Return ONE JSON object with the following fields:\n"
            "{\n"
            "  \"question\": \"다음 글의 빈칸에 들어갈 말로 가장 적절한 것은?\",\n"
            "  \"passage\": \"[original passage with EXACTLY ONE blank (_____)]\",\n"
            "  \"options\": [\"opt1\",\"opt2\",\"opt3\",\"opt4\",\"opt5\"],\n"
            "  \"correct_answer\": \"1\"|\"2\"|\"3\"|\"4\"|\"5\",\n"
            "  \"blank_text\": \"[the exact phrase/clause removed from the passage]\",\n"
            "  \"pattern_type\": \"A\"|\"B\"|\"C\",\n"
            "  \"explanation\": \"[Korean explanation of why the correct option is best]\"\n"
            "}\n\n"
            "- \"passage\" MUST be identical to the given PASSAGE, except that one phrase/clause\n"
            "   has been replaced by '_____'.\n"
            "- There must be EXACTLY ONE '_____'.\n"
            "- \"pattern_type\" must reflect which pattern (A/B/C) you used for blank_text.\n"
            "- Do NOT output any text outside this JSON object. No markdown.\n\n"
            "PASSAGE:\n" + (passage or "")
        )

    # --- 간단한 공백 정규화 유틸 ---
    def _norm_spaces(self, s: str) -> str:
        s = re.sub(r"\s+", " ", s or "").strip()
        s = re.sub(r"\s+([.,;:!?])", r"\1", s)
        return s

    # --- 유연 치환 헬퍼: 공백/대소문자 약간 달라도 찾기 ---
    def _replace_blank_fuzzy(self, text: str, span: str) -> str | None:
        """
        text 안에서 span(빈칸으로 만들 구/절)을 최대한 유연하게 찾아
        첫 한 곳만 '_____ '로 치환한 문자열을 돌려준다.
        - 정확 매칭 실패 시: 공백 무시, 대소문자 무시 정규식으로 재시도.
        - 실패하면 None.
        """
        if not text or not span:
            return None

        t = text
        s = span.strip()

        # 1차: 정확 매칭
        idx = t.find(s)
        if idx != -1:
            return t[:idx] + "_____" + t[idx + len(s):]

        # 2차: 공백 유연 + 대소문자 무시 정규식
        # "ideas that are unlikely to be successful" ->
        #   r"ideas\s+that\s+are\s+unlikely\s+to\s+be\s+successful"
        pattern = re.escape(s)
        pattern = pattern.replace(r"\ ", r"\s+")
        m = re.search(pattern, t, flags=re.I | re.M)
        if m:
            return t[:m.start()] + "_____" + t[m.end():]

        return None

    def quote_postprocess(self, passage: str, llm_json: dict) -> dict:
        orig_passage = passage or ""

        # ----- 필수 필드 추출 -----
        opts = list((llm_json.get("options") or [])[:5])
        if len(opts) != 5:
            raise ValueError("RC32(quote): options must have exactly 5 items")

        ca = str(llm_json.get("correct_answer") or "").strip()
        if ca not in {"1", "2", "3", "4", "5"}:
            if ca in opts:
                ca = str(opts.index(ca) + 1)
            else:
                ca = "1"
        correct_idx = int(ca) - 1
        correct_opt = (opts[correct_idx] or "").strip()

        blank_text = (llm_json.get("blank_text") or "").strip()
        if not blank_text:
            blank_text = correct_opt

        pattern_type = (llm_json.get("pattern_type") or "").strip()

        # ----- 1단계: '원본 지문'에서 유연 매칭으로 blank 만들기 -----
        p_with_blank = (
            self._replace_blank_fuzzy(orig_passage, blank_text)
            or self._replace_blank_fuzzy(orig_passage, correct_opt)
        )

        # ----- 2단계: 실패하면 LLM이 준 passage를 폴백으로 사용 -----
        if not p_with_blank:
            llm_passage = (llm_json.get("passage") or "").strip()
            if "_____" in llm_passage:
                p_with_blank = llm_passage
            else:
                raise ValueError(
                    "RC32(quote): cannot locate the blank span in the original passage "
                    "and no usable blank found in model passage."
                )

        p = p_with_blank

        # blank 개수 확인
        if p.count("_____") != 1:
            raise ValueError(
                f"RC32(quote): passage must contain exactly ONE blank, found {p.count('_____')}."
            )

        explanation = (llm_json.get("explanation") or "").strip()

        item = {
            "question": "다음 글의 빈칸에 들어갈 말로 가장 적절한 것은?",
            "passage": p,
            "options": [o.strip() for o in opts],
            "correct_answer": ca,
            "explanation": explanation,
            "_blank_text": blank_text,
            "_pattern_type": pattern_type,
        }
        return item



    def quote_validate(self, item: dict) -> None:
        """
        인용 모드 검증(간단 버전):
        - passage에 정확히 1개의 빈칸(_____)이 있을 것
        - 보기 5개, 정답 '1'..'5'
        - 첫/마지막 문장 여부는 더 이상 hard constraint로 막지 않는다.
        """
        p = (item.get("passage") or "")
        blank_count = p.count("_____")
        if blank_count != 1:
            raise AssertionError(
                f"RC32(quote): passage must contain exactly one blank marker, found {blank_count}"
            )

        opts = item.get("options") or []
        if len(opts) != 5:
            raise AssertionError("RC32(quote): exactly 5 options are required.")

        ca = str(item.get("correct_answer") or "").strip()
        if ca not in {"1", "2", "3", "4", "5"}:
            raise AssertionError("RC32(quote): correct_answer must be '1'..'5'.")