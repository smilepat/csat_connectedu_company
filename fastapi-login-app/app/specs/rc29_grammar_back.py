# app/specs/rc29_grammar.py
from __future__ import annotations
import re
from pydantic import BaseModel, Field, field_validator

from app.specs.base import ItemSpec, GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like
from app.specs.passage_preprocessor import sanitize_user_passage

# ---------- repair용 정규식 ----------
# ① 뒤에 <u>…</u>가 없을 때 1~3토큰을 감싸기
RE_LABEL_WRAP   = re.compile(r"([①②③④⑤])(?:\s|&nbsp;)*(?!<u>)([^\s)»”\"',.;:()]+(?:\s+[^\s)»”\"',.;:()]+){0,2})")
# <u>…</u> 다음에 숫자가 뒤에 붙은 잘못된 케이스: <u>X</u> ① → ①<u>X</u>
RE_UL_THEN_NUM  = re.compile(r"<u>(.*?)</u>\s*([①②③④⑤])", re.I | re.S)
# 정규화에 사용할 패턴들
RE_ANY_UL       = re.compile(r"<u>(.*?)</u>", re.I | re.S)
RE_LABELED_UL   = re.compile(r"([①②③④⑤])(?:\s|&nbsp;)*<u>(.*?)</u>", re.I | re.S)
TOKEN_SPLIT_RE  = re.compile(r"\s+")
NUMS            = ["①","②","③","④","⑤"]
UNDERLINE_RE    = re.compile(r"([①②③④⑤])(?:\s|&nbsp;)*<u>(.*?)</u>")

def _norm_span(txt: str) -> str:
    # 쉼표/세미콜론/콜론 제거 + 1~3토큰 제한
    txt = re.sub(r"[,:;]", "", (txt or "")).strip()
    toks = [t for t in TOKEN_SPLIT_RE.split(txt) if t][:3]
    return " ".join(toks) if toks else txt


# ===== 인용 전용 유틸 (RC30 패턴 차용) =====
_RE_U = re.compile(r"<u>.*?</u>", re.I | re.S)
_RE_CIRCLED = re.compile(r"[①②③④⑤]")
_U_RE = re.compile(r"<u>(.*?)</u>", re.I | re.S)
_NUMS = ["①", "②", "③", "④", "⑤"]

def _collapse_dup(word: str) -> str:
    # CraftingCrafting → Crafting, interestsinterests → interests
    return re.sub(r"\b([A-Za-z가-힣]+)\1\b", r"\1", word, flags=re.I)

