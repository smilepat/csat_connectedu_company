from __future__ import annotations
import re
from typing import List
from pydantic import BaseModel, Field, field_validator
from app.specs.base import GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like


class RC33Model(BaseModel):
    question: str
    passage: str
    options: list[str] = Field(min_length=5, max_length=5)
    correct_answer: str
    explanation: str

    @field_validator("question", "passage", "explanation", "correct_answer", mode="before")
    @classmethod
    def _strip(cls, v):
        return (v or "").strip()

    @field_validator("options", mode="before")
    @classmethod
    def _opts(cls, v):
        return [str(o).strip() for o in (v or [])]


class RC33Spec:
    id = "RC33"

    # ======================
    # 기본(생성) 모드 - 기존 유지
    # ======================
    def system_prompt(self) -> str:
        return (
            "CSAT English RC33 (고난도 구/절 빈칸). "
            "Return ONLY JSON matching the schema. Use ONLY the provided passage."
        )

    def build_prompt(self, ctx: GenContext) -> str:
        """
        기본 생성 모드는 그대로 유지 (PromptManager 기반).
        인용 모드는 아래 quote_* 훅으로 분리.
        """
        item_type = (ctx.get("item_id") or self.id)
        return PromptManager.generate(
            item_type=item_type,
            difficulty=(ctx.get("difficulty") or "medium"),
            topic_code=(ctx.get("topic") or "random"),
            passage=(ctx.get("passage") or ""),
        )

    # ---------- helpers (공용) ----------
    def _answer_to_index(self, answer: str, options: List[str]) -> str:
        """
        RC32와 동일 패턴:
        - "1"~"5"면 그대로
        - 숫자면 정규화
        - 그 외에는 options에서 텍스트 매칭 → index
        """
        a = str(answer or "").strip()
        if a in {"1", "2", "3", "4", "5"}:
            return a
        if a.isdigit() and 1 <= int(a) <= 5:
            return str(int(a))
        try:
            return str(options.index(a) + 1)
        except ValueError:
            # 매칭 실패 시 안전 폴백
            return "1" if options else a

    def normalize(self, data: dict) -> dict:
        """
        공통 normalize:
        - coerce_mcq_like 적용
        - correct_answer를 무조건 "1"~"5" 인덱스로 정규화
        """
        d = coerce_mcq_like(data)
        if d.get("options") and d.get("correct_answer") is not None:
            d["correct_answer"] = self._answer_to_index(d["correct_answer"], d["options"])
        return d

    def validate(self, data: dict):
        m = RC33Model.model_validate(data)
        pas = (data.get("passage") or "").lower()

        # 1) 반드시 지문 안에 빈칸 마커가 있어야 함
        if "_____" not in pas and "<blank>" not in pas:
            raise ValueError("RC33 requires a blank marker (_____ or <blank>).")

        # 2) 옵션 평균 길이 3단어 이상 권장(복합성 확보)
        opts = data.get("options", [])
        if opts and (sum(len(o.split()) for o in opts) / len(opts)) < 3.0:
            raise ValueError("RC33 options should be complex enough (avg length ≥ 3 words).")

        # 3) correct_answer 형식: 기본적으로 '1'..'5' 사용
        ca = str(data.get("correct_answer") or "").strip()
        if ca not in {"1", "2", "3", "4", "5"}:
            raise ValueError("RC33 correct_answer must be an index string '1'..'5'.")

        return m

    def json_schema(self) -> dict:
        return RC33Model.model_json_schema()

    def repair_budget(self) -> dict:
        return {"fixer": 1, "regen": 1, "timeout_s": 15}

    # =========================
    # 인용(quote) 전용 훅 — RC33 전용
    # =========================
    def has_quote_support(self) -> bool:
        return True

    def quote_build_prompt(self, passage: str) -> str:
        """
        RC33 인용(quote) 모드 프롬프트
        - 길이/형식 가이드는 주되, 하드 에러는 postprocess에서 완화
        """
        return (
            "You will create ONE CSAT English item of type RC33 "
            "(high-level clause blank) in QUOTE MODE from the given PASSAGE.\n\n"
            "============================\n"
            "ABSOLUTE RULES ABOUT PASSAGE\n"
            "============================\n"
            "1) You MUST use the given PASSAGE exactly as it is.\n"
            "   - Do NOT rewrite, paraphrase, summarize, reorder, add, or delete sentences.\n"
            "   - You may ONLY replace ONE existing clause/short sentence with a blank.\n"
            "2) The blank marker MUST be exactly five underscores: _____\n"
            "3) The passage you output must be identical to the original PASSAGE except\n"
            "   for that ONE clause/short sentence being replaced by '_____'.\n\n"
            "============================\n"
            "HOW TO CHOOSE THE BLANK (RC33 STYLE)\n"
            "============================\n"
            "A. Identify a single clause or short sentence that ALREADY EXISTS in the PASSAGE\n"
            "   and satisfies ALL of the following:\n"
            "   1) It is a single clause/phrase, not a long multi-clause sentence.\n"
            "      - Ideally: between 6 and 18 words.\n"
            "      - No semicolons; at most one comma.\n"
            "   2) Its grammatical form and style can be used to build five parallel options,\n"
            "      like typical RC33 answer lines:\n"
            "        · \"allow the colony to regulate its workforce\"\n"
            "        · \"participate in decisions to change the rules\"\n"
            "        · \"any number of them could be substituted for one another without loss\"\n"
            "   3) Semantically, it summarizes, defines, or evaluates the passage as a whole.\n\n"
            "B. Replace ONLY that chosen clause/phrase with '_____'.\n"
            "   - The rest of the PASSAGE must remain exactly unchanged.\n"
            "   - There must be EXACTLY ONE blank in the final passage.\n\n"
            "============================\n"
            "OPTIONS (5 CHOICES)\n"
            "============================\n"
            "You must create 5 options that all fit grammatically into the blank.\n"
            "- All options share the same grammatical pattern as blank_text.\n"
            "- The correct option is the exact blank_text from the passage.\n"
            "- The 4 distractors reuse key vocabulary but twist or partially distort\n"
            "  the overall meaning of the passage.\n\n"
            "============================\n"
            "OUTPUT FORMAT (STRICT JSON ONLY)\n"
            "============================\n"
            "Return ONLY ONE JSON object:\n"
            "{\n"
            "  \"question\": \"다음 글의 빈칸에 들어갈 말로 가장 적절한 것은?\",\n"
            "  \"passage\": \"[original passage with EXACTLY ONE '_____']\",\n"
            "  \"options\": [\"option1\", \"option2\", \"option3\", \"option4\", \"option5\"],\n"
            "  \"correct_answer\": \"the EXACT string of the correct option (must equal one of options)\",\n"
            "  \"blank_text\": \"the EXACT clause/phrase removed from the passage\",\n"
            "  \"explanation\": \"짧은 한국어 해설\"\n"
            "}\n\n"
            "PASSAGE:\n" + (passage or "")
        )

    # --- 공백 정규화 유틸 ---
    def _norm_spaces(self, s: str) -> str:
        s = re.sub(r"\s+", " ", s or "").strip()
        s = re.sub(r"\s+([.,;:!?])", r"\1", s)
        return s

    # --- 유연 치환 헬퍼 ---
    def _replace_blank_fuzzy(self, text: str, span: str) -> str | None:
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

    # --- 너무 긴 blank_text를 짧게 자르는 헬퍼 ---
    def _shrink_span_to_window(self, passage: str, span: str,
                               min_words: int = 6, max_words: int = 18) -> str:
        """
        span이 너무 길면:
        - span을 단어 단위로 쪼갠 뒤
        - 길이 min_words~max_words인 모든 연속 부분문자열 후보를 만들어
        - 그 중 실제 passage 안에 그대로 포함되는 첫 번째 후보를 반환.
        없으면 원본 span 유지.
        """
        if not span:
            return span

        words = span.split()
        wc = len(words)
        if wc <= max_words:
            return span  # 이미 충분히 짧음

        # 긴 경우: window를 줄여가며 후보 탐색
        for window in range(max_words, min_words - 1, -1):
            if window > wc:
                continue
            for start in range(0, wc - window + 1):
                cand = " ".join(words[start:start + window])
                if cand in passage:
                    return cand

        # 적당한 후보를 못 찾으면 원본 유지
        return span

    def quote_postprocess(self, passage: str, llm_json: dict) -> dict:
        """
        LLM이 RC33 인용 모드에서 반환한 JSON을 최종 item 구조로 정리.

        - 1순위: '원본 지문'에서 blank_text(또는 correct_answer 텍스트)를 찾아 유연하게 빈칸으로 교체.
        - blank_text가 너무 길면 6~18단어짜리 하위 절로 자동 축약.
        - 정답 옵션도 이 축약된 절로 덮어씌움.
        - 최종 correct_answer는 '1'..'5' 인덱스로 맞춰서 반환.
        """
        orig_passage = passage or ""

        # ----- 필수 필드 추출 -----
        opts = list((llm_json.get("options") or [])[:5])
        if len(opts) != 5:
            raise ValueError("RC33(quote): options must have exactly 5 items")

        ca_raw = (llm_json.get("correct_answer") or "").strip()
        blank_text = (llm_json.get("blank_text") or "").strip()

        # 우선순위: blank_text → correct_answer 텍스트 → opt[0]
        if blank_text:
            correct_text = blank_text.strip()
        elif ca_raw and ca_raw not in {"1", "2", "3", "4", "5"}:
            correct_text = ca_raw.strip()
        else:
            correct_text = opts[0].strip()

        # 일단 options 안에 없으면 / 있으면 상관없이,
        # 나중에 우리가 강제로 맞춰줄 예정
        # → 먼저 길이 축약
        shrunk = self._shrink_span_to_window(orig_passage, correct_text,
                                             min_words=6, max_words=18)
        correct_text = shrunk or correct_text

        # 정답 옵션 인덱스: 있으면 그 자리, 없으면 0번으로
        if correct_text in opts:
            correct_idx = opts.index(correct_text)
        else:
            correct_idx = 0
        opts[correct_idx] = correct_text  # 정답 옵션을 축약된 절로 강제 덮어쓰기
        ca_index = str(correct_idx + 1)

        # ----- 원본 지문에서 blank 교체 시도 -----
        p_with_blank = (
            self._replace_blank_fuzzy(orig_passage, correct_text)
            or (blank_text and self._replace_blank_fuzzy(orig_passage, blank_text))
        )

        if not p_with_blank:
            llm_passage = (llm_json.get("passage") or "").strip()
            if "_____" in llm_passage:
                p_with_blank = llm_passage
            else:
                raise ValueError(
                    "RC33(quote): cannot locate the blank span in the original passage "
                    "and no usable blank found in model passage."
                )

        p = p_with_blank

        if p.count("_____") != 1:
            raise ValueError(
                f"RC33(quote): passage must contain exactly ONE blank, found {p.count('_____')}."
            )

        explanation = (llm_json.get("explanation") or "").strip()

        item = {
            "question": "다음 글의 빈칸에 들어갈 말로 가장 적절한 것은?",
            "passage": p,
            "options": [o.strip() for o in opts],
            "correct_answer": ca_index,       # 인덱스로 통일
            "explanation": explanation,
            "_blank_text": correct_text,      # 실제 사용된 짧은 절/구
        }
        return item

    def quote_validate(self, item: dict) -> None:
        """
        RC33 인용 모드 검증:
        - passage에 정확히 1개의 빈칸(_____)이 있을 것
        - 보기 5개
        - correct_answer는 '1'..'5'
        - (길이 제한은 하드 에러 X: postprocess에서 축약 이미 시도)
        """
        p = (item.get("passage") or "")
        blank_count = p.count("_____")
        if blank_count != 1:
            raise AssertionError(
                f"RC33(quote): passage must contain exactly one blank marker, found {blank_count}"
            )

        opts = item.get("options") or []
        if len(opts) != 5:
            raise AssertionError("RC33(quote): exactly 5 options are required.")

        ca = str(item.get("correct_answer") or "").strip()
        if ca not in {"1", "2", "3", "4", "5"}:
            raise AssertionError("RC33(quote): correct_answer must be '1'..'5'.")
