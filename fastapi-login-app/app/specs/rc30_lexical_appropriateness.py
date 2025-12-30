# app/specs/rc30_lexical_appropriateness.py
from __future__ import annotations
import re
from app.specs._base_mcq import BaseMCQSpec

# ===== 공통 유틸(기존) =====
_RE_U = re.compile(r"<u>.*?</u>", re.I | re.S)
_RE_CIRCLED = re.compile(r"[①②③④⑤]")

_NUMS = ["①","②","③","④","⑤"]
_U_RE = re.compile(r"<u>(.*?)</u>", re.I | re.S)

def _collapse_dup(word: str) -> str:
    # CraftingCrafting → Crafting, interestsinterests → interests
    return re.sub(r"\b([A-Za-z가-힣]+)\1\b", r"\1", word, flags=re.I)

# ===== 인용 전용 유틸 =====
def _underline_once(text: str, label: str, token: str) -> str:
    """
    token을 본문에 '최초 1회만' 밑줄로 감싼다.
    1차: 단어 경계 우선, 대소문자 무시
    2차: 공백/하이픈 느슨 매칭(그래도 실패하면 skip)
    """
    if not token:
        return text
    # 1) 단어 경계 기반 매칭
    pat = re.compile(rf"\b({re.escape(token)})\b", re.I)
    new = pat.sub(lambda m: f"<u>{label}{m.group(1)}</u>", text, count=1)
    if new != text:
        return new
    # 2) 느슨 매칭: 공백(여러 칸) 허용, 하이픈 등 최소 허용
    loose = re.compile(rf"({re.escape(token).replace(r'\ ', r'\s+')})", re.I)
    new2 = loose.sub(lambda m: f"<u>{label}{m.group(1)}</u>", text, count=1)
    return new2

def _insert_circled_underlines(passage: str, tokens: list[str]) -> str:
    out = passage
    for i, tok in enumerate((tokens or [])[:5]):
        out = _underline_once(out, _NUMS[i], (tok or "").strip())
    return out

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