def _underline_once(text: str, label: str, token: str) -> str:
    """
    token을 본문에 '최초 1회만' 밑줄로 감싼다.
    1차: 단어 경계 우선, 대소문자 무시
    2차: 공백/하이픈 느슨 매칭(그래도 실패하면 skip)

    인용 모드에서는 <u>안쪽에 ①~⑤ 라벨을 포함하는 형태로 삽입:
    <u>①have grown</u>
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


# ---------- 모델 ----------
class RC29Model(BaseModel):
    """
    RC29: 어법 판단 — 5지선다 MCQ
    correct_answer는 정수(1~5)로 강제
    """
    question: str
    passage: str
    options: list[str] = Field(min_length=5, max_length=5)
    correct_answer: int
    explanation: str

    model_config = {"extra": "allow"}  # 여분 필드 허용(rationale, _warnings 등)

    @field_validator("question", "passage", "explanation", mode="before")
    @classmethod
    def _strip(cls, v):
        return (v or "").strip()

    @field_validator("options", mode="before")
    @classmethod
    def _strip_options(cls, v):
        return [str(o).strip() for o in (v or [])]

    @field_validator("correct_answer", mode="before")
    @classmethod
    def _coerce_ca(cls, v):
        m = {"①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5}
        if isinstance(v, str):
            s = v.strip()
            if s in m: return m[s]
            if s.isdigit(): return int(s)
        if isinstance(v, (int, float)):
            return int(v)
        return v


# ---------- 스펙 ----------
CUSTOM_MODES = {"custom_rc29", "edit_one", "custom_grammar"}

class RC29Spec(ItemSpec):
    """
    맞춤 어법(일반 passage 입력 → ①~⑤ 삽입, 정확히 1곳만 오류)과
    그냥 생성(모델이 passage도 함께 생성 가능) 둘을 같은 Spec에서 분기 처리.
    - 맞춤 어법: 기존 표식 제거(strip_circled=True, strip_underlines=True) 후,
      RC29_EDIT_ONE_FROM_CLEAN 프롬프트 사용.
    - 그냥 생성: 동일 전처리 후 기본 RC29 프롬프트 사용.
    - repair(): ①–⑤ × <u>…</u> 보정(이미 완전 5쌍이면 건드리지 않음).

    ✅ 인용(quote) 모드 지원: RC30과 동일 패턴의 quote 훅 제공.
    """
    id = "RC29"

    def system_prompt(self) -> str:
        # 기본 system_prompt (JSON 강제 등). build_prompt()에서 실제 프롬프트 키를 분기합니다.
        return (
            "CSAT English RC29 (Grammar Judgment). "
            "Return ONLY JSON matching the schema. "
            "Embed five labeled targets ①–⑤ as <u>...</u>. "
            "Each underline MUST be a single word or a very short unit (2–3 words). "
            "Exactly ONE target is ungrammatical; four are correct. "
            "The stem must be exactly '다음 글의 밑줄 친 부분 중, 어법상 <u>틀린</u> 것은?'. "
            "Options must be ['①','②','③','④','⑤']. "
            "The 'correct_answer' MUST be an INTEGER 1–5. "
            "Use ONLY the provided passage. Do NOT rewrite, paraphrase, shorten, extend, split, merge, or reorder any part."
        )

    def build_prompt(self, ctx: GenContext) -> str:
        # --- optional debug switch ---
        DEBUG = False
        if DEBUG:
            print("[RC29.build_prompt] ctx keys:", list(ctx.keys()))
            print("[RC29.build_prompt] ctx.mode:", ctx.get("mode"))
            print("[RC29.build_prompt] ctx.item_id:", ctx.get("item_id"))
            print("[RC29.build_prompt] raw passage repr:", repr(ctx.get("passage")))

        raw_passage = (ctx.get("passage") or "")
        has_passage = bool(raw_passage.strip())

        # 맞춤/그냥 분기 기준: passage 유무 + mode=='custom_passage'
        is_custom = has_passage or (ctx.get("mode") == "custom_passage")
        if DEBUG:
            print("[RC29.build_prompt] has_passage:", has_passage, "/ is_custom:", is_custom)

        if not is_custom:
            # 그냥 생성: passage 없음 → 프롬프트가 본문까지 새로 작성
            return PromptManager.generate(
                item_type=self.id,  # "RC29"
                difficulty=(ctx.get("difficulty") or "medium"),
                topic_code=(ctx.get("topic") or "random"),
                passage="",  # 빈 값 유지 (전처리 불필요)
            )

        # 맞춤 생성: 사용자 본문을 정리한 뒤, 전용 프롬프트 사용
        cleaned = sanitize_user_passage(
            raw_passage,
            strip_circled=True,       # 기존 ①~⑤ 제거
            strip_underlines=True     # 기존 <u>…</u> 제거
        )
        if DEBUG:
            print("[RC29.build_prompt] cleaned passage len:", len(cleaned))

        return PromptManager.generate(
            item_type="RC29_EDIT_ONE_FROM_CLEAN",  # 맞춤 전용 프롬프트
            difficulty=(ctx.get("difficulty") or "medium"),
            topic_code=(ctx.get("topic") or "random"),
            passage=cleaned,
        )

    # ---------- 품질 보정/검증 ----------
    def normalize(self, data: dict) -> dict:
        return coerce_mcq_like(data)

    def validate(self, data: dict):
        """
        느슨화된 검증:
        - 필수 키/질문 문구/옵션 고정
        - 정답: int(1~5) 변환
        - 밑줄은 3~6개까지 허용 (부족/과다분은 repair에서 최대한 보완)
        - 각 밑줄 토큰 수는 1~4 허용(위반 시 경고 수준)
        - 설명 길이 ≥ 5
        """
        d = self.normalize(data)
        model = RC29Model(**d)

        # 1) 질문 문구/옵션 고정 (단, 질문은 '틀린' 포함만 확인)
        if "틀린" not in model.question:
            raise ValueError("Stem must mention '<u>틀린</u>'.")

        if model.options != ["①", "②", "③", "④", "⑤"]:
            raise ValueError("Options must be exactly ['①','②','③','④','⑤'].")

        # 2) 밑줄 개수 느슨화 (3~6개)
        marks = list(UNDERLINE_RE.finditer(model.passage))
        if not (3 <= len(marks) <= 6):
            raise ValueError(f"Found {len(marks)} underlined targets, expected 3–6.")

        # 3) 각 밑줄 토큰 수 느슨화 (1~4 허용, 위반은 경고)
        for m in marks:
            span_text = (m.group(2) or "").strip()
            tokens = [t for t in TOKEN_SPLIT_RE.split(span_text) if t]
            if not (1 <= len(tokens) <= 4):
                # 엄격 차단 대신 런타임 경고(로그)
                print(f"[RC29 validate] Warning: '{span_text}' has {len(tokens)} tokens.")

        # 4) 설명 최소 길이 완화
        if len(model.explanation) < 5:
            raise ValueError("Explanation too short (<5 chars).")

    def json_schema(self) -> dict:
        return RC29Model.model_json_schema()

    def repair_budget(self) -> dict:
        return {"fixer": 1, "regen": 1, "timeout_s": 15}

    # ---------- 자동 보정(형식 강제): ①–⑤ × <u>…</u> 1:1 보장 ----------
    def repair(self, raw: dict, _passage_ctx: str) -> dict:
        """
        공통 실패 패턴을 자동 보정:
        1) <u>X</u> ①  →  ①<u>X</u> 로 재배치
        2) ① 뒤에 <u>…</u>가 없으면 1~3토큰을 감싸기
        3) 레이블 중복/누락 정리: 각 레이블(①~⑤)은 정확히 한 번만 등장
        4) 밑줄 내부는 쉼표/세미콜론/콜론 제거 → 1~3토큰으로 정규화
        5) 라벨 없는 <u>…</u>에는 누락 라벨을 앞에서부터 부여(최대 5개까지)
        """
        if not isinstance(raw, dict):
            return raw
        data = dict(raw)
        p = data.get("passage")
        if not isinstance(p, str) or not p.strip():
            return data

        # ✅ 이미 ①–⑤ × <u>…</u> 5쌍이 정확히 존재하면 건드리지 않음(의도 보존)
        labeled = list(RE_LABELED_UL.finditer(p))
        if len(labeled) == 5 and len({m.group(1) for m in labeled}) == 5:
            return data

        s = p

        # (1) 잘못된 순서: <u>X</u> ①  →  ①<u>X</u>
        s = RE_UL_THEN_NUM.sub(lambda m: f"{m.group(2)}<u>{_norm_span(m.group(1))}</u>", s)

        # (2) ① 뒤에 <u>…</u>가 없으면 1~3토큰을 감싸기
        def _wrap_after_label(m: re.Match) -> str:
            label = m.group(1)
            phrase = _norm_span(m.group(2) or "")
            return f"{label}<u>{phrase}</u>" if phrase else label
        s = RE_LABEL_WRAP.sub(_wrap_after_label, s)

        # (3) 라벨-밑줄 쌍 스캔: 중복 라벨 첫등장만 유지
        out_parts, pos, seen = [], 0, set()
        for m in RE_LABELED_UL.finditer(s):
            start, end = m.span()
            label, span = m.group(1), _norm_span(m.group(2))
            out_parts.append(s[pos:start])
            if label in seen:
                out_parts.append(f"<u>{span}</u>")
            else:
                out_parts.append(f"{label}<u>{span}</u>")
                seen.add(label)
            pos = end
        out_parts.append(s[pos:])
        s = "".join(out_parts)

        # (4) 라벨 없는 <u>…</u>에 누락 라벨 부여하여 5개 채우기
        labeled_now = list(RE_LABELED_UL.finditer(s))
        labels_present = [m.group(1) for m in labeled_now]
        missing = [n for n in NUMS if n not in labels_present]
        if missing:
            new_s, pos = [], 0
            for m in RE_ANY_UL.finditer(s):
                start, end = m.span()
                new_s.append(s[pos:start])
                content = _norm_span(m.group(1) or "")
                prefix = s[max(0, start-6):start]
                has_label_prefix = bool(re.search(r"[①②③④⑤](?:\s|&nbsp;)*$", prefix))
                if (not has_label_prefix) and missing and len(labels_present) < 5:
                    lab = missing.pop(0)
                    labels_present.append(lab)
                    new_s.append(f"{lab}<u>{content}</u>")
                else:
                    new_s.append(f"<u>{content}</u>")
                pos = end
            new_s.append(s[pos:])
            s = "".join(new_s)

        # (5) 안전 정규화: 라벨-밑줄 쌍 내부 span 1~3토큰으로 제한
        def _re_norm(m: re.Match) -> str:
            return f"{m.group(1)}<u>{_norm_span(m.group(2))}</u>"
        s = RE_LABELED_UL.sub(_re_norm, s)

        data["passage"] = s
        return data

    # =========================
    # 인용(quote) 전용 훅 (RC30 패턴)
    # =========================
    def has_quote_support(self) -> bool:
        """
        인용(quote) 모드를 지원함을 알린다.
        generate 경로에는 영향 없음.
        """
        return True

    def quote_build_prompt(self, passage: str) -> str:
        """
        인용 모드 프롬프트:
        - passage를 직접 수정하지 말고 메타 JSON만 생성.
        - 5개의 문법 포인트를 고르고,
          그 중 1개를 어법 오류로 만들 계획만 세운다.
        """
        return (
            "Create a CSAT Reading Item 29 (Grammar Judgment) from the given passage.\n\n"
            "## HARD CONSTRAINTS ON GRAMMAR POINTS\n"
            "- ABSOLUTE RULE: Every 'targets[i].text' MUST be copied EXACTLY from the passage.\n"
            "- You MUST NOT invent, paraphrase, conjugate, or otherwise change any word or phrase that does NOT already appear in the passage.\n"
            "- If a required grammar category does not appear in the passage, DO NOT invent a fake example. Instead, skip that category and choose another REAL grammar point from the passage.\n"
            "- Use the passage AS-IS for content: do NOT paraphrase, reorder, summarize, or expand sentences.\n"
            "- You must choose EXACTLY FIVE short targets (1–3 tokens each) from the passage, in order of first appearance.\n"
            "- Each target must be a single word or a very short unit (max 2–3 words, e.g., 'to be', 'have been').\n"
            "- NEVER select a full clause or a long phrase as a target.\n"
            "- The five targets must use grammar categories from the following set:\n"
            "    {'relative','tense_or_agreement','modal','passive','participle'}.\n"
            "- Among the five targets, you MUST use AT LEAST THREE DISTINCT grammar categories from this set.\n"
            "- It is allowed that some categories repeat or are not used at all, but you must NEVER invent a target that is not literally present in the passage.\n"
            "- Do NOT use articles, simple prepositions, or punctuation as grammar targets.\n\n"
            "## GRAMMAR ERROR REQUIREMENT\n"
            "- Make EXACTLY ONE of the five targets ungrammatical by proposing a wrong replacement that violates a clear grammar rule\n"
            "  (e.g., wrong relative pronoun, wrong tense or agreement, incorrect modal form, broken passive, wrong participle form).\n"
            "- The other four targets must remain fully grammatical and natural (keep them as-is in the passage).\n"
            "- Stylistic awkwardness, redundancy, or meaning-only shifts are NOT allowed as errors.\n\n"
            "## RETURN FORMAT (JSON ONLY)\n"
            "{\n"
            '  "question": "다음 글의 밑줄 친 부분 중, 어법상 <u>틀린</u> 것은?",\n'
            '  "options": ["①","②","③","④","⑤"],\n'
            '  "targets": [\n'
            '    {"text": "... (substring from passage)", "category": "relative | tense_or_agreement | modal | passive | participle"},\n'
            '    {"text": "... (substring from passage)", "category": "..."},\n'
            '    {"text": "... (substring from passage)", "category": "..."},\n'
            '    {"text": "... (substring from passage)", "category": "..."},\n'
            '    {"text": "... (substring from passage)", "category": "..." }\n'
            "  ],\n"
            "- Do NOT copy the example values like \"which\" or \"is purchased\". "
            "Replace them with real substrings from the passage.\n"            
            '  "wrong_index": "1" | "2" | "3" | "4" | "5",\n'
            '  "wrong_replacement": "... (replacement making the chosen target ungrammatical)",\n'
            '  "correct_answer": "1" | "2" | "3" | "4" | "5",\n'
            '  "explanation": "[한국어로: 선택된 문법 범주, 틀린 형태 vs 올바른 형태, 왜 틀렸는지 설명]"\n'
            "}\n"
            "- IMPORTANT: Do NOT modify the passage or insert any <u>…</u> yourself. Only return the JSON metadata.\n"
            "- After you choose the five targets, DOUBLE-CHECK that each 'targets[i].text' is an exact, contiguous substring that appears in the PASSAGE (case-insensitive ok).\n"
            "- If any target text is not found in the passage, you MUST fix it before returning the JSON.\n"
            "- All five 'category' values MUST be in the set {'relative','tense_or_agreement','modal','passive','participle'}.\n"
            "- Among these, you MUST use at least three distinct categories overall.\n"
            "- 'correct_answer' MUST equal 'wrong_index'.\n\n"
            "PASSAGE:\n" + (passage or "")
        )


    def quote_postprocess(self, passage: str, llm_json: dict) -> dict:
        """
        인용 모드 사후처리:
        - passage 원문에서 targets[wrong_index-1]을 wrong_replacement로 '한 번만' 치환
        - 교체된 표면형을 포함한 5개 토큰을 순서대로 ①~⑤ + <u>…</u> 삽입
        - options/정답 정규화
        - targets 는 두 가지 포맷을 모두 허용:
          · 구형: ["t1","t2","t3","t4","t5"]
          · 신형: [{"text": "...", "category": "..."}, ...]
        """
        raw_targets = (llm_json.get("targets") or [])[:5]

        # ---- 1) targets 파싱 (신형 + 구형 모두 지원) ----
        texts: list[str] = []
        categories: list[str] = []

        if raw_targets and isinstance(raw_targets[0], dict):
            # 새 포맷: {"text": "...", "category": "..."}
            for obj in raw_targets:
                txt = (obj.get("text") or "").strip()
                cat = (obj.get("category") or "").strip()
                if txt:
                    texts.append(txt)
                categories.append(cat)
        else:
            # 구형 포맷: ["...", "...", ...]
            texts = [str(t or "").strip() for t in raw_targets]

        if len(texts) != 5:
            raise ValueError("RC29(quote): targets must have exactly 5 items")

        # ✅ (A) 타겟 텍스트가 실제 passage 안에 존재하는지 사전 검증
        missing: list[str] = []
        for t in texts:
            if not t:
                missing.append(t)
                continue
            # 단어 경계 기준, 대소문자 무시
            pat = re.compile(rf"\b{re.escape(t)}\b", re.I)
            if not pat.search(passage):
                missing.append(t)

        if missing:
            # 이 에러는 상위 레벨에서 "LLM 출력 불량 → 재생성 필요"로 처리하는 게 좋다.
            raise ValueError(
                f"RC29(quote): some targets not found in passage: {missing}"
            )

        # 카테고리 검사 (신형 포맷일 때만 강제)
        allowed_cats = {"relative", "tense_or_agreement", "modal", "passive", "participle"}
        if categories:
            # 허용된 카테고리만 필터링 (빈 문자열/이상값 감지용)
            valid_cats = [c for c in categories if c in allowed_cats]
            if len(valid_cats) != 5:
                raise ValueError(
                    "RC29(quote): each target must have a valid grammar category "
                    f"from {allowed_cats}, got {categories}"
                )
            # 서로 다른 범주가 최소 3개 이상이어야 함
            if len(set(valid_cats)) < 3:
                raise ValueError(
                    "RC29(quote): must use at least 3 distinct grammar categories "
                    f"from {allowed_cats}, got {valid_cats}"
                )

        wrong_idx_s = str(
            llm_json.get("wrong_index") or llm_json.get("correct_answer") or ""
        ).strip()
        repl = (llm_json.get("wrong_replacement") or "").strip()

        if wrong_idx_s not in {"1", "2", "3", "4", "5"}:
            raise ValueError("RC29(quote): wrong_index must be '1'..'5'")
        wrong_i = int(wrong_idx_s) - 1

        orig = (texts[wrong_i] or "").strip()
        if not orig or not repl or repl.lower() == orig.lower():
            raise ValueError("RC29(quote): invalid wrong_replacement or original token")

        # 1) 본문에서 '해당 토큰'을 '틀린 형태'로 한 번만 교체 (문법 오류 유발)
        replaced_passage = _replace_once(passage, orig, repl)

        # 2) 교체된 표면형을 반영하여 밑줄 삽입용 토큰 시퀀스 구성
        tokens_for_mark = list(texts)
        tokens_for_mark[wrong_i] = repl

        # 3) ①~⑤ + 밑줄 삽입
        marked = _insert_circled_underlines(replaced_passage, tokens_for_mark)

        # ✅ (B) 실제로 밑줄이 5개 들어갔는지 즉시 확인
        UL_SPAN_RE = re.compile(r"<u>\s*([①②③④⑤])([^<]*?)</u>")
        marks = list(UL_SPAN_RE.finditer(marked))
        if len(marks) != 5:
            raise ValueError(
                f"RC29(quote): failed to insert 5 underlines, got {len(marks)}; "
                f"targets={texts}"
            )

        # 4) 결과 구성(정답은 wrong_index)
        item = {
            "passage": marked,
            "question": "다음 글의 밑줄 친 부분 중, 어법상 <u>틀린</u> 것은?",
            "options": _NUMS.copy(),
            "correct_answer": int(wrong_idx_s),
            "explanation": llm_json.get("explanation") or "",
        }
        return item


    def quote_validate(self, item: dict) -> None:
        """
        인용 모드 얇은 검증:
        - options == ["①","②","③","④","⑤"]
        - correct_answer ∈ {1,2,3,4,5}
        - passage 안에 <u>...</u> 스팬이 5개 있고, 그 안에 ①~⑤가 각각 1번씩 등장
        - 각 밑줄 토큰은 1~3 단어
        """
        import re as _re

        # 0) 옵션 & 정답 형태
        assert item.get("options") == _NUMS, \
            "RC29(quote): options must be ['①','②','③','④','⑤']"

        ca = item.get("correct_answer")
        try:
            ca_int = int(ca)
        except Exception:
            raise AssertionError("RC29(quote): correct_answer must be an integer 1~5")
        assert ca_int in {1, 2, 3, 4, 5}, \
            "RC29(quote): correct_answer must be 1~5"

        p = item.get("passage") or ""

        # 1) <u>...</u> 스팬 안에서 라벨+내용을 파싱
        #    라벨은 <u> 안쪽 첫 글자(①~⑤), 그 뒤가 실제 토큰 부분
        UL_SPAN_RE = _re.compile(r"<u>\s*([①②③④⑤])([^<]*?)</u>")
        marks = list(UL_SPAN_RE.finditer(p))
        if len(marks) != 5:
            raise AssertionError(
                f"RC29(quote): expected 5 underlined spans, got {len(marks)}"
            )

        # 라벨별 등장 횟수 체크 (①~⑤ 각각 1번씩)
        labels = [m.group(1) for m in marks]
        counts = [labels.count(n) for n in _NUMS]
        if not all(c == 1 for c in counts):
            raise AssertionError(
                f"RC29(quote): each label ①~⑤ must appear once in underlines, got {counts}"
            )

        # 2) 각 밑줄 내용(라벨 제외)이 1~3 단어인지 확인
        for m in marks:
            span_text = (m.group(2) or "").strip()
            tokens = [t for t in span_text.split() if t]
            if not (1 <= len(tokens) <= 3):
                raise AssertionError(
                    f"RC29(quote): underline span '{span_text}' has "
                    f"{len(tokens)} tokens; require 1–3."
                )
