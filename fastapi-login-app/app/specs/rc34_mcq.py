# app/specs/rc34_mcq.py
from __future__ import annotations
import re

from .base import ItemSpec, GenContext
from app.schemas.items_rc34 import RC34Model
from .utils import standardize_answer, tidy_options

class RC34Spec(ItemSpec):
    id = "RC34"

    # (선택) 시스템 프롬프트가 있다면 추가해도 됩니다.
    # def system_prompt(self) -> str:
    #     return (
    #         "You are an expert CSAT item writer. "
    #         "Return ONLY valid JSON that matches the schema for RC34 items. "
    #         "Use ONLY the provided passage; do NOT invent or rewrite it."
    #     )

    def build_prompt(self, ctx: GenContext) -> str:
        from app.prompts.prompt_manager import PromptManager

        difficulty = (ctx.get("difficulty") or "medium").strip()
        topic      = (ctx.get("topic") or "random").strip()
        passage    = (ctx.get("passage") or "").strip()
        item_id    = (ctx.get("item_id") or "RC34").strip()
        if passage:
            return PromptManager.generate(
                item_id,
                difficulty,
                topic,
                passage=passage,
            )
        # 2) passage가 없으면: 템플릿로 지문+문항 동시 생성
        #    (ITEM_PROMPTS["RC34"]가 free-mode를 지원해야 함)
        return PromptManager.generate(
            item_id,
            difficulty,
            topic,
            # passage 미전달 → PromptManager가 주입하지 않음(자유 생성)
        )

    def normalize(self, data: dict) -> dict:
        d = dict(data or {})
        d["passage"]   = (d.get("passage") or "").strip()
        d["question"]  = (d.get("question") or "").strip()
        d["options"]   = tidy_options(d.get("options") or [])
        ans            = standardize_answer(d.get("correct_answer") or d.get("answer") or "")
        d["correct_answer"] = ans
        # 입력은 rationale/explanation 둘 다 허용 → 출력은 explanation으로 통일
        exp = (d.get("explanation") or d.get("rationale") or "").strip()
        d["explanation"] = exp
        d.pop("rationale", None)
        return d

    def validate(self, data: dict):
        return RC34Model(**data)

    def json_schema(self) -> dict:
        return RC34Model.model_json_schema()

    def repair_budget(self) -> dict:
        return {"fixer": 1, "regen": 1, "timeout_s": 12}

    def repair(self, data: dict, passage: str) -> dict:
        d = dict(data or {})
        out_p = (d.get("passage") or "").strip()
        # 모델이 passage를 비워두면 외부 passage로 채워줌 (빈칸 "_____” 유무는 상위 self-check에서 재생성 유도)
        if passage and not out_p:
            d["passage"] = passage
        return d

    # =========================
    # 인용(quote) 전용 훅 — RC34
    # =========================
    def has_quote_support(self) -> bool:
        """
        인용 모드 지원 여부. 상위 파이프라인에서 이 메서드가 있으면
        quote_build_prompt / quote_postprocess / quote_validate를 사용.
        """
        return True

    def quote_build_prompt(self, passage: str) -> str:
        """
        RC34 인용(quote) 모드 프롬프트 생성.

        요구사항 요약:
        1) 전달 받은 지문(PASSAGE)을 그대로 사용한다.
        2) 첫 문장과 마지막 문장은 절대 건드리지 않는다.
        3) 가운데 문장(중간부)에서, 길이 7~15 단어 정도의 완결 절/명사구를 하나 골라
           그 부분만 빈칸(_____)으로 교체한다.
        4) 그 절/구는 글의 흐름에서 '전환 / 인과 / 요약 pivot' 역할을 해야 한다.
        5) 제거한 원래 절/구는 정답 선택지로 사용한다.
        """
        return (
            "You will create a CSAT Reading Item 34 (High-difficulty Blank - Phrase/Clause)\n"
            "in QUOTE MODE from the given PASSAGE.\n\n"
            "## ABSOLUTE RULES ABOUT THE PASSAGE\n"
            "- You MUST use the given PASSAGE exactly as it is.\n"
            "- DO NOT rewrite, paraphrase, reorder, add, or delete any sentences.\n"
            "- You may only replace ONE existing phrase/clause with a blank (_____).\n"
            "- The FIRST sentence and the LAST sentence must NEVER contain the blank.\n\n"
            "## HOW TO CHOOSE THE BLANK (RC34-style span)\n"
            "1) Split the PASSAGE into sentences.\n"
            "2) If the passage has 5 or more sentences:\n"
            "   - Choose the blank ONLY from a middle sentence (e.g., 3rd, 4th, or 5th),\n"
            "     NOT from the first or the last sentence.\n"
            "3) If the passage has 3–4 sentences:\n"
            "   - Choose the blank from a middle sentence (NOT the first or last).\n"
            "4) The blanked span must:\n"
            "   (a) ALREADY EXIST VERBATIM in the passage (do NOT invent new text),\n"
            "   (b) have a length of about 7–15 words, and\n"
            "   (c) be either:\n"
            "       - a COMPLETE CLAUSE (can function as a sentence when combined with\n"
            "         its subject), or\n"
            "       - a NOUN PHRASE that can serve as a full constituent (subject,\n"
            "         complement, or object) in the sentence.\n"
            "5) Semantically, the blanked span MUST play a PIVOT ROLE in the discourse:\n"
            "   - CONTRAST / TURNING POINT (e.g., however / but / instead / on the other hand),\n"
            "   - CAUSE–EFFECT or RESULT (e.g., therefore / thus / as a result / this leads to ~),\n"
            "   - ABSTRACT SUMMARY / GENERALIZATION of previous content.\n"
            "   In other words, removing this span should make the overall logical flow of the\n"
            "   passage significantly harder to grasp.\n"
            "6) Replace ONLY that chosen span with exactly five underscores (_____).\n"
            "7) The removed span (blank_text) will be the CORRECT option.\n\n"
            "## OPTIONS (5 CHOICES)\n"
            "- Provide exactly FIVE options.\n"
            "- ALL options must be grammatically compatible with the sentence frame\n"
            "  where the blank appears.\n"
            "- The CORRECT option MUST be (almost) exactly the same as the removed span\n"
            "  copied from the original passage (do NOT paraphrase).\n"
            "- The four WRONG options must be:\n"
            "    · similar in length (roughly 7–15 words), and\n"
            "    · grammatically acceptable in the local sentence frame, but\n"
            "    · logically wrong, less appropriate, or inconsistent with the global\n"
            "      meaning and logical structure of the passage.\n\n"
            "## OUTPUT FORMAT (STRICT JSON ONLY)\n"
            "Return ONE JSON object with the following fields:\n"
            "{\n"
            "  \"question\": \"다음 글의 빈칸에 들어갈 말로 가장 적절한 것은?\",\n"
            "  \"passage\": \"[original passage with EXACTLY ONE blank (_____)]\",\n"
            "  \"options\": [\"opt1\",\"opt2\",\"opt3\",\"opt4\",\"opt5\"],\n"
            "  \"correct_answer\": \"1\"|\"2\"|\"3\"|\"4\"|\"5\",\n"
            "  \"blank_text\": \"[the exact phrase/clause removed from the passage]\",\n"
            "  \"explanation\": \"[Korean explanation of why the correct option is best]\"\n"
            "}\n\n"
            "- \"passage\" MUST be identical to the given PASSAGE, except that one\n"
            "  phrase/clause has been replaced by '_____'.\n"
            "- There must be EXACTLY ONE '_____'.\n"
            "- Do NOT output any text outside this JSON object. No markdown.\n\n"
            "PASSAGE:\n" + (passage or "")
        )

    # ----- 유연 치환 헬퍼: 공백/대소문자 약간 달라도 찾기 -----
    def _replace_blank_fuzzy(self, text: str, span: str) -> str | None:
        """
        text 안에서 span(빈칸으로 만들 구/절)을 최대한 유연하게 찾아
        첫 한 곳만 '_____'로 치환한 문자열을 돌려준다.
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
        pattern = re.escape(s)
        pattern = pattern.replace(r"\ ", r"\s+")
        m = re.search(pattern, t, flags=re.I | re.M)
        if m:
            return t[:m.start()] + "_____" + t[m.end():]

        return None

    def quote_postprocess(self, passage: str, llm_json: dict) -> dict:
        """
        LLM이 반환한 JSON을 RC34 인용용 내부 item 구조로 정리.
        - 1순위: '원본 지문'에서 blank_text/정답 옵션을 찾아 유연하게 빈칸으로 교체.
        - 2순위: 그래도 실패하면 LLM이 준 passage(이미 빈칸 포함)를 폴백으로 사용.
        - 문장 첫/마지막에 빈칸이 오지 않도록 검증.
        """
        orig_passage = passage or ""

        # ----- 필수 필드 추출 -----
        opts = list((llm_json.get("options") or [])[:5])
        if len(opts) != 5:
            raise ValueError("RC34(quote): options must have exactly 5 items")

        ca = str(llm_json.get("correct_answer") or "").strip()
        if ca not in {"1", "2", "3", "4", "5"}:
            # 옵션 텍스트가 들어온 경우 인덱스로 변환
            if ca in opts:
                ca = str(opts.index(ca) + 1)
            else:
                ca = "1"
        correct_idx = int(ca) - 1
        correct_opt = (opts[correct_idx] or "").strip()

        blank_text = (llm_json.get("blank_text") or "").strip()
        if not blank_text:
            blank_text = correct_opt

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
                    "RC34(quote): cannot locate the blank span in the original passage "
                    "and no usable blank found in model passage."
                )

        p = p_with_blank

        # blank 개수 확인
        if p.count("_____") != 1:
            raise ValueError(
                f"RC34(quote): passage must contain exactly ONE blank, found {p.count('_____')}."
            )

        # ----- 문장 위치 검사: 첫/마지막 문장은 금지 -----
        sentences = re.split(r"(?<=[.?!])\s+", p.strip())
        n = len(sentences)
        idx_blank = next((i for i, s in enumerate(sentences) if "_____" in s), -1)
        if idx_blank == -1:
            raise ValueError("RC34(quote): cannot locate blank in sentence split.")

        if n >= 3 and idx_blank in (0, n - 1):
            raise ValueError(
                f"RC34(quote): blank must not be in the first or last sentence "
                f"(found at {idx_blank + 1}/{n})."
            )

        explanation = (llm_json.get("explanation") or "").strip()
        question = (llm_json.get("question") or "").strip() or "다음 글의 빈칸에 들어갈 말로 가장 적절한 것은?"

        item = {
            "question": question,
            "passage": p,
            "options": [o.strip() for o in opts],
            "correct_answer": ca,
            "explanation": explanation,
        }
        return item

    def quote_validate(self, item: dict) -> None:
        """
        인용 모드 검증:
        - passage에 정확히 1개의 빈칸(_____)이 있을 것
        - 보기 5개, 정답 '1'..'5'
        - 빈칸은 첫/마지막 문장에 위치하지 않을 것
        """
        p = (item.get("passage") or "")
        blank_count = p.count("_____")
        if blank_count != 1:
            raise AssertionError(
                f"RC34(quote): passage must contain exactly one blank marker, found {blank_count}"
            )

        opts = item.get("options") or []
        if len(opts) != 5:
            raise AssertionError("RC34(quote): exactly 5 options are required.")

        ca = str(item.get("correct_answer") or "").strip()
        if ca not in {"1", "2", "3", "4", "5"}:
            raise AssertionError("RC34(quote): correct_answer must be '1'..'5'.")

        # 위치 검증
        sentences = re.split(r"(?<=[.?!])\s+", p.strip())
        n = len(sentences)
        idx_blank = next((i for i, s in enumerate(sentences) if '_____' in s), -1)
        if n >= 3 and idx_blank in (0, n - 1):
            raise AssertionError(
                f"RC34(quote): blank must not be in the first or last sentence "
                f"(found at {idx_blank + 1}/{n})."
            )