class RC30Spec(BaseMCQSpec):
    """
    RC30 — Lexical Appropriateness (낱말의 쓰임)
    - 문맥상 부적절한 어휘/표현 1개를 찾는 유형.
    - 밑줄 <u>...</u>이 일반적이지만, 없어도 허용(번호형 선지 등).
    """
    id = "RC30"

    # ===== (기존) generate 경로용 설정 =====
    def system_prompt(self) -> str:
        return (
            "CSAT English RC30 — Lexical appropriateness.\n"
            "Task: Ask which underlined word in the PASSAGE is INAPPROPRIATE in context.\n"
            "- Underline tokens in the PASSAGE using <u>…</u>; DO NOT put the words in options.\n"
            "- OPTIONS MUST be only the labels: ①, ②, ③, ④, ⑤.\n"
            "- Ensure exactly ONE option is contextually inappropriate; the others must be acceptable.\n"
            "Output JSON only; no code fences."
        )

    def extra_checks(self, data: dict):
        """
        RC30 유효성 점검(과도한 제약 제거, 낱말 쓰임 중심으로 완화):
        - 질문이 '낱말/어휘/적절/부적절/word/lexical/collocation' 계열을 언급하거나,
        - 본문 또는 질문에 밑줄 <u>...</u>가 있거나,
        - 본문에 ①~⑤ 같은 번호 신호가 있을 때 OK.
        - (형식 신호가 전혀 없어도) 실제로 '한 개만 부적절'을 명시하면 허용.
        """
        q = (data.get("question") or "").strip()
        passage = (data.get("passage") or "").strip()
        options = data.get("options") or []
        ca = str(data.get("correct_answer") or "").strip()

        q_lower = q.lower()
        lexical_cues = (
            ("낱말" in q) or ("어휘" in q) or ("적절" in q) or ("부적절" in q) or
            ("inappropriate" in q_lower) or ("appropriate" in q_lower) or
            ("word choice" in q_lower) or ("lexical" in q_lower) or ("collocation" in q_lower)
        )
        has_u = bool(_RE_U.search(passage) or _RE_U.search(q))
        has_circled = bool(_RE_CIRCLED.search(passage) or _RE_CIRCLED.search(q))

        # 최소 형식/의미 조건 중 하나는 만족해야 함
        if not (lexical_cues or has_u or has_circled):
            raise ValueError(
                "RC30 expects lexical-appropriateness cues: "
                "include wording like '낱말/어휘/부적절', or use <u>…</u>, or numbered ①~⑤."
            )

        # 옵션 기본 체크(베이스 스펙이 이미 검증한다면 중복 최소화)
        if not isinstance(options, list) or len(options) < 4:
            raise ValueError("RC30 requires 4–5 options representing candidate words/phrases.")

        # 정답 표준화(베이스에서 처리하더라도 안전망)
        if ca not in {"1","2","3","4","5","①","②","③","④","⑤"}:
            raise ValueError("RC30 correct_answer must point to exactly one option (1–5 or ①–⑤).")
        
    def repair(self, data: dict, passage: str) -> dict:
        """
        (generate 경로) 모델이 본문에 <u>…</u>를 넣어줬을 때 ①~⑤ 라벨을 부여하고
        options/정답을 정규화한다. 인용(quote) 모드는 별도 훅에서 처리.
        """
        txt = data.get("passage") or passage or ""
        # 0) 본문 내 기존 ①~⑤ 제거
        txt = re.sub(r"[①②③④⑤]", "", txt)

        opts = data.get("options") or []
        ca = str(data.get("correct_answer") or "").strip()

        # 1) 본문 밑줄 토큰에 ①~⑤ 라벨 부착
        parts = []
        idx = 0
        def _repl(m):
            nonlocal idx, parts
            clean = re.sub(r"^[①②③④⑤]\s*", "", m.group(1)).strip()
            clean = _collapse_dup(clean)
            parts.append(clean)
            i = min(idx, 4)
            out = f"<u>{_NUMS[i]}{clean}</u>"
            idx += 1
            return out

        new_txt = _U_RE.sub(_repl, txt)

        # 2) 옵션/정답 정규화
        if len(parts) == 5:
            # 옵션은 ‘라벨만’
            data["options"] = _NUMS.copy()
            # 정답 표준화
            if ca in _NUMS:
                ca = str(_NUMS.index(ca) + 1)
            if ca not in {"1","2","3","4","5"}:
                ca = "1"
            data["correct_answer"] = ca

        data["passage"] = new_txt
        return data    

    # ===== (신규) quote 전용 훅들 =====
    def has_quote_support(self) -> bool:
        """
        인용(quote) 모드를 지원함을 알린다.
        generate 경로에는 영향 없음.
        """
        return True

    def quote_build_prompt(self, passage: str) -> str:
        """
        인용 모드 프롬프트: passage는 수정 금지(LLM 단계). 표식 삽입 금지.
        LLM은 형식을 위한 '메타'만 JSON으로 반환.
        이 버전은 '정확히 1개 토큰을 틀리게 바꿀 후보(wrong_replacement)'까지 지정하도록 강제.
        """
        return (
            "You are generating a CSAT-English RC30 (lexical appropriateness) item from the given PASSAGE.\n"
            "RULES:\n"
            "- DO NOT modify the passage text. DO NOT insert <u>…</u> or circled numbers into the passage.\n"
            "- Choose exactly five target tokens from the PASSAGE and return them in ORDER OF FIRST APPEARANCE.\n"
            "- Each token MUST be a contiguous substring that actually exists in the passage (case-insensitive ok).\n"
            "- Exactly ONE token must be made contextually INAPPROPRIATE by replacing it with a wrong form that is still grammatical but semantically/morally/pragmatically wrong in this context.\n"
            "- Provide which one to replace (wrong_index: \"1\"..\"5\") and the replacement string (wrong_replacement).\n"
            "- The explanation MUST be written in Korean, explaining why the replaced word is inappropriate; include the label and word like ②<u>wrong_replacement</u>.\n"
            'Return JSON only with keys: {"question","options","targets","wrong_index","wrong_replacement","correct_answer","explanation"}.\n'
            '- "options" MUST be ["①","②","③","④","⑤"].\n'
            '- "targets" MUST be ["t1","t2","t3","t4","t5"] in appearance order and MUST match substrings in the passage.\n'
            '- "wrong_index" MUST be "1"|"2"|"3"|"4"|"5"; "correct_answer" MUST equal "wrong_index".\n'
            "PASSAGE:\n" + passage
        )

    def quote_postprocess(self, passage: str, llm_json: dict) -> dict:
        """
        인용 모드 사후처리:
        - passage 원문에서 targets[wrong_index-1]을 wrong_replacement로 '한 번만' 교체
        - 교체된 표면형을 포함한 5개 토큰을 순서대로 <u>①…</u>~<u>⑤…</u> 삽입
        - options/정답 정규화
        """
        targets = (llm_json.get("targets") or [])[:5]
        wrong_idx_s = str(llm_json.get("wrong_index") or llm_json.get("correct_answer") or "").strip()
        repl = (llm_json.get("wrong_replacement") or "").strip()

        if len(targets) != 5:
            raise ValueError("RC30(quote): targets must have exactly 5 items")
        if wrong_idx_s not in {"1","2","3","4","5"}:
            raise ValueError("RC30(quote): wrong_index must be '1'..'5'")
        wrong_i = int(wrong_idx_s) - 1

        orig = (targets[wrong_i] or "").strip()
        if not orig or not repl or repl.lower() == orig.lower():
            raise ValueError("RC30(quote): invalid wrong_replacement or original token")

        # 1) 본문에서 '해당 토큰'을 '틀린 형태'로 한 번만 교체
        replaced_passage = _replace_once(passage, orig, repl)

        # 2) 교체된 표면형을 반영하여 밑줄 삽입용 토큰 시퀀스 구성
        tokens_for_mark = list(targets)
        tokens_for_mark[wrong_i] = repl

        # 3) ①~⑤ + 밑줄 삽입
        marked = _insert_circled_underlines(replaced_passage, tokens_for_mark)

        # 4) 결과 구성(정답은 wrong_index)
        item = {
            "passage": marked,
            "question": "다음 글의 밑줄 친 부분 중, 문맥상 낱말의 쓰임이 적절하지 <u>않은</u> 것은? [3점]",
            "options": _NUMS.copy(),
            "correct_answer": wrong_idx_s,
            "explanation": llm_json.get("explanation") or "",
        }
        return item

    def quote_validate(self, item: dict) -> None:
        """
        인용 모드 얇은 검증:
        - options == ["①","②","③","④","⑤"]
        - correct_answer ∈ {"1","2","3","4","5"}
        - passage 안에 <u>① ...</u> ~ <u>⑤ ...</u>가 각 1회 존재
        - '틀린 토큰' 교체가 실제 반영되었는지(원문 토큰 ≠ 교체 후 토큰) 점검은 사후처리 단계에서 보장하므로,
          여기서는 최소 등장 확인만 수행
        """
        import re as _re
        assert item.get("options") == _NUMS, "RC30(quote): options must be ['①','②','③','④','⑤']"
        assert str(item.get("correct_answer")) in {"1","2","3","4","5"}, "RC30(quote): correct_answer must be 1~5"

        p = item.get("passage") or ""
        counts = [len(_re.findall(fr"<u>{n}", p)) for n in _NUMS]
        if not all(c == 1 for c in counts):
            raise AssertionError(f"RC30(quote): passage must contain each underline once, got {counts}")
