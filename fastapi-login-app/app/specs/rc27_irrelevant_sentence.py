from __future__ import annotations
import re
from app.specs._base_mcq import BaseMCQSpec


class RC27Spec(BaseMCQSpec):
    """
    RC27: 안내문 내용 일치/불일치(정답: 불일치) — 5지선다 MCQ
    - 기본 generate 경로는 BaseMCQSpec 로직 유지
    - 인용(quote) 경로에서만 '지문 불변 + 보기/정답/해설만 생성'
    """
    id = "RC27"

    # ===== (기존) generate 경로용 설정 =====
    def system_prompt(self) -> str:
        return (
            "CSAT English RC27 (안내문 불일치). "
            "Return ONLY JSON matching the schema. Use ONLY the provided passage."
        )

    def extra_checks(self, data: dict):
        """
        옵션이 '문장'으로 보이는지 느슨히 점검:
        - 영문/숫자권: ., !, ? 로 끝나거나
        - 한글권: 마침표가 없어도 '다'/'요' 등 서술어 종결로 끝나면 허용
        - 너무 짧은 토막 문장 방지(토큰 4개 이상 또는 글자 8자 이상)
        """
        def is_sentence_like(o: str) -> bool:
            o = (o or "").strip()
            if len(o.split()) >= 4 or len(o) >= 8:
                if re.search(r"[.!?]$", o):
                    return True
                if re.search(r"[다요]$", o):  # 한글 평서/존댓말 종결 허용
                    return True
            return False

        sentence_like = sum(is_sentence_like(o) for o in (data.get("options") or []))
        if sentence_like < 3:
            raise ValueError(
                "RC27 options should be sentence-like (., !, ? or Korean sentence endings) and non-trivial."
            )

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
        - PASSAGE는 절대 수정/재작성/재포맷 금지.
        - LLM은 보기 5개(한국어 문장), 정답("1"~"5"), 해설(한국어),
          어휘 정보(vocabulary_difficulty, low_frequency_words, rationale)만 JSON으로 생성.
        - PASSAGE는 출력 JSON에 포함하지 않고, 외부에서 그대로 주입한다.
        """
        return (
            "You are generating a CSAT-English RC27 multiple-choice item based on a NOTICE/ANNOUNCEMENT style PASSAGE.\n"
            "TASK TYPE: 안내문의 내용과 일치하지 않는 선택지를 고르는 유형입니다.\n"
            "\n"
            "READ-ONLY PASSAGE RULES (VERY IMPORTANT):\n"
            "- The PASSAGE you see is already formatted as a notice.\n"
            "- You MUST NOT modify, paraphrase, reflow, or recreate the PASSAGE in any way.\n"
            "- Do NOT rewrite the dividers, labels, or line breaks.\n"
            "- You will NOT output the passage text in your JSON. It will be injected externally as-is.\n"
            "\n"
            "PASSAGE FORMAT (FOR YOUR UNDERSTANDING ONLY — DO NOT OUTPUT OR CHANGE IT):\n"
            "The notice uses an ASCII-styled layout with the following structure:\n"
            "  1) A top divider line of '=' repeated at least 40 times\n"
            "     (e.g., '============================================').\n"
            "  2) A single line with the EVENT TITLE in ALL CAPS\n"
            "     (e.g., '2025 INTERNATIONAL STUDENT FORUM').\n"
            "  3) An identical divider line of '='.\n"
            "  4) The labeled sections, each on its own line in this exact order and spelling:\n"
            "       Title:, Date:, Location:, Eligibility:, Registration:, Fee:, Contact:, Note:\n"
            "     - Each label is followed by a space and its content on the same line.\n"
            "  5) A bottom divider line identical to the top/between dividers.\n"
            "These details are ONLY to help you interpret the notice accurately. DO NOT reproduce or change this layout.\n"
            "\n"
            "GENERAL OUTPUT RESTRICTIONS:\n"
            "- In your JSON fields (question, options, explanation, vocabulary_difficulty,\n"
            "  low_frequency_words, rationale), do NOT use Markdown formatting (#, ##, **, *, -).\n"
            "- Avoid HTML tags in your outputs except the <u> tag around '않는' in the question if needed.\n"
            "- Do NOT include double quotes inside string values if you can avoid it.\n"
            "\n"
            "OUTPUT KEYS (JSON ONLY):\n"
            "- You MUST return JSON with exactly these keys:\n"
            "  {\"question\",\"options\",\"correct_answer\",\"explanation\",\n"
            "   \"vocabulary_difficulty\",\"low_frequency_words\",\"rationale\"}.\n"
            "- Do NOT include the passage text itself in the JSON.\n"
            "\n"
            "QUESTION:\n"
            "- Korean, about the given 안내문.\n"
            "- It must end with \"내용과 일치하지 <u>않는</u> 것은?\".\n"
            "- You may optionally include the event title before that, as in the example:\n"
            "  \"CLASSICAL LITERATURE EXHIBITION에 관한 다음 안내문의 내용과 일치하지 <u>않는</u> 것은?\".\n"
            "\n"
            "OPTIONS:\n"
            "- Exactly 5 options in Korean.\n"
            "- Each option should be a full sentence-like statement summarizing some detail of the notice\n"
            "  (행사명, 날짜, 기간, 장소, 대상, 참가비, 신청 방법, 특이 사항 등).\n"
            "- 4 options MUST be factually consistent with the PASSAGE.\n"
            "- Exactly 1 option MUST be factually inconsistent (불일치) with the PASSAGE.\n"
            "- Do NOT add any leading numbering or bullets (no ①~⑤, 1., -, etc.).\n"
            "\n"
            "CORRECT_ANSWER:\n"
            "- A STRING among \"1\",\"2\",\"3\",\"4\",\"5\" indicating which option is the incorrect one.\n"
            "- Do NOT put the option text itself here.\n"
            "\n"
            "EXPLANATION (Korean):\n"
            "- Briefly explain why the chosen option is inconsistent with the notice.\n"
            "- Also briefly state that the other options match the notice.\n"
            "\n"
            "VOCABULARY FIELDS (optional but recommended):\n"
            "- vocabulary_difficulty: a short label such as \"CSAT+O3000\".\n"
            "- low_frequency_words: a JSON array of 3–6 lower-frequency ENGLISH words from the PASSAGE\n"
            "  (if no such words exist, you may return an empty array).\n"
            "- rationale (Korean): a short explanation for teachers, which may be similar to explanation.\n"
            "\n"
            "OUTPUT FORMAT:\n"
            "- JSON only, no code fences, no extra commentary.\n"
            "- Do NOT include a trailing comma after the last key.\n"
            "\n"
            "PASSAGE (READ ONLY — DO NOT OUTPUT OR EDIT THIS TEXT):\n"
            f"{passage}"
        )

    def quote_postprocess(self, passage: str, llm_json: dict) -> dict:
        """
        인용 모드 사후처리:
        - LLM이 반환한 question/options/correct_answer/explanation/어휘 정보를 가져오고,
          passage는 인자로 받은 원문을 그대로 주입.
        - BaseMCQSpec.normalize()로 번호/불릿 제거 및 정답 보정.
        """
        question = (llm_json.get("question") or "").strip()
        if not question:
            question = "다음 안내문의 내용과 일치하지 <u>않는</u> 것은?"

        explanation = (llm_json.get("explanation") or "").strip()
        vocab_diff = (llm_json.get("vocabulary_difficulty") or "").strip() or "CSAT+O3000"
        low_freq = llm_json.get("low_frequency_words") or []
        if not isinstance(low_freq, list):
            low_freq = [str(low_freq)]

        rationale = (llm_json.get("rationale") or "").strip()
        if not rationale:
            rationale = explanation

        # passage는 절대 손대지 않고 그대로 주입
        item = {
            "passage": passage or "",
            "question": question,
            "options": list(llm_json.get("options") or []),
            "correct_answer": str(llm_json.get("correct_answer") or "").strip(),
            "explanation": explanation,
            "vocabulary_difficulty": vocab_diff,
            "low_frequency_words": low_freq,
            "rationale": rationale,
        }

        # 공통 정규화(옵션 번호/불릿 제거, 정답 표준화 등)만 수행
        item = self.normalize(item)
        return item

    def quote_validate(self, item: dict) -> None:
        """
        인용 모드 얇은 검증:
        - passage 비어 있지 않음 (외부에서 그대로 주입)
        - 옵션 정확히 5개
        - BaseMCQSpec.validate() + extra_checks() 통과
        """
        if not (item.get("passage") or "").strip():
            raise AssertionError("RC27(quote): passage must not be empty")

        options = item.get("options") or []
        if len(options) != 5:
            raise AssertionError("RC27(quote): exactly 5 options required")

        # MCQ 공통 검증 + extra_checks 재사용
        self.validate(item)
