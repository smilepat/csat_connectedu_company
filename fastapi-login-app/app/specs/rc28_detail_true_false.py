from __future__ import annotations
import re
from typing import Dict, Tuple

from app.specs._base_mcq import BaseMCQSpec
from app.schemas.items_rc28 import RC28Model

FIELD_NAMES = [
    "Title", "Date", "Time", "Location", "Eligibility",
    "Registration", "Fee", "Program", "Benefits", "Contact", "Website", "Note"
]

RE_NEWLINE = re.compile(r"[\r\n]")


class RC28Spec(BaseMCQSpec):
    """
    RC28: 안내문 일치(Notices - Match)
    - generate 경로: 기존 PromptManager 기반 생성용(ASCII 안내문 생성)
    - quote 경로: 이미 주어진 안내문 지문을 '그대로' 두고 보기/정답/해설만 생성
      · 이때 지문은 ASCII 레이아웃일 수도 있고, 일반 안내문 형태일 수도 있음.
    """
    id = "RC28"

    # ===== (기존) generate 경로용 설정 =====
    def system_prompt(self) -> str:
        return (
            "CSAT English RC28 (안내문일치). "
            "Return ONLY JSON matching the schema. "
            "Passage MUST be an ASCII notice with divider lines and key:value fields. "
            "Question MUST use the exact ALL-CAPS title in square brackets. "
            "Only passage may contain newlines; question/options/explanation must be single-line."
        )

    # ---------- 기본 validate ----------
    def validate(self, data: dict):
        """
        Pydantic 스키마로 1차 검증 + extra_checks로 형식/내용 점검.
        """
        RC28Model(**data)
        self.extra_checks(data)
        return data

    def json_schema(self) -> dict:
        return RC28Model.model_json_schema()

    # ---------- 내부 유틸: ASCII 안내문 여부 ----------
    def _split_nonempty(self, passage: str) -> list[str]:
        lines = [ln.rstrip("\r") for ln in passage.split("\n")]
        return [ln for ln in lines if ln.strip()]

    def _is_divider(self, s: str) -> bool:
        s = s.strip()
        return len(s) >= 40 and set(s) == {"="}

    def _looks_ascii_notice(self, nonempty: list[str]) -> bool:
        """
        ASCII 레이아웃인지 판별:
        0) top divider
        1) ALL-CAPS title
        2) middle divider
        ...
        last) bottom divider
        """
        if len(nonempty) < 4:
            return False
        top = nonempty[0]
        mid = nonempty[2]
        bottom = nonempty[-1]
        if not (self._is_divider(top) and self._is_divider(mid) and self._is_divider(bottom)):
            return False
        if top.strip() != mid.strip() or top.strip() != bottom.strip():
            return False
        return True

    # ---------- ASCII 안내문 파서 (generate/ASCII quote에서 사용) ----------
    def _parse_notice_fields(self, passage: str) -> Tuple[str, Dict[str, str]]:
        """
        ASCII 안내문 레이아웃을 전제로 헤더 제목(ALL CAPS)과 key:value 필드를 파싱.
        기대 형식:
          0) "====..." (top divider, ≥40 '=')
          1) ALL-CAPS TITLE (e.g., "ART EXHIBITION SPACE INQUIRY")
          2) "====..." (middle divider, 동일 문자열)
          3..N-2) "Field: Value" 라인들 (FIELD_NAMES 중 하나)
          N-1) "====..." (bottom divider, 동일 문자열)
        """
        nonempty = self._split_nonempty(passage)
        if len(nonempty) < 6:
            raise ValueError("RC28 passage must contain at least 6 non-empty lines (dividers + title + fields).")

        top = nonempty[0]
        header = nonempty[1]
        mid = nonempty[2]
        bottom = nonempty[-1]

        if not (self._is_divider(top) and self._is_divider(mid) and self._is_divider(bottom)):
            raise ValueError("RC28 passage must have top/middle/bottom '=' divider lines.")

        if top.strip() != mid.strip() or top.strip() != bottom.strip():
            raise ValueError("RC28 passage divider lines must be identical.")

        header_title = header.strip()
        if not header_title:
            raise ValueError("RC28 passage must have a non-empty ALL-CAPS title line.")

        field_lines = nonempty[3:-1]
        if not field_lines:
            raise ValueError("RC28 passage must contain key:value field lines between dividers.")

        fields: Dict[str, str] = {}
        for ln in field_lines:
            if ":" not in ln:
                raise ValueError("Each field line in RC28 passage must contain a colon separating field and value.")
            key, val = ln.split(":", 1)
            key = key.strip()
            val = val.strip()
            if key not in FIELD_NAMES:
                raise ValueError(f"Invalid field name in RC28 passage: {key}")
            if key in fields:
                raise ValueError(f"Duplicate field in RC28 passage: {key}")
            if not val or val.endswith(":"):
                raise ValueError(f"Empty or invalid value for field: {key}")
            fields[key] = val

        required = {"Title", "Date", "Location", "Registration", "Contact"}
        missing = required - set(fields.keys())
        if missing:
            raise ValueError(f"Missing required fields for RC28: {', '.join(sorted(missing))}")

        return header_title, fields

    # ---------- 공통 추가 점검(extra_checks) ----------
    def extra_checks(self, data: dict):
        passage = data["passage"]

        # passage: HTML 금지
        if "<" in passage or ">" in passage:
            raise ValueError("RC28 passage must not contain HTML tags.")

        nonempty = self._split_nonempty(passage)
        ascii_notice = self._looks_ascii_notice(nonempty)

        # correct_answer: "1"~"5" 문자열로 통일 (ASCII / 일반 공통)
        raw_ca = data.get("correct_answer")
        ca_str = str(raw_ca).strip()
        if ca_str not in {"1", "2", "3", "4", "5"}:
            raise ValueError("RC28 correct_answer must be a string in {'1','2','3','4','5'}.")
        data["correct_answer"] = ca_str

        # options: 5개, 서로 다른 문장 & single-line & HTML 금지 (공통)
        opts = data.get("options") or []
        if len(opts) != 5:
            raise ValueError("RC28 options must contain exactly 5 items.")
        norm_opts = [str(o or "").strip() for o in opts]
        if len(set(o.lower() for o in norm_opts)) < 5:
            raise ValueError("RC28 options must be five and distinct (case-insensitive).")
        if any(RE_NEWLINE.search(o) for o in norm_opts):
            raise ValueError("RC28 options must be single-line (no newline characters).")
        if any("<" in o or ">" in o for o in norm_opts):
            raise ValueError("RC28 options must not contain HTML tags.")

        # explanation: single-line & HTML 금지 (공통)
        if "explanation" in data:
            exp = str(data["explanation"] or "")
            if RE_NEWLINE.search(exp):
                raise ValueError("RC28 explanation must be single-line (no newline characters).")
            if "<" in exp or ">" in exp:
                raise ValueError("RC28 explanation must not contain HTML tags.")

        # rationale: 있으면 형식만 점검 (공통)
        if "rationale" in data:
            rat = str(data["rationale"] or "")
            if RE_NEWLINE.search(rat):
                raise ValueError("RC28 rationale must be single-line (no newline characters).")
            if "<" in rat or ">" in rat:
                raise ValueError("RC28 rationale must not contain HTML tags.")

        # 부정 표현 너무 많은지(트릭 피하기) (공통)
        neg_patterns = ("않", "아니", "없", "불가", "금지")
        if sum(any(p in o for p in neg_patterns) for o in norm_opts) >= 3:
            raise ValueError("RC28: Too many negative-form options. Avoid trivial negation tells.")

        # --- 여기서부터 ASCII 안내문인 경우에만 추가 엄격 검증 ---
        if ascii_notice:
            header_title, _fields = self._parse_notice_fields(passage)

            q = (data.get("question") or "").strip()
            if RE_NEWLINE.search(q):
                raise ValueError("RC28 question must be single-line (no newline characters).")
            expected_q = f"[{header_title}]에 관한 다음 안내문의 내용과 일치하는 것은?"
            if q != expected_q:
                raise ValueError(
                    f"RC28 question must be exactly: '{expected_q}' (got: '{q}')"
                )
        else:
            # 일반 안내문(quote 모드 등)인 경우:
            # - question은 한 줄만 확인하고, 내용은 느슨하게 허용
            q = (data.get("question") or "").strip()
            if RE_NEWLINE.search(q):
                raise ValueError("RC28 question must be single-line (no newline characters).")
            if "<" in q or ">" in q:
                raise ValueError("RC28 question must not contain HTML tags.")
            # 여기서는 [Title] 패턴까지 강제하지 않음 (LLM이 이미 생성했고, 안내문 구조가 제각각일 수 있음)

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
        - PASSAGE는 안내문이며, 절대 수정/재작성/재포맷 금지.
        - LLM은 question/options/correct_answer/explanation/rationale만 JSON으로 생성.
        - PASSAGE는 출력 JSON에 포함하지 않고, 외부에서 그대로 주입한다.
        """
        # 가능하면 ASCII 레이아웃에서 헤더 제목 추출, 아니면 빈 문자열
        try:
            nonempty = self._split_nonempty(passage)
            header_title = ""
            if self._looks_ascii_notice(nonempty):
                header_title, _ = self._parse_notice_fields(passage)
        except Exception:
            header_title = ""

        title_hint = (
            f'- EVENT_TITLE (if present as ALL-CAPS between dividers) is: "{header_title}".\n'
            if header_title else
            "- EVENT_TITLE is the main heading or first line of the notice.\n"
        )

        question_hint = (
            f"- A natural question format is:\n"
            f"  \"[{header_title}]에 관한 다음 안내문의 내용과 일치하는 것은?\"\n"
            if header_title else
            "- Use the main title of the notice inside square brackets in the question if clear.\n"
        )

        return (
            "You are generating a CSAT-English RC28 (Notice Match) item in QUOTE MODE.\n"
            "\n"
            "GOAL:\n"
            "- Use ONLY the given PASSAGE (a notice) to create a multiple-choice item where\n"
            "  exactly ONE option is factually consistent with the notice, and the other four are not.\n"
            "- DO NOT modify, rewrite, summarize, or reformat the PASSAGE.\n"
            "- DO NOT output the passage text in your JSON. It will be supplied externally.\n"
            "\n"
            "PASSAGE FORMAT (FOR YOUR UNDERSTANDING ONLY — DO NOT OUTPUT OR CHANGE IT):\n"
            "- The passage is a notice about an event (career day, exhibition, tour, etc.).\n"
            "- It may or may not use ASCII divider lines and key:value fields.\n"
            "- Your job is ONLY to read it and compare facts.\n"
            "\n"
            "QUESTION (Korean):\n"
            "- Single-line, no HTML/Markdown.\n"
            "- It should ask which option matches the content of the notice.\n"
            + title_hint +
            question_hint +
            "\n"
            "OPTIONS (Korean):\n"
            "- Exactly 5 Korean sentences.\n"
            "- Each option must be a single line (no '\\n').\n"
            "- Each option states some fact about the event (일정, 장소, 참가 대상, 참가비, 신청 방법, 혜택 등).\n"
            "- Exactly ONE option must be fully consistent with the PASSAGE (일치).\n"
            "- The other FOUR must contain incorrect, altered, or unrelated details.\n"
            "- Avoid trivial negation patterns like '~않다', '~없다', '불가', '금지' in many options;\n"
            "  instead, use detail mismatches (wrong dates, wrong times, wrong fees, wrong conditions, etc.).\n"
            "- Do NOT prefix options with any numbering or bullets (no ①~⑤, 1., -, etc.).\n"
            "\n"
            "CORRECT_ANSWER:\n"
            "- A STRING among \"1\",\"2\",\"3\",\"4\",\"5\" indicating which option is the correct (matching) one.\n"
            "- Do NOT put the option text itself here.\n"
            "\n"
            "EXPLANATION & RATIONALE (Korean):\n"
            "- explanation: single-line.\n"
            "- Briefly state why the chosen option matches the notice and why the others are wrong.\n"
            "- rationale: you may repeat or slightly expand the explanation for teacher use.\n"
            "- Both fields must not contain HTML/Markdown.\n"
            "\n"
            "OUTPUT FORMAT (STRICT):\n"
            "- Return exactly ONE JSON object with the following keys ONLY:\n"
            '  {\"question\",\"options\",\"correct_answer\",\"explanation\",\"rationale\"}.\n'
            "- Do NOT include the passage text in the JSON.\n"
            "- No code fences, no backticks, no extra commentary.\n"
            "\n"
            "Example SHAPE (do NOT copy values):\n"
            "{\n"
            '  \"question\": \"[Career Day with a Big Data Expert]에 관한 다음 안내문의 내용과 일치하는 것은?\",\n'
            '  \"options\": [\"...\", \"...\", \"...\", \"...\", \"...\"],\n'
            '  \"correct_answer\": \"2\",\n'
            '  \"explanation\": \"정답은 ②번입니다. ...\",\n'
            '  \"rationale\": \"정답은 ②번입니다. ...\"\n'
            "}\n"
            "\n"
            "PASSAGE (READ ONLY — DO NOT OUTPUT OR EDIT THIS TEXT):\n"
            f"{passage}"
        )

    def quote_postprocess(self, passage: str, llm_json: dict) -> dict:
        """
        인용 모드 사후처리:
        - LLM이 반환한 question/options/correct_answer/explanation/rationale를 가져오고,
          passage는 인자로 받은 원문을 그대로 주입한다.
        - passage에 대해서는 어떤 strip/가공도 하지 않는다(구조 100% 유지).
        - correct_answer는 문자열 \"1\"~\"5\"로 통일.
        """
        raw_question = llm_json.get("question") or ""
        raw_options = llm_json.get("options") or []
        raw_ca = llm_json.get("correct_answer", "")
        raw_expl = llm_json.get("explanation") or ""
        raw_rat = llm_json.get("rationale") or ""

        question = str(raw_question).strip()
        options = [str(o or "").strip() for o in list(raw_options)]
        ca_str = str(raw_ca).strip()
        explanation = str(raw_expl).strip()
        rationale = str(raw_rat).strip() or explanation

        item = {
            "passage": passage,        # 🔴 원문 그대로
            "question": question,
            "options": options,
            "correct_answer": ca_str,  # 문자열
            "explanation": explanation,
            "rationale": rationale,
        }

        # normalize가 passage를 건드릴 수 있으므로, 호출 후 다시 원본을 덮어쓴다.
        try:
            norm = self.normalize(dict(item))
            norm["passage"] = passage
            item = norm
        except Exception:
            pass

        return item

    def quote_validate(self, item: dict) -> None:
        """
        인용 모드 검증:
        - passage 비어 있지 않음
        - options 정확히 5개
        - RC28Model + extra_checks() 재사용
        """
        if not (item.get("passage") or "").strip():
            raise AssertionError("RC28(quote): passage must not be empty")

        options = item.get("options") or []
        if len(options) != 5:
            raise AssertionError("RC28(quote): exactly 5 options required")

        RC28Model(**item)
        self.extra_checks(item)
