from __future__ import annotations
from typing import Dict, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.specs.base import GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like
import re

_VALID_KEYS = ("(A)", "(B)", "(C)")


class RC37Model(BaseModel):
    model_config = ConfigDict(extra="ignore")  # 출력에 rationale 등 추가 필드가 와도 무시

    question: str
    intro_paragraph: str
    passage_parts: Dict[str, str]  # "(A)","(B)","(C)" 키 필수
    options: list[str] = Field(min_length=5, max_length=5)
    correct_answer: str  # "1"~"5" 권장
    explanation: str

    @field_validator("question", "intro_paragraph", "explanation", "correct_answer", mode="before")
    @classmethod
    def _strip(cls, v):
        # None이면 빈 문자열, 그 외는 항상 문자열로 변환 후 strip
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("options", mode="before")
    @classmethod
    def _opts(cls, v):
        return [str(o).strip() for o in (v or [])]

    @field_validator("passage_parts", mode="before")
    @classmethod
    def _pp(cls, v):
        v = v or {}
        # 키를 "(A)","(B)","(C)" 로 강제
        fixed = {}
        for k in _VALID_KEYS:
            if isinstance(v, dict) and k in v and v[k]:
                fixed[k] = str(v[k]).strip()
        return fixed


class RC37Spec:
    id = "RC37"

    # ============================================================
    # 기본 생성용 (compat)
    # ============================================================
    def system_prompt(self) -> str:
        # 구조를 명확히 가이드: intro + (A)(B)(C), 정답은 인덱스(1~5)
        return (
            "CSAT English RC37 (순서 배열 고난도). "
            "You MUST return ONLY JSON that matches the schema: "
            "{question, intro_paragraph, passage_parts:{'(A)':'...', '(B)':'...', '(C)':'...'}, "
            "options:[5 items like '(B)-(C)-(A)'], correct_answer:'1-5', explanation}. "
            "Use ONLY the provided passage (do not add external facts)."
        )

    def build_prompt(self, ctx: GenContext) -> str:
        item_type = (ctx.get("item_id") or self.id)
        return PromptManager.generate(
            item_type=item_type,
            difficulty=(ctx.get("difficulty") or "medium"),
            topic_code=(ctx.get("topic") or "random"),
            passage=(ctx.get("passage") or "")
        )

    # ---- passage 파싱(compat/백업용) ----------------------------------------
    def _parse_passage_to_parts(self, passage: str) -> tuple[str, dict]:
        """
        통짜 passage에서 intro + (A)/(B)/(C) 추출 시도.
        (A)/(B)/(C) 마커가 없으면 intro만 채우고 parts는 비움.
        """
        text = (passage or "").strip()
        if not text:
            return "", {}

        parts: Dict[str, str] = {}
        intro = text

        # 1차: 줄바꿈 + (A)(B)(C) 패턴
        splitter = re.split(r"\n\s*\((A|B|C)\)\s*", text)
        # 예: [intro, 'A', a_text, 'B', b_text, 'C', c_text]
        if len(splitter) >= 7 and splitter[1] == "A" and splitter[3] == "B" and splitter[5] == "C":
            intro = splitter[0].strip()
            parts["(A)"] = splitter[2].strip()
            parts["(B)"] = splitter[4].strip()
            parts["(C)"] = splitter[6].strip()
            return intro, parts

        # 2차: 빈 줄 2개 기준 블록 + "(A) ..." 패턴
        blocks = re.split(r"\n{2,}", text)
        label_re = re.compile(r"^\((A|B|C)\)\s*")
        tmp = {}
        intro_chunks = []
        for blk in blocks:
            s = blk.strip()
            if not s:
                continue
            m = label_re.match(s)
            if m:
                key = f"({m.group(1)})"
                tmp[key] = label_re.sub("", s).strip()
            else:
                intro_chunks.append(s)
        if tmp:
            intro = "\n\n".join([ch for ch in intro_chunks if ch]).strip()
            for k in _VALID_KEYS:
                if k in tmp:
                    parts[k] = tmp[k]
        return intro, parts

    def _answer_to_index(self, answer: str, options: list[str]) -> str:
        """
        정답이 '(B)-(C)-(A)' 같이 왔을 때 옵션 인덱스('1'~'5')로 변환.
        숫자(예: 3)로 와도 안전하게 처리.
        """
        a = "" if answer is None else str(answer).strip()

        # 이미 '1'~'5' 형태면 그대로 사용
        if a in {"1", "2", "3", "4", "5"}:
            return a

        # 패턴 문자열로 옵션 리스트에서 찾기
        try:
            idx = options.index(a)
            return str(idx + 1)
        except ValueError:
            # 못 찾으면 그대로 두고 validate 단계에서 걸리게 함
            return a

    def normalize(self, data: dict) -> dict:
        data = dict(data or {})

        # ---- 0) 방어적 캐스팅: 주요 필드를 문자열로 정규화 ----
        for key in ("question", "intro_paragraph", "explanation", "correct_answer"):
            if key in data and data[key] is not None:
                data[key] = str(data[key]).strip()

        # options가 리스트일 때 각 요소를 문자열로
        if isinstance(data.get("options"), list):
            data["options"] = [str(o).strip() for o in data["options"]]

        # passage_parts가 dict일 때 각 값 문자열로
        if isinstance(data.get("passage_parts"), dict):
            data["passage_parts"] = {
                k: ("" if v is None else str(v).strip())
                for k, v in data["passage_parts"].items()
            }

        # 1) passage → (intro_paragraph, passage_parts) 자동 변환
        if not data.get("intro_paragraph") and not data.get("passage_parts"):
            if data.get("passage"):
                intro, parts = self._parse_passage_to_parts(data.get("passage", ""))
                if intro and parts:
                    data["intro_paragraph"] = intro
                    data["passage_parts"] = parts
                elif intro and not parts:
                    data["intro_paragraph"] = intro
                    data.setdefault("passage_parts", {})

        # 2) correct_answer가 서술형/패턴/숫자일 때 인덱스로 치환
        if data.get("options") and data.get("correct_answer") is not None:
            data["correct_answer"] = self._answer_to_index(
                data["correct_answer"], data["options"]
            )

        # 3) 공통 MCQ 정규화(공백, 줄바꿈 등 정리)
        data = coerce_mcq_like(data)
        return data

    # ---- Validation -----------------------------------------------------------
    def validate(self, data: dict):
        # 필수 키 검사
        pp = (data.get("passage_parts") or {})
        missing = [k for k in _VALID_KEYS if k not in pp or not str(pp.get(k)).strip()]
        if missing:
            raise ValueError(f"RC37 passage_parts missing sections: {', '.join(missing)}")

        # 옵션 중복/유사 금지(대소문자 무시)
        opts = data.get("options", [])
        if len(opts) != 5:
            raise ValueError("RC37 options must have exactly 5 items.")
        if len(set(o.lower() for o in opts)) < 5:
            raise ValueError("RC37 options must be distinct (avoid near duplicates).")

        # 정답은 '1'~'5'
        ca = str(data.get("correct_answer", "")).strip()
        if ca not in {"1", "2", "3", "4", "5"}:
            raise ValueError("RC37 correct_answer must be one of '1','2','3','4','5'.")

        # Pydantic 최종 검증
        m = RC37Model.model_validate(data)
        return m

    # ---- Schema / budget ------------------------------------------------------
    def json_schema(self) -> dict:
        return RC37Model.model_json_schema()

    def repair_budget(self) -> dict:
        # RC37은 포맷 오류가 잦아 살짝 여유를 둡니다.
        return {"fixer": 2, "regen": 2, "timeout_s": 20}

    # ============================================================
    #  인용(quote) 모드용 헬퍼들
    # ============================================================

    def has_quote_support(self) -> bool:
        """
        RC35와 동일한 패턴: 라우터에서 인용 모드 지원 여부 확인.
        """
        return True

    def quote_build_prompt(self, passage: str) -> str:
        """
        RC37 인용(quote) 모드 프롬프트.
        - 기본적으로 '주어진 글 다음에 이어질 글의 순서' 문항을 그대로 유지하되,
          정답/해설만 필요할 때 사용할 수 있음.
        - 필요 없다면 실제 파이프라인에서 호출하지 않아도 됩니다.
        """
        base_question = "주어진 글 다음에 이어질 글의 순서로 가장 적절한 것은? [3점]"
        return (
            "You will create a CSAT English RC37 item (paragraph ordering) in QUOTE MODE.\n"
            "Use the given PASSAGE as is. Do not reorder or paraphrase the paragraphs.\n"
            "Your job is only to provide the JSON fields for question, intro_paragraph,\n"
            "passage_parts (A,B,C in the GIVEN order), five options like '(B)-(C)-(A)',\n"
            "correct_answer as a STRING digit '1'..'5', and a brief explanation.\n\n"
            f"Use the question exactly as: \"{base_question}\".\n"
            "Return ONLY JSON matching the RC37 schema.\n\n"
            "[PASSAGE]\n"
            f"{passage}\n"
        )

    # ---------- 패턴 정규화 / 재배열 공통 로직 -------------------
    def _normalize_pattern(self, pattern: str) -> str:
        """
        '(B)-(A)-(C)', ' b - a - c ' 등 다양한 변형을 'B-A-C' 형태로 표준화.
        """
        if pattern is None:
            return ""
        p = str(pattern).upper().strip()
        # 괄호 제거
        p = p.replace("(", "").replace(")", "")
        # 여러 종류의 구분자를 '-'로 통일
        p = re.sub(r"\s*[-~>\u2192]\s*", "-", p)
        # 불필요 공백 제거
        p = re.sub(r"\s+", "", p)
        return p

    def _extract_correct_pattern(self, options: List[str], correct_answer: str | int) -> str:
        """
        - correct_answer가 '1'~'5' 또는 int(1~5)라면 options에서 해당 패턴을 가져오고,
        - 그 외에는 correct_answer 자체를 패턴으로 간주.
        """
        if options is None:
            options = []

        if correct_answer is not None:
            s = str(correct_answer).strip()
            if s in {"1", "2", "3", "4", "5"}:
                idx = int(s) - 1
                if 0 <= idx < len(options):
                    return self._normalize_pattern(options[idx])

        # 그 외: correct_answer를 직접 패턴으로 사용
        return self._normalize_pattern(str(correct_answer or ""))

    def _reorder_paragraphs(self, paragraphs: List[str], pattern: str) -> List[str]:
        """
        3개의 문단을 1,2,3으로 명명하고,
        A→문단1, B→문단2, C→문단3으로 매핑한 뒤,
        패턴(B-A-C 등) 순서대로 재구성한다.
        """
        if len(paragraphs) != 3:
            paragraphs = (paragraphs + ["", "", ""])[:3]

        # A,B,C → 1,2,3 → 인덱스 0,1,2
        letter_to_idx = {"A": 0, "B": 1, "C": 2}
        norm = self._normalize_pattern(pattern)

        if not norm:
            # 패턴이 없으면 원래 순서 유지
            return paragraphs

        letters = norm.split("-")
        ordered: List[str] = []
        for ch in letters:
            idx = letter_to_idx.get(ch)
            if idx is None:
                continue
            ordered.append(paragraphs[idx])

        # 혹시 3개가 안 채워졌으면 남은 문단을 뒤에 이어붙이기
        if len(ordered) < 3:
            used = set(ordered)
            for para in paragraphs:
                if para not in used:
                    ordered.append(para)

        return ordered[:3]

    def _split_intro_and_rest(self, passage: str) -> tuple[str, str]:
        """
        (A),(B),(C)가 없는 통짜 지문에서
        - 첫 문장을 '도입(intro)'으로,
        - 나머지를 '하단 텍스트(rest)'로 분리.
        (인용 백업용)
        """
        text = (passage or "").strip()
        if not text:
            return "", ""

        # 첫 문장 경계 찾기 (. ! ? 뒤 공백 기준)
        m = re.search(r"([.!?])\s+", text)
        if not m:
            # 문장부호가 없으면, 첫 줄을 도입으로 보고 나머지를 하단으로
            lines = text.splitlines()
            if len(lines) == 1:
                return text, ""
            intro = lines[0].strip()
            rest = "\n".join(lines[1:]).strip()
            return intro, rest

        end_idx = m.end()
        intro = text[:end_idx].strip()
        rest = text[end_idx:].strip()
        return intro, rest

    def _split_rest_into_three(self, rest: str) -> List[str]:
        """
        '하단 텍스트'를 적당히 3부분으로 분할.
        (인용 백업용)
        """
        if not rest:
            return ["", "", ""]

        # 문장 분리 (. ! ? 뒤의 공백 기준)
        sentences = re.split(r"(?<=[.!?])\s+", rest)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return ["", "", ""]

        if len(sentences) <= 3:
            parts = sentences + [""] * (3 - len(sentences))
            return parts[:3]

        # 문장 수를 3등분
        n = len(sentences)
        base = n // 3
        rem = n % 3
        sizes = [base + (1 if i < rem else 0) for i in range(3)]

        parts: List[str] = []
        idx = 0
        for size in sizes:
            chunk = " ".join(sentences[idx: idx + size]).strip()
            parts.append(chunk)
            idx += size

        if len(parts) < 3:
            parts += [""] * (3 - len(parts))
        return parts[:3]

    # ============================================================
    #  quote 모드 전용 후처리
    # ============================================================

    def quote_postprocess(self, passage: str, llm_json: dict) -> dict:
        """
        RC37 인용용 아이템 생성.
        - LLM이 준 intro_paragraph / passage_parts를 우선 활용.
        - 정답 패턴(예: '(B)-(C)-(A)')에 따라 문단 순서를 재구성.
        - 재구성된 순서를 (A),(B),(C)에 1,2,3으로 다시 매핑해서 반환.
        """
        raw_passage = (llm_json.get("passage") or passage or "").strip()

        # 1) intro 우선순위: LLM → 파싱 → fallback
        intro = (llm_json.get("intro_paragraph") or "").strip()
        if not intro and raw_passage:
            intro_parsed, _ = self._parse_passage_to_parts(raw_passage)
            if intro_parsed:
                intro = intro_parsed

        # 2) 원본 문단: LLM이 준 passage_parts를 최우선 사용
        pp = llm_json.get("passage_parts") or {}
        paragraphs: List[str] = []
        if all(k in pp and str(pp[k]).strip() for k in _VALID_KEYS):
            paragraphs = [
                str(pp["(A)"]).strip(),
                str(pp["(B)"]).strip(),
                str(pp["(C)"]).strip(),
            ]
        else:
            # 라벨이 없으면: passage 재파싱 → 그마저 안 되면 3분할
            intro2, parts_abc = self._parse_passage_to_parts(raw_passage)
            if parts_abc:
                if not intro and intro2:
                    intro = intro2
                paragraphs = [
                    parts_abc.get("(A)", "").strip(),
                    parts_abc.get("(B)", "").strip(),
                    parts_abc.get("(C)", "").strip(),
                ]
            else:
                # 최후의 수단: 통짜를 도입/하단 나눠서 3분할
                intro3, rest = self._split_intro_and_rest(raw_passage)
                if not intro and intro3:
                    intro = intro3
                paragraphs = self._split_rest_into_three(rest)

        # 3) 정답 패턴 추출
        options = llm_json.get("options") or []
        correct_answer = llm_json.get("correct_answer") or ""
        pattern = self._extract_correct_pattern(options, correct_answer)

        # 4) 패턴에 따라 문단 재구성 (예: B-C-A → [문단2, 문단3, 문단1])
        reordered = self._reorder_paragraphs(paragraphs, pattern)

        # 5) 인용용 item 구성: 재구성된 순서를 (A),(B),(C)에 1,2,3으로 다시 할당
        item = {
            "question": (llm_json.get("question") or
                         "주어진 글 다음에 이어질 글의 순서로 가장 적절한 것은?"),
            "intro_paragraph": intro,
            "passage_parts": {
                "(A)": reordered[0],
                "(B)": reordered[1],
                "(C)": reordered[2],
            },
            "options": options,
            # quote 모드에서도 정답 인덱스는 그대로 유지(또는 필요시 패턴대로 바꿔도 됨)
            "correct_answer": str(correct_answer).strip(),
            "explanation": (llm_json.get("explanation") or "").strip(),
        }
        return item

    def quote_validate(self, item: dict) -> None:
        """
        인용 모드 결과도 RC37Model 스키마에 그대로 태워 검증.
        """
        RC37Model.model_validate(item)
