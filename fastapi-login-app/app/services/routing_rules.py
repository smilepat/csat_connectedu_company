from __future__ import annotations
import os
import re
from typing import List, Dict
from app.specs.passage_preprocessor import sanitize_user_passage
from app.services.llm_client import call_llm_json  # (유지)

"""
Rule-based candidate suggester (format + content hybrid).
- Returns up to 12 candidates sorted by fit(desc).
- Adds RC30 even WITHOUT underline markers if lexical/nuance signals exist,
  or when circled numerals are followed by short lexical candidates.
- 2025-09 업데이트:
  · RC18~RC41 "최종 통합표" 반영: 길이/담화/포맷 신호 기반 보정 레이어 추가
  · 길이 구간(짧음/중간/김) + 표면 신호(번호/라벨/공지/서신) + 내용 신호(정서/권고/비유/도표/전기 등)
    → 유형별 fit을 안전하게 가산 보정

- 2025-09 길이 우선(Gating) 적용 (세분화 규칙):
  · ≤150 → RC33까지 허용
  · 151–199 → RC40까지 허용
  · ≥200 → RC41 이상(세트형) 포함 허용
  ※ 길이 조건을 만족하지 않는 유형은 어떤 경우에도 추천에 포함되지 않도록 add/주입/보정 단계 전체에 게이트 적용.
"""

# ---------- Base regex signals (format-like) ----------
RE_UNDERLINE        = re.compile(r"<u>.*?</u>", re.I | re.S)
RE_NUM_BULLETS      = re.compile(r"[①②③④⑤]")
RE_INSERT_PARENS    = re.compile(r"\(\s*[①②③④⑤]\s*\)")
RE_PARAGRAPH_LABELS = re.compile(r"\([A-C]\)")
RE_LOWER_PARENS     = re.compile(r"\([a-e]\)")  # (a)(b)(c) 라벨 감지
RE_NOTICE_KEYS      = re.compile(
    r"\b("
    r"Title|Date|Location|Eligibility|Registration|Fee|Contact|Note|Time|Venue|"
    r"Deadline|Participants?|Age requirement|Restrictions?|Details?|Awards?|"
    r"Evaluation Criteria|Activities?|Duration|Period|Schedule|Return|Use|"
    r"Service Range|Purchase Information|Tour Times?|Renovation Period|"
    r"Areas to be Closed|Card Type|Additional Information|Caution"
    r")\s*:",
    re.I,
)
RE_RC33_PIVOT = re.compile(
    r"\b(it follows that|in turn|therefore|thus|consequently|as a result)\b",
    re.I,
)

RE_RC39_META = re.compile(
    r"\b(analogy|argument|reasoning|logic|this is why|the reason is|what's worse|in reality|in fact|not .* but|the essence of|fails to|undermine[s]?)\b",
    re.I,
)

RE_RC39_CONTRAST = re.compile(
    r"\b(by contrast|in contrast|however|but |yet |still,|nevertheless|nonetheless|on the other hand)\b",
    re.I,
)

# NEW: 안내문 전용 보조 신호
RE_BULLET_DOT       = re.compile(r"[∙•]|^\s*[-*]\s", re.M)
RE_PRICE_SIGN       = re.compile(r"[$￡€]\s*\d", re.I)

RE_TABLEY           = re.compile(r"\b(table|figure|chart|graph)\b", re.I)
RE_CHARTY           = re.compile(r"\b(percent|percentage|survey|dataset|index|rank(ed)?|ratio|per capita|growth rate|decline|increase)\b", re.I)
RE_BIO = re.compile(
    r"\b("
    r"born\b|born in|was born in|"      # 출생
    r"died in|passed away|"             # 사망
    r"awarded|won the|"                 # 상·수상
    r"career|early life|later years|retired|"  # 경력/생애
    r"biograph|Nobel|prize"             # 전기/노벨 등
    r")\b",
    re.I,
)
RE_ARGUMENT         = re.compile(
    r"\b("
    r"should|must|ought to|need to|have to|has to|"
    r"it is necessary to|"
    r"it is (?:important|essential|crucial|critical) to|"
    r"it is desirable that|"
    r"it would be better to|"
    r"we (?:have|need to)"
    r")\b",
    re.I,
)
RE_EMOTION          = re.compile(r"\b(feel|felt|anxious|relieved|disappointed|excited|upset|proud|afraid|confident|confidence)\b", re.I)

# 실험·연구·데이터 기반 묘사 (RC37 쪽으로 강하게 보내고 싶은 패턴)
RE_RC_EXP_LIKE = re.compile(
    r"\b("
    r"experiment|experimental|research|study|studies|"
    r"data|dataset|measurements?|subjects?|participants?|"
    r"they found that|we found that|results? (?:show|suggest|indicate)|"
    r"observed that|observations? of|"
    r"patterns? of|scanning"
    r")\b",
    re.I,
)

# ▶ RC37: 진짜 '실험 보고형' 신호 (강한 RC37 힌트)
RE_RC37_STRONG_EXP = re.compile(
    r"\b("
    r"experiment|experimental|"
    r"randomi[sz]ed|control group|treatment group|placebo|"
    r"subjects?|participants?|"
    r"in one study|in a study|in an experiment"
    r")\b",
    re.I,
)

# ▶ RC37: 논증/이론/모형/균형 등 '단계적 논증' 메타 단어
RE_RC37_REASONING_META = re.compile(
    r"\b("
    r"assume|assumption|principle|theory|model|"
    r"equilibrium|equilibria|outcome|outcomes|scenario|"
    r"case in which|cases? where"
    r")\b",
    re.I,
)

# ▶ RC37: 인과 연쇄를 나타내는 접속사 (따라서, 그 결과, 그러므로…)
RE_RC37_CAUSAL_CHAIN = re.compile(
    r"\b("
    r"therefore|thus|consequently|as a result|hence|in turn"
    r")\b",
    re.I,
)

# ▶ RC36: 정의/용어 소개 신호
RE_RC36_DEF_CUE = re.compile(
    r"\b(is|are|was|were)\s+(called|known as|defined as)\b"
    r"|\b(refers to|means that)\b",
    re.I,
)

# ▶ RC36: 예시/비교 전개 신호 (기존)
RE_RC36_EXAMPLE_CUE = re.compile(
    r"\b("
    r"for example|for instance|similarly|in particular|"
    r"in this sense|in practice|in the real world"
    r")\b",
    re.I,
)

# RC19용 감정 polarity 세트 + 전환 시그널
POS_EMO = {
    "relieved", "confident", "confidence", "excited", "proud",
    "joy", "joyful", "happy", "glad", "satisfied", "at peace"
}
NEG_EMO = {
    "anxious", "uneasy", "upset", "afraid", "nervous",
    "disappointed", "frustrated", "shaking", "troubled", "worried"
}
RE_TURNING = re.compile(
    r"\b(However|But|Then|Finally|At last|After (he|she|I)|After hearing)\b",
    re.I,
)

RE_IDIOM_SHELLS = [
    re.compile(r"\bthe\s+[a-z]+?\s+in\s+the\s+room\b", re.I),
    re.compile(r"\b[a-z]+-?ed\s+sword\b", re.I),
    re.compile(r"\bball\s+is\s+in\s+(?:my|your|his|her|their|our)\s+court\b", re.I),
    re.compile(r"\bon\s+thin\s+ice\b", re.I),
    re.compile(r"\bglass\s+ceiling\b", re.I),
    re.compile(r"\bslippery\s+slope\b", re.I),
]
RE_SIMILE = re.compile(r"\b(?:like|as)\s+(?:a|an|the)?\s*[A-Za-z][A-Za-z\-']{3,}", re.I)

METAPHOR_CUES = {
    "iceberg", "elephant", "sword", "ceiling", "slope", "anchor",
    "compass", "pillar", "bridge", "lens", "canvas", "blind trust"
}

# ---------- RC29/RC30: extra semantic/lexical signals (content-based) ----------
RE_CIRCLED          = re.compile(r"[①②③④⑤]")
RE_INLINE_LEX       = re.compile(r"[①②③④⑤]\s*[A-Za-z가-힣\-]+(?:\s+[A-Za-z가-힣\-]+){0,2}")

RE_LEXICAL_META     = re.compile(
    r"\b(word\s*choice|lexical|collocation|nuance|synonym|antonym|appropriate|inappropriate)\b",
    re.I
)
RE_CONTRAST_EVAL    = re.compile(
    r"\b(irrelevant|inaccurate|misleading|awkward|odd|inapt|ill[-\s]?fitted|ill[-\s]?chosen|off)\b.*?\b"
    r"(relevant|accurate|apt|fitting|well[-\s]?chosen|on[-\s]?point|natural)\b|"
    r"\b(relevant|accurate|apt|fitting|well[-\s]?chosen|on[-\s]?point|natural)\b.*?\b"
    r"(irrelevant|inaccurate|misleading|awkward|odd|inapt|ill[-\s]?fitted|ill[-\s]?chosen|off)\b",
    re.I | re.S
)
RE_DERIV            = re.compile(r"\b\w+(?:ness|tion|sion|ity|able|ible|ive|al|ly|ment|ize|ise|ous)\b", re.I)

RE_GRAMMAR_META     = re.compile(
    r"\b(tense|agreement|subject[-\s]?verb|preposition|article|pronoun|parallelism|comparative|superlative|"
    r"modifier|participle|gerund|infinitive|voice|case|concord)\b",
    re.I
)

# ---------- Set-type signals (RC41–RC42) ----------
RE_ROMAN_PARENS     = re.compile(r"\(\s*(?:i|ii|iii|iv|v)\s*\)", re.I)  # (i)(ii)(iii)...
RE_PART_HEADING     = re.compile(r"\bPart\s*(?:I|II|III|1|2|3)\b", re.I)
RE_SECTION_HEAD     = re.compile(r"\bSection\s*[A-C1-3]\b", re.I)
RE_Q_RANGE          = re.compile(r"\bQuestions?\s*(?:\d+\s*[-–]\s*\d+|\d+\s*(?:and|&)\s*\d+)\b", re.I)
RE_FORMER_LATTER    = re.compile(r"\b(the\s+former|the\s+latter|respectively)\b", re.I)
RE_REF_PASSAGE      = re.compile(r"\b(in|from)\s+(?:passage|paragraph|text)\s*\(?[a-e]\)?\b", re.I)

# ---------- Extra signals for RC18/27/28 ----------
RE_LETTER_DEAR      = re.compile(r"\b(Dear\s+[A-Z][a-zA-Z]+|To whom it may concern|Dear\s+Friends)\b")
RE_LETTER_CLOSE     = re.compile(r"\b(Sincerely|Regards|Best regards|Yours truly|Many blessings)\b")
RE_WEBSITE_URL      = re.compile(r"https?://|www\.", re.I)

# NEW: RC18 intent / purpose signals
RE_INTENT_REQUEST = re.compile(
    r"\b(I would like to (?:ask|request)|Please let me know|I ask you to|"
    r"I want immediate action)\b",
    re.I,
)

RE_INTENT_INQUIRY = re.compile(
    r"\b(I am writing to inquire|I would like to know|I want to know|"
    r"could not find (?:any )?information)\b",
    re.I,
)

RE_INTENT_GUIDE = re.compile(
    r"\b(This is how you participate|Here is how you participate|"
    r"You can bring your items for donation|You can bring your items)\b",
    re.I,
)

# ★ 광고/안내형 의도 표현 (웹툰 예시 대응)
RE_INTENT_PROMO = re.compile(
    r"\bIf you'?re interested in\b|\bThis post is for you\b|\bIt'?s time to\b",
    re.I,
)
RE_RC38_PIVOT = re.compile(
    r"\b("
    r"yes,|however,|but |in fact,|indeed,|"
    r"for example,|by way of example,|"
    r"without\b|once\b|thus,"
    r")",
    re.I,
)

def _looks_rc39_argument_insertion(
    txt: str,
    m: Dict[str, float],
    strong_emotion_shift: bool,
    notice_like: bool,
) -> bool:
    """
    RC39(고난도 문장 삽입) '깨끗한 지문' 판별:

    - 단일 주제의 설명/분석/논증 지문이어야 하고(_looks_expository_topic),
    - 공지/서신/강한 감정 서사는 제외,
    - 길이 130~260 토큰, 문장 수 5개 이상,
    - 'analogy, argument, reasoning, logic' 같은 논증 메타 단어가 있고,
    - 'by contrast, nevertheless, still, on the other hand' 같은 강한 대조/반전 신호가 함께 존재할 것.
    """
    if not txt:
        return False

    if notice_like or strong_emotion_shift:
        return False

    # 기본적으로 설명/논증형 지문인지 확인
    if not _looks_expository_topic(txt, m):
        return False

    tok = m.get("tok", 0)
    sent = m.get("sent", 1)

    if tok < 130 or tok > 260:
        return False
    if sent < 5:
        return False

    # 논증 메타 + 대조 신호가 동시에 있는 경우만 RC39로 본다
    if not RE_RC39_META.search(txt):
        return False
    if not RE_RC39_CONTRAST.search(txt):
        return False

    return True


# ---------- Toggle: RC21 pass-through to LLM ----------
FORCE_RC21_PASS = os.getenv("FORCE_RC21_PASS", "1").lower() in ("1", "true", "yes", "on")

# ✅ ---------- Evergreen types ----------
"""
EVERGREEN_TYPES = [
    "RC22", "RC23", "RC24"
]

_EVERGREEN_BASE_FIT = {
    "RC22": 0.46, "RC23": 0.46, "RC24": 0.44
}
"""
EVERGREEN_TYPES = [
    "RC22", "RC23", "RC24", "RC40",
    #"RC31", "RC32", "RC33",
    # "RC29",  # ❌ Evergreen에서 제거
    "RC30",  # 어휘 적절성은 여전히 범용 후보로 유지
    "RC41", "RC42",
]

_EVERGREEN_BASE_FIT = {
    "RC22": 0.46, "RC23": 0.46, "RC24": 0.44, "RC40": 0.42,
    #"RC31": 0.45, "RC32": 0.45, "RC33": 0.43,
    # "RC29": 0.48,  # ❌ 필요 없으면 삭제해도 되고, 남겨둬도 실제로는 안 쓰임
    "RC30": 0.47,
    "RC41": 0.41, "RC42": 0.41,
}

# ---------- NEW: Length-first gating (세분화) ----------
# ≤150 → RC33까지, 151–199 → RC40까지, ≥200 → RC41+
def _length_band(tokens: int) -> str:
    if tokens <= 150:
        return "upto_rc33"
    if tokens < 200:
        return "upto_rc40"
    return "rc41_plus"

# 길이 밴드별 허용 유형(검출/주입/보정 모두 이 집합을 통과해야 함)
ALLOW_BY_LENGTH = {
    "upto_rc33": {
        "RC18","RC19","RC20","RC21","RC22","RC23","RC24",
        "RC25", "RC26",  # ✅ 짧은 표/그래프 설명 지문도 RC25 허용
        "RC27","RC28","RC29","RC30",
        "RC31","RC32","RC33",
    },
    "upto_rc40": {
        "RC18","RC19","RC20","RC21","RC22","RC23","RC24",
        "RC25","RC26","RC27","RC28","RC29","RC30",
        "RC31","RC32","RC33","RC34","RC35","RC36","RC37","RC38","RC39","RC40",
    },
    "rc41_plus": {
        "RC18","RC19","RC20","RC21","RC22","RC23","RC24",
        "RC25","RC26","RC27","RC28","RC29","RC30",
        "RC31","RC32","RC33","RC34","RC35","RC36","RC37","RC38","RC39","RC40",
        "RC41","RC42",
    },
}

# ---------- Scorers ----------
def _score_rc30_semantic(text: str) -> float:
    score = 0.0
    if RE_LEXICAL_META.search(text):
        score += 0.35
    if RE_CONTRAST_EVAL.search(text):
        score += 0.25
    if len(RE_DERIV.findall(text)) >= 3:
        score += 0.10
    return min(0.80, score)

def _score_rc29_semantic(text: str) -> float:
    score = 0.0
    if RE_GRAMMAR_META.search(text):
        score += 0.30
    return min(0.55, score)

def _score_rc29_structure(text: str) -> float:
    """
    ★ 인용 모드용 RC29 구조 스코어러
    - ①~⑤, 밑줄이 전처리에서 사라진 상태에서도
      '문장 구조'만 보고 문법 판단(RC29) 적합성을 추정.
    - 전형적인 RC29 지문 패턴:
      · 90~220단어 정도의 설명/분석 지문
      · 문장 수 4개 이상
      · 관계사/종속절/분사구 등 문법 포인트가 군데군데 존재
    """
    if not text:
        return 0.0

    tokens = re.findall(r"[A-Za-z']+|\d+%?", text)
    tok = len(tokens)
    if tok < 60 or tok > 260:
        return 0.0

    sent_cnt = max(1, len(re.findall(r"[.!?]+(?:\s|$)", text)))
    if sent_cnt < 4:
        return 0.0

    lc = text.lower()
    rel_hits = len(re.findall(r"\b(which|that|who|whom|whose|where|when)\b", lc))
    sub_hits = len(re.findall(r"\b(because|although|though|while|when|if|unless|since|after|before)\b", lc))
    aux_hits = len(re.findall(
        r"\b(am|is|are|was|were|has|have|had|do|does|did|can|could|should|would|must|may|might)\b",
        lc,
    ))

    score = 0.0
    if rel_hits >= 2:
        score += 0.25
    elif rel_hits == 1:
        score += 0.15

    if sub_hits >= 2:
        score += 0.20
    elif sub_hits == 1:
        score += 0.10

    if sent_cnt >= 5:
        score += 0.10
    if tok >= 100:
        score += 0.10
    if aux_hits >= 10:
        score += 0.05

    # 상한은 대략 0.65 정도로 두고, 나머지는 length/signal boost에서 더 얹어 줄 수 있게
    return min(0.65, score)

def _score_rc21_semantic(text: str, *, has_bullets: bool, has_underline: bool, has_insert_mark: bool) -> float:
    """
    RC21: 문맥 기반 의미/비유/관용 표현 해석 가능성 스코어링.
    - 형식(①~⑤, 밑줄, 삽입표시)이 있어도 비유/관용 신호가 강하면 RC21 후보로 인정.
    - 다만 강한 형식 신호(①~⑤ + 밑줄 등)가 있으면 RC29/30/35/38과의 충돌을 피하기 위해 소폭 감쇠.
    """
    shell_hit = any(p.search(text) for p in RE_IDIOM_SHELLS)
    simile_hit = bool(RE_SIMILE.search(text))
    lc = text.lower()
    cue_hits = sum(1 for w in METAPHOR_CUES if w in lc)

    score = 0.0
    if shell_hit:
        score += 0.50    # 관용구 패턴 (the ~ in the room, on thin ice 등)
    if simile_hit:
        score += 0.30    # like / as ~ 직유 패턴
    if cue_hits >= 2:
        score += 0.20    # 비유 단어가 여러 개
    elif cue_hits == 1:
        score += 0.10    # 비유 단어 1개

    # 형식 신호가 강하면 RC29/30/35/38이 더 우선이므로 약간 감쇠
    if has_bullets or has_underline or has_insert_mark:
        score *= 0.85

    return score


def _score_set_signals(text: str) -> dict:
    t = text or ""
    score_41 = score_42 = 0.0
    if RE_LOWER_PARENS.search(t):     score_41 += 0.18; score_42 += 0.15
    if RE_ROMAN_PARENS.search(t):     score_41 += 0.10; score_42 += 0.08
    if RE_PART_HEADING.search(t):     score_41 += 0.08; score_42 += 0.06
    if RE_SECTION_HEAD.search(t):     score_41 += 0.06; score_42 += 0.05
    if RE_Q_RANGE.search(t):          score_41 += 0.07; score_42 += 0.06
    if RE_FORMER_LATTER.search(t):    score_41 += 0.05; score_42 += 0.05
    if RE_REF_PASSAGE.search(t):      score_41 += 0.06; score_42 += 0.06
    para_cnt = max(1, t.count("\n\n") + 1)
    if para_cnt >= 2:
        boost = min(0.06, 0.02 * (para_cnt - 1))
        score_41 += boost; score_42 += boost
    score_41 = min(score_41, 0.30)
    score_42 = min(score_42, 0.28)
    return {"rc41": score_41, "rc42": score_42}

# ✅ Evergreen 주입 유틸 (길이 게이트 적용)
def _inject_evergreen_candidates(cands: List[Dict], passage: str, allowed_types: set[str]) -> List[Dict]:
    existing = {c.get("type") for c in cands}

    # 길이/기초 통계
    metrics = _basic_counts(passage or "")
    notice_like = _is_notice_like(passage or "", metrics)

    has_strong_format = bool(
        RE_NOTICE_KEYS.search(passage)
        or RE_INSERT_PARENS.search(passage)
        or RE_UNDERLINE.search(passage)
        or notice_like
    )
    boost = 0.0 if has_strong_format else 0.03

    # 🔑 전기형(개인 생애) 지문인지 여부
    is_bio_passage = bool(RE_BIO.search(passage))

    # 전기형일 때는 제목/주제/요지/빈칸/AB요약 Evergreen은 주입하지 않는다.
    BIO_BLOCKED_EVERGREEN = {
        "RC22", "RC23", "RC24",  # 요지/주제/제목
        "RC31", "RC32", "RC33",  # 빈칸
        "RC40",                  # AB 요약
    }

    # 안내문(Notice)일 때는 주제/요지/제목 + 빈칸/AB 요약 Evergreen도 주입하지 않는다.
    NOTICE_BLOCKED_EVERGREEN = {
        "RC22", "RC23", "RC24",
        "RC31", "RC32", "RC33",
        "RC40",
    }

    for t in EVERGREEN_TYPES:
        if t not in allowed_types:
            continue

        # 전기형 지문이면 위 타입들은 스킵 → RC26이 상대적으로 두드러지게 함
        if is_bio_passage and t in BIO_BLOCKED_EVERGREEN:
            continue

        # 안내문 지문이면 요지/주제/제목/빈칸/AB요약 Evergreen은 스킵 → RC27이 두드러지게 함
        if notice_like and t in NOTICE_BLOCKED_EVERGREEN:
            continue

        if t not in existing:
            base = _EVERGREEN_BASE_FIT.get(t, 0.45)
            cands.append({
                "type": t,
                "fit": float(max(0.0, min(1.0, base + boost))),
                "reason": "형식 신호 없어도 범용 출제가 가능한 Evergreen 유형",
                "prep_hint": "지문 전반의 논리/구문/어휘 점검"
            })
    return cands

def _llm_rc29_feasible(passage: str) -> bool:
    if not passage or len(passage.split()) < 30:
        return False
    user = (
        "Goal: Decide if RC29 (Grammar Judgment) is feasible for the given passage *without rewriting it*.\n\n"
        "STRICT RULES:\n"
        "- Do NOT rewrite, add, delete, or reorder any part of the passage.\n"
        "- Decide feasibility ONLY: whether you could pick 5 short spans (1–3 tokens) as underlined targets "
        "and make exactly ONE of them ungrammatical while the others remain correct in context.\n"
        "- Candidate grammar points to consider: relative (that/which/who/when/where), S/V agreement or tense, "
        "modal+base (must/should/can + V), passive (be + p.p.), participle (-ing/-ed phrase).\n\n"
        "OUTPUT JSON ONLY (choose exactly one):\n"
        "1) {{\n"
        '   "feasible": true\n'
        "}}\n"
        "2) {{\n"
        '   "feasible": false\n'
        "}}\n\n"
        "Passage:\n"
        "```passage\n"
        f"{passage}\n"
        "```"
    )
    try:
        resp = call_llm_json(
            system=("You evaluate feasibility for CSAT RC29 using ONLY the provided passage. "
                    "Return JSON only. No commentary."),
            user=user,
            temperature=0.0,
            max_tokens=80,
        )
        return bool(resp.get("feasible") is True)
    except Exception:
        return False

def _collapse_set_groups(cands: List[Dict]) -> List[Dict]:
    by_type = {c["type"]: c for c in cands}
    out = cands[:]

    def _remove(types):
        nonlocal out
        tset = set(types)
        out = [c for c in out if c.get("type") not in tset]

    # RC41 & RC42를 하나의 세트로 병합
    if "RC41" in by_type and "RC42" in by_type:
        fit = max(by_type["RC41"]["fit"], by_type["RC42"]["fit"])
        _remove(["RC41", "RC42"])
        out.append({
            "type": "RC41",
            "fit": float(fit),
            "reason": "세트 지문: 하위 문항 2개 동시 생성 적합",
            "prep_hint": "세트 선택 시 멤버 전부 생성",
            "ui_label": "RC41_42",
            "members": ["RC41", "RC42"],
        })

    out = sorted(out, key=lambda x: x["fit"], reverse=True)
    return out[:12]

# ---------- NEW: Lightweight metrics & boosts ----------
DISCOURSE_MARKERS = {
    "however","nevertheless","nonetheless","instead","rather",
    "therefore","thus","consequently","hence","as a result",
    "moreover","furthermore","in","in addition","for example","for instance"
}
DEICTICS = {"this","that","these","those","it","they","which","whose","where","when"}

RE_RC40_PAIRING = re.compile(
    r"\b("
    r"on the one hand\b.*\bon the other hand\b|"  # on the one hand / on the other hand
    r"both\b.*\band\b|"                           # both A and B
    r"not only\b.*\bbut\b|"                       # not only A but (also) B
    r"while\b.*\b(but|and)\b|"                    # while A, (but/and) B
    r"whereas\b"                                  # whereas
    r")",
    re.I | re.S,
)

def _looks_expository_topic(txt: str, m: Dict[str, float]) -> bool:
    """
    RC23(주제 파악)에 특히 잘 맞는 '설명/분석(expository)' 지문인지 판별.
    - 하나의 개념/논지를 여러 문장으로 풀어 설명하는 전형적인 설명문.
    - 편지/공지/전기/표·그래프/강한 감정 변화/서사적 요소는 없음.
    - 패턴 신호(①, (A), 밑줄 등)는 고려하지 않음(있어도/없어도 상관 X).
    """
    t = txt or ""
    lc = t.lower()

    tok = m.get("tok", 0)
    sent = m.get("sent", 1)
    dm_cnt = m.get("dm_cnt", 0)

    # 1) 길이: 어느 정도 긴 단일 설명문
    if tok < 90:
        return False
    if sent < 3:
        return False

    # 2) 편지/공지/전기/웹 공지 같은 형식은 제외
    if RE_NOTICE_KEYS.search(t):
        return False
    if RE_BIO.search(t):
        return False
    if RE_LETTER_DEAR.search(t) or RE_LETTER_CLOSE.search(t):
        return False
    if RE_WEBSITE_URL.search(t):
        return False

    # 3) 강한 감정 변화(서사형)는 제외
    neg_hits = sum(1 for w in NEG_EMO if w in lc)
    pos_hits = sum(1 for w in POS_EMO if w in lc)
    has_turning = bool(RE_TURNING.search(t))
    if (neg_hits > 0 and pos_hits > 0) or (has_turning and RE_EMOTION.search(t)):
        return False

    # 4) 논리 전개용 담화표지가 어느 정도 있는 설명/분석 스타일
    #    (however, therefore, for example, in addition 등)
    if dm_cnt < 2:
        return False

    # 5) '당위/권고' 중심의 강한 설득문(RC20 순수형)은 살짝 제외
    #    (단순히 "we argue that" 같은 표현은 여기서 걸러지지 않음)
    if RE_ARGUMENT.search(t) and dm_cnt == 0:
        # 당위 표현만 있고 논리 전개 표지 거의 없으면 RC20 쪽에 더 가깝다고 보고 제외
        return False

    return True


def _looks_rc31_blank_friendly(txt: str, m: Dict[str, float]) -> bool:
    """
    RC31(핵심 개념 단어 빈칸) 적합 지문인지 추가로 필터링.
    - 기본적으로는 설명/분석(expository) 지문이어야 하고(_looks_expository_topic 기반),
    - 번호/라벨/삽입표 등 다른 유형 신호가 없어야 하며,
    - 문장 길이가 어느 정도 길어 '핵심 개념'을 비워두기 좋은 구조일 것.
    """
    if not txt:
        return False

    # 1) 먼저 전형적인 설명문인지 확인 (편지/공지/전기/감정 변화 등 이미 제외)
    if not _looks_expository_topic(txt, m):
        return False

    tok = m.get("tok", 0)
    avg_len = m.get("avg_len", 0.0)

    # 2) 길이 범위: RC31 단일 지문에 적합한 대략적인 구간
    if tok < 90 or tok > 260:
        return False

    # 3) 다른 형식 신호가 있으면 RC31로 쓰기 어렵다고 본다
    #   - ①~⑤, ( ① ) : RC29/30/35/38 계열
    #   - (A)(B)(C)    : RC36/37 계열
    #   - (a)(b)(c)    : RC41/42 세트형
    if RE_NUM_BULLETS.search(txt):
        return False
    if RE_INSERT_PARENS.search(txt):
        return False
    if RE_PARAGRAPH_LABELS.search(txt):
        return False
    if RE_LOWER_PARENS.search(txt):
        return False

    if avg_len < 14:
        return False

    return True

def _looks_rc33_high_level(txt: str, m: Dict[str, float]) -> bool:
    """
    RC33(고난도 구/절 빈칸) 전형 패턴:
    - 단일 주제의 설명/분석(expository) 지문이어야 하고(_looks_expository_topic 기반),
    - 길이가 충분히 길고(추상 개념 전개),
    - 문장 수와 담화표지/지시어가 많으며,
    - 'in turn', 'it follows that', 'thus' 같은 논리 pivot이 등장.
    """
    if not txt:
        return False

    # 1) 기본적으로 설명/분석 지문이 아니면 RC33 하이레벨로 보지 않음
    if not _looks_expository_topic(txt, m):
        return False

    tok = m.get("tok", 0)
    sent = m.get("sent", 1)
    dm_cnt = m.get("dm_cnt", 0)
    deictic_cnt = m.get("deictic_cnt", 0)
    lc = txt.lower()

    # 2) 길이/문장 수: 어느 정도 장문 + 문장 여러 개
    if tok < 120 or tok > 260:
        return False
    if sent < 5:
        return False

    # 3) 담화표지·지시어 많이 쓰이는 추상 논리 전개
    if dm_cnt < 3:
        return False
    if deictic_cnt < 5:
        return False

    # 4) 논리적 pivot 표현: in turn / it follows that / thus / therefore / consequently / as a result 등
    if not RE_RC33_PIVOT.search(lc):
        return False

    return True

def _looks_rc34_global_blank(txt: str, m: Dict[str, float]) -> bool:
    """
    RC34(고난도 구/절 빈칸) 전형 패턴:
    - 단일 주제의 설명/분석(expository) 지문이어야 하고(_looks_expository_topic 기반),
    - RC33보다 조금 더 '장문·고난도'에 가깝고,
    - 문장 수/담화표지/지시어가 충분히 많으며,
    - 전환/인과 pivot 역할을 하는 표현이 존재.
      (예: however, instead, on the other hand, therefore, thus, as a result, in turn 등)
    """
    if not txt:
        return False

    # 1) 기본적으로 설명/분석 지문이 아니면 RC34 후보가 아님
    if not _looks_expository_topic(txt, m):
        return False

    tok = m.get("tok", 0)
    sent = m.get("sent", 1)
    dm_cnt = m.get("dm_cnt", 0)
    deictic_cnt = m.get("deictic_cnt", 0)
    avg_len = m.get("avg_len", 0.0)
    lc = txt.lower()

    # 2) 길이/문장 수: RC33보다 조금 더 장문 쪽을 우선
    #   - 길이 140~270 정도, 문장 5개 이상
    if tok < 140 or tok > 270:
        return False
    if sent < 5:
        return False

    # 3) 담화표지/지시어가 충분히 많아 '논리 연결부'가 풍부해야 함
    if dm_cnt < 3:
        return False
    if deictic_cnt < 5:
        return False
    if avg_len < 16:
        return False

    # 4) 전환/인과 pivot 표현(“in turn”, “it follows that”, “however”, “instead”, “on the other hand” 등)
    pivot = bool(RE_RC33_PIVOT.search(lc) or re.search(
        r"\b(however|instead|on the other hand|but)\b", lc
    ))
    if not pivot:
        return False

    return True



def _looks_rc40_ab_summary(txt: str, m: Dict[str, float]) -> bool:
    """
    RC40(AB 요약) 적합 지문 판별:

    - 전형적인 설명/분석(expository) 지문이어야 하고(_looks_expository_topic 기반),
    - 단일 주제를 여러 문장으로 전개하며,
    - '두 가지 측면/요소'로 압축 가능한 대조·보완 구조가 있을 것.
      (예: 제한 vs 보완, 문제 vs 해결, 원인 vs 결과 등)
    """
    if not txt:
        return False

    # 1) 기본적으로 설명/분석 지문인지 확인
    if not _looks_expository_topic(txt, m):
        return False

    tok = m.get("tok", 0)
    sent = m.get("sent", 1)
    dm_cnt = m.get("dm_cnt", 0)

    # 길이: 중장문 위주 (RC40는 세트형까지는 아님)
    if tok < 90 or tok > 260:
        return False
    if sent < 3:
        return False

    # 논리 전개 표지 최소 2개 이상
    if dm_cnt < 2:
        return False

    lc = txt.lower()

    # 2) AB 페어 구조 신호:
    #    - 명시적 페어링 표현 (both A and B, not only A but B, on the one hand...)
    #    - 혹은 while/whereas/although 등으로 두 측면을 비교·대조
    has_pair = bool(RE_RC40_PAIRING.search(lc))
    has_basic_contrast = bool(
        re.search(r"\b(while|whereas|although|though)\b", lc)
    )

    if not (has_pair or has_basic_contrast):
        return False

    return True

def _looks_rc35_expository_flow(
    txt: str,
    m: Dict[str, float],
    strong_emotion_shift: bool,
) -> bool:
    """
    RC35(무관한 문장 찾기) 후보 지문 판별:

    핵심 조건 (사용자 요구 반영):
    - 번호(①~⑤) 유무와 관계없이,
    - 문장이 5개 이상이면 RC35 출제 '가능'으로 본다.
    - 단, 공지/전기/서신/강한 감정 서사 등은 제외하고,
      기본적으로 하나의 주제를 설명하는 설명문(expository)에 가깝게 필터링한다.
    """

    if not txt:
        return False

    sent_cnt = m.get("sent", 1)
    tok = m.get("tok", 0)

    # 1) 문장 수: 5문장 이상일 때만 RC35 후보
    #    (너무 긴 세트형 장문은 RC41/42 쪽이 더 적합하므로 대략 상한만 둠)
    if sent_cnt < 5:
        return False
    if tok < 70 or tok > 260:
        return False

    # 2) 안내문/전기/서신/웹 공지면 RC35보다는 다른 유형이 우선
    if _is_notice_like(txt, m):
        return False
    if RE_NOTICE_KEYS.search(txt):
        return False
    if RE_BIO.search(txt):
        return False
    if RE_LETTER_DEAR.search(txt) or RE_LETTER_CLOSE.search(txt):
        return False
    if RE_WEBSITE_URL.search(txt):
        return False

    # 3) 강한 감정 변화 서사는 RC19가 더 적합
    if strong_emotion_shift:
        return False

    # 4) 설명문(expository)인지 간단히 체크
    #    - 이미 정의된 _looks_expository_topic을 그대로 활용하면 가장 안전
    if not _looks_expository_topic(txt, m):
        return False

    return True

def _looks_rc38_insertion_friendly(
    txt: str,
    m: Dict[str, float],
    strong_emotion_shift: bool,
    notice_like: bool,
) -> bool:
    """
    RC38(문장 삽입) '깨끗한 지문' 판별:

    - 단일 주제의 설명/분석(expository) 지문이어야 하고(_looks_expository_topic 기반),
    - 공지/전기/서신/강한 감정 서사는 제외,
    - 길이 120~230 토큰, 문장 수 5개 이상,
    - 중간부에 전환/예시/대조 pivot 문장이 1개 이상 존재할 것.
    """
    if not txt:
        return False

    if notice_like or strong_emotion_shift:
        return False

    # 기본적으로 설명문인지 확인
    if not _looks_expository_topic(txt, m):
        return False

    tok = m.get("tok", 0)
    sent = m.get("sent", 1)

    if tok < 120 or tok > 230:
        return False
    if sent < 5:
        return False

    # pivot 표현 존재 여부
    if not RE_RC38_PIVOT.search(txt):
        return False

    return True

def _classify_abc_for_rc36_37(
    txt: str,
    m: Dict[str, float],
    strong_emotion_shift: bool,
) -> str:
    """
    (A)(B)(C) 라벨이 있는 지문을 RC36 / RC37 / none 중 하나로 분류.
    - RC36: 정의/예시 중심 일반 설명문 단락 배열
    - RC37: 연구/실험 보고형 + 단계적 논증(조건-결과, 균형, 모형 등)
    """
    # (A)(B)(C) 라벨 없으면 둘 다 아님
    if not RE_PARAGRAPH_LABELS.search(txt):
        return "none"

    # 안내문/전기/서신/강한 정서 변화는 RC36·RC37 모두 제외
    if strong_emotion_shift:
        return "none"
    if _is_notice_like(txt, m):
        return "none"
    if RE_NOTICE_KEYS.search(txt):
        return "none"
    if RE_BIO.search(txt):
        return "none"
    if RE_LETTER_DEAR.search(txt) or RE_LETTER_CLOSE.search(txt):
        return "none"

    tok = m.get("tok", 0)
    sent = m.get("sent", 1)

    # 너무 짧거나 너무 긴 (A)(B)(C)는 여기서 다루지 않음
    if tok < 70 or tok > 260:
        return "none"
    if sent < 4:
        return "none"

    lc = txt.lower()
    expository      = _looks_expository_topic(txt, m)

    exp_hits        = len(RE_RC_EXP_LIKE.findall(lc))
    strong_exp_hits = len(RE_RC37_STRONG_EXP.findall(lc))
    reasoning_hits  = len(RE_RC37_REASONING_META.findall(lc))
    causal_hits     = len(RE_RC37_CAUSAL_CHAIN.findall(lc))
    example_hits    = len(RE_RC36_EXAMPLE_CUE.findall(lc))
    definition_hits = len(RE_RC36_DEF_CUE.findall(lc))

    # 감정 변화 + (연구 신호 없음) + (설명문 아님) → RC36/37 둘 다 제외
    if strong_emotion_shift and not exp_hits and not expository:
        return "none"

    # 1) 강한 실험/연구 보고형: RC37 고정
    #    - 실험 장치/참가자/무작위배정 등 + 일반 연구/데이터 신호가 함께 있을 때
    if strong_exp_hits >= 1 and exp_hits >= 2:
        return "RC37"

    # 2) 연구 단어는 조금 있지만, 전형적인 정의/예시 중심 설명문:
    #    - 연구가 '예시로 살짝' 등장하는 RC36 기출을 RC37로 보내지 않도록 예외 처리
    if exp_hits >= 1 and expository and (example_hits + definition_hits) >= 2 and reasoning_hits == 0:
        return "RC36"

    # 3) 단계적 논증 구조 (연구 단어 없어도 RC37로 보내고 싶은 경우)
    #    - 논증/모형/원리 메타 단어 + 인과 연쇄 신호가 동시에 있을 때
    if expository and reasoning_hits >= 1 and causal_hits >= 1:
        return "RC37"

    # 4) 전형적인 정의/예시 중심 설명문 → RC36
    if expository and (example_hits >= 1 or definition_hits >= 1):
        return "RC36"

    # 5) 설명문이긴 한데 위 신호가 애매하게 적다면:
    #    - 기출 분포상 RC36이 더 많으므로 기본값을 RC36으로 둠
    if expository:
        return "RC36"

    # 6) 설명문도 아니고 애매하지만 (A)(B)(C) 구조는 잡힌 경우:
    #    - 기본은 RC37로 두되, 이후 add 단계에서 다시 걸러질 수 있음
    return "RC37"




def _basic_counts(text: str) -> Dict[str, float]:
    t = (text or "").strip()
    tokens = re.findall(r"[A-Za-z]+(?:['-][A-Za-z]+)?|\d+%?", t)
    tok = len(tokens)
    sent = max(1, len(re.findall(r"[.!?]+(?:\s|$)", t)))
    paras = max(1, t.count("\n\n") + 1)
    lower = [w.lower() for w in tokens if re.match(r"[A-Za-z]", w)]
    uniq = len(set(lower))
    ttr = (uniq / max(1, len(lower))) if lower else 0.0
    dm_cnt = sum(1 for w in lower if w in DISCOURSE_MARKERS)
    deictic_cnt = sum(1 for w in lower if w in DEICTICS)
    digits_cnt = len(re.findall(r"\b\d{2,4}(?:%|[.,]?\d+)?\b", t))
    unit_cnt = len(re.findall(r"\b(?:km|kg|cm|mm|°c|°f|mph|percent|percentages?)\b", t, re.I))
    proper_like = len(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", t))
    return {
        "tok": tok, "sent": sent, "paras": paras, "ttr": ttr,
        "avg_len": (tok / max(1, sent)),
        "dm_cnt": dm_cnt, "deictic_cnt": deictic_cnt,
        "num_cnt": digits_cnt + unit_cnt, "proper_like": proper_like
    }


def _is_notice_like(txt: str, m: Dict[str, float]) -> bool:
    """
    RC27/RC28 안내문 후보 여부 판별:
    - 섹션 라벨(Deadline, Restrictions, Awards 등) + bullet/가격/기간 정보가 다수
    - 짧은 사실 문장 여러 개로 구성된 공지/안내/서비스 소개문
    """
    if not txt:
        return False

    t = txt.lower()

    # 1) 강한 형식 신호: 섹션 라벨 or URL
    strong = bool(RE_NOTICE_KEYS.search(txt) or RE_WEBSITE_URL.search(txt))

    # 2) 보조 신호들
    bullet_hits = bool(RE_BULLET_DOT.search(txt))
    price_hits = bool(RE_PRICE_SIGN.search(txt))
    date_or_period = bool(
        re.search(
            r"\b(deadline|period|schedule|from\s+\w+\s+\d|\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.)|"
            r"tour\s+times?|renovation period|from\s+june|from\s+november)\b",
            t,
        )
    )
    # 안내문 특유의 서브 섹션 키워드
    section_hits = len(
        re.findall(
            r"\b(age requirement|restrictions?|participants?|awards?|evaluation criteria|"
            r"activities?|use|return|service range|purchase information|tour times?|"
            r"renovation period|areas to be closed|card type|additional information)\b",
            t,
        )
    )

    fact_signals = sum(
        [
            1 if bullet_hits else 0,
            1 if price_hits else 0,
            1 if date_or_period else 0,
            1 if section_hits >= 1 else 0,
        ]
    )

    # 3) 문장 수/길이 기반 필터
    tok = m.get("tok", 0)
    sent = m.get("sent", 1)

    # - 문장 3~4개 이상 + 사실 신호 2개 이상
    # - 너무 긴 논설문/장문은 제외 (세트/설명문 가능성)
    if (strong and sent >= 3) or (fact_signals >= 2 and sent >= 4 and tok <= 220):
        return True
    return False

def _bump(base: Dict[str, Dict], t: str, v: float):
    if t in base:
        base[t]["fit"] = float(min(1.0, base[t]["fit"] + v))

def _apply_length_based_boosts(base: Dict[str, Dict], m: Dict[str, float]) -> None:
    tok, avg_len, paras = m["tok"], m["avg_len"], m["paras"]
    if tok < 150:
        for t,v in (("RC18",0.06),("RC19",0.04),("RC27",0.05),("RC28", 0.03),("RC24",0.02)):
            _bump(base,t,v)
    elif tok < 190:
        for t,v in (("RC20",0.03),("RC22",0.04),("RC23",0.04),("RC26",0.03),
                    ("RC25",0.03),("RC27",0.02),("RC28",0.02),
                    ("RC29",0.04),("RC30",0.03),("RC36",0.03)):
            _bump(base,t,v)
    else:
        for t,v in (("RC31",0.04),("RC32",0.04),("RC33",0.03),("RC34",0.04),
                    ("RC35",0.03),("RC37",0.03),("RC38",0.03),("RC39",0.03),
                    ("RC40",0.03)):
            _bump(base,t,v)
        if tok >= 220:
            _bump(base, "RC41", 0.04)
            _bump(base, "RC42", 0.04)
    if avg_len >= 18:
        for t,v in (("RC31",0.02),("RC32",0.03),("RC33",0.03),("RC29",0.02)):
            _bump(base,t,v)
    if paras >= 2:
        for t,v in (("RC22",0.03),("RC23",0.03),("RC32",0.02),("RC33",0.02),("RC40",0.03)):
            _bump(base,t,v)
    if paras >= 3 and m["tok"] >= 180:
        for t,v in (("RC41",0.03),("RC42",0.03)):
            _bump(base,t,v)

def _apply_signal_boosts(base: Dict[str, Dict], txt: str, m: Dict[str, float]) -> None:
    # 담화표지·지시어 기반 보정
    if m["dm_cnt"] >= 4:
        for t,v in (("RC22",0.05),("RC23",0.04),("RC31",0.03),("RC32",0.03),("RC33",0.03),("RC38",0.03),("RC39",0.03)):
            _bump(base,t,v)
    if m["deictic_cnt"] >= 6:
        for t,v in (("RC38",0.04),("RC39",0.04),("RC36",0.03),("RC37",0.03),("RC22",0.02),("RC40",0.02)):
            _bump(base,t,v)
    if RE_RC39_META.search(txt) and RE_RC39_CONTRAST.search(txt):
        _bump(base, "RC39", 0.06)            


    notice_like = _is_notice_like(txt, m)            

        # ★ RC40: 페어링/대조 신호가 뚜렷한 설명문에 추가 가점
    if not notice_like and not RE_BIO.search(txt):
        if RE_RC40_PAIRING.search(txt):
            _bump(base, "RC40", 0.06)

    # --- RC25: 표·그래프/통계 기반 지문 강신호 ---
    # --- RC25: 표·그래프/통계 기반 지문 강신호 ---
    chart_like = bool(RE_TABLEY.search(txt) or RE_CHARTY.search(txt))
    sent_cnt = m.get("sent", 1)

    # ⚠ 선지로 바로 쓸 수 있는 문장 최소 5개 필요
    if sent_cnt >= 5 and (chart_like or m["num_cnt"] >= 3):
        year_hits = len(re.findall(r"\b\d{4}\b", txt))
        compare_hits = len(re.findall(r"\b(compared to|compared with|than|whereas)\b", txt, re.I))
        group_hits = len(re.findall(
            r"\b(rural|urban|country|countries|region|regions|age group|age-group|age groups|respondents|survey)\b",
            txt,
            re.I,
        ))

        if m["num_cnt"] >= 3:
            _bump(base, "RC25", 0.08)
        if chart_like:
            _bump(base, "RC25", 0.06)
        if year_hits >= 2:
            _bump(base, "RC25", 0.05)
        if compare_hits >= 1:
            _bump(base, "RC25", 0.04)
        if group_hits >= 1:
            _bump(base, "RC25", 0.04)

    if RE_BIO.search(txt):
        _bump(base,"RC26",0.06)
    if m["ttr"] < 0.35:
        for t,v in (("RC31",0.04),("RC40",0.04)):
            _bump(base,t,v)
    if m["proper_like"] >= 6:
        for t,v in (("RC22",0.02),("RC23",0.02),("RC31",0.02),("RC40",0.02)):
            _bump(base,t,v)

    has_letter = bool(RE_LETTER_DEAR.search(txt) or RE_LETTER_CLOSE.search(txt))
    has_intent = bool(
        RE_INTENT_REQUEST.search(txt)
        or RE_INTENT_INQUIRY.search(txt)
        or RE_INTENT_GUIDE.search(txt)
        or RE_INTENT_PROMO.search(txt) 
    )

    if has_letter:
        _bump(base, "RC18", 0.10)

    # intent 표현만 있어도 RC18 가중치 추가
    if has_intent:
        _bump(base, "RC18", 0.06)

    # 편지 형식 + intent가 동시에 있으면 한 번 더 소폭 보정
    if has_letter and has_intent:
        _bump(base, "RC18", 0.04)

    if RE_EMOTION.search(txt):
        _bump(base,"RC19",0.06)
    if RE_ARGUMENT.search(txt):
        _bump(base,"RC20",0.05)

    shell_hit = any(p.search(txt) for p in RE_IDIOM_SHELLS)
    simile_hit = bool(RE_SIMILE.search(txt))
    lc = txt.lower()
    cue_hits = sum(1 for w in METAPHOR_CUES if w in lc)
    if shell_hit or simile_hit or cue_hits >= 1:
        _bump(base,"RC21",0.05)
    if notice_like:
        _bump(base, "RC27", 0.12)
        _bump(base, "RC28", 0.06)

        # 안내문에서는 설명문 Evergreen 계열을 약하게 줄인다.
        for t, delta in (
            ("RC22", -0.12), ("RC23", -0.12), ("RC24", -0.08),
            ("RC31", -0.12), ("RC32", -0.10), ("RC33", -0.10),
            ("RC40", -0.10),
        ):
            if t in base:
                base[t]["fit"] = float(max(0.0, base[t]["fit"] + delta))
    elif RE_NOTICE_KEYS.search(txt) or RE_WEBSITE_URL.search(txt):
        _bump(base,"RC27",0.05)
        _bump(base,"RC28",0.04)
    if RE_GRAMMAR_META.search(txt):
        _bump(base,"RC29",0.04)
    if RE_LEXICAL_META.search(txt):
        _bump(base,"RC30",0.04)
    if RE_NUM_BULLETS.search(txt) and RE_UNDERLINE.search(txt):
        _bump(base,"RC29",0.08); _bump(base,"RC30",0.06)
    if RE_INSERT_PARENS.search(txt):
        _bump(base,"RC35",0.06); _bump(base,"RC38",0.05)
    if RE_PARAGRAPH_LABELS.search(txt):
        _bump(base,"RC36",0.05); _bump(base,"RC37",0.04)
    if RE_LOWER_PARENS.search(txt):
        _bump(base,"RC41",0.05); _bump(base,"RC42",0.05)
    # --- RC23 계열: 전형적인 설명/분석 지문에서 주제/제목/요지 가중치 ---
    if _looks_expository_topic(txt, m):
        # 제목 추론을 대표 유형으로 약간 더 높게
        _bump(base, "RC24", 0.10)  # 제목 추론
        _bump(base, "RC23", 0.06)  # 주제 파악
        _bump(base, "RC22", 0.04)  # 요지 파악

def _apply_final_table_boosts(merged: Dict[str, Dict], passage: str) -> None:
    metrics = _basic_counts(passage or "")
    _apply_length_based_boosts(merged, metrics)
    _apply_signal_boosts(merged, passage or "", metrics)

# ---------- Public API ----------
def rule_based_candidates(passage: str) -> List[Dict]:
    cands: List[Dict] = []
    txt = sanitize_user_passage(passage or "")
    tokens = len(txt.split())
    band = _length_band(tokens)
    allowed_types = ALLOW_BY_LENGTH.get(band, ALLOW_BY_LENGTH["upto_rc33"])

    # emotion-shift 판정용 (RC19 강신호)
    lc = txt.lower()
    neg_hits = sum(1 for w in NEG_EMO if w in lc)
    pos_hits = sum(1 for w in POS_EMO if w in lc)
    has_turning = bool(RE_TURNING.search(txt))
    strong_emotion_shift = (
        (neg_hits > 0 and pos_hits > 0) or
        (has_turning and RE_EMOTION.search(txt))
    )

    metrics = _basic_counts(txt)
    notice_like = _is_notice_like(txt, metrics)

    def add(t: str, fit: float, reason: str, hint: str = "-"):
        if t not in allowed_types:
            return
        cands.append({
            "type": t,
            "fit": float(max(0.0, min(1.0, fit))),
            "reason": reason[:120],
            "prep_hint": hint,
        })
    # 공지/안내문: RC27 최우선, RC28 보조
    if notice_like:
        add(
            "RC27",
            0.90,
            "공지/안내문: 다수의 사실·조건·기간·요금 정보 나열",
            "표·조건을 그대로 선지로 옮겨 사실 여부 판단"
        )
        add(
            "RC28",
            0.80,  # ★ 0.72 → 0.80 정도로 상향
            "공지/안내문: 일부 적절한 내용 선택 가능",
            "전체 안내와 어울리는 내용 1개만 고르기"
        )
    elif RE_NOTICE_KEYS.search(txt):
        add("RC27", 0.85, "공지/안내문 섹션 키 검출", "섹션 유지, 사실 검증 포인트 표시")
        add("RC28", 0.80, "공지/안내문 섹션 키 검출", "정합 사실 1개만 맞게 옵션 구성")

    if RE_INSERT_PARENS.search(txt):
        add("RC38", 0.90, "( ① )~( ⑤ ) 삽입 포인트 패턴", "담화표지/지시어 연결성 검사")
        add("RC39", 0.85, "( ① )~( ⑤ ) 삽입 포인트 패턴(고난도)", "전후 논리 심층 점검")

    if RE_NUM_BULLETS.search(txt) and RE_UNDERLINE.search(txt):
        rc29_ok = _llm_rc29_feasible(txt)
        add("RC29",
            0.88 if rc29_ok else 0.50,
            "①~⑤ + <u>…</u> 패턴" + (" (사전판정: 가능)" if rc29_ok else " (사전판정: 불확실)"),
            "문법/구문 오류 1개 탐지")
        add("RC30", 0.80, "①~⑤ + <u>…</u> 패턴", "어휘/콜로케이션 부적절 1개 탐지")

    if RE_NUM_BULLETS.search(txt) and not RE_UNDERLINE.search(txt):
        rc29_ok = _llm_rc29_feasible(txt)
        if rc29_ok:
            add("RC29", 0.70, "①~⑤ 번호만 감지: 문법 판단 기본형 (사전판정: 가능)", "수일치/시제/관계사/준동사 점검")
        else:
            add("RC29", 0.45, "①~⑤ 번호만 감지 (사전판정: 불확실)", "수일치/시제/관계사/준동사 점검")

    try:
        has_bullets = bool(RE_NUM_BULLETS.search(txt))
        has_insert_mark = bool(RE_INSERT_PARENS.search(txt))
        has_underline = bool(RE_UNDERLINE.search(txt))

        # 1) LLM 패스스루용 RC21 (기존 로직 유지, 조건은 그대로)
        if FORCE_RC21_PASS and not has_bullets and not has_insert_mark:
            add(
                "RC21",
                0.55,
                "패스스루: LLM 검증용 후보(형식 신호 약함)",
                "문맥 속 표현의 의미를 추론하는 연습",
            )

        # 2) 의미/비유 기반 RC21 스코어링 (★ 형식이 있어도 평가)
        rc21_score = _score_rc21_semantic(
            txt,
            has_bullets=has_bullets,
            has_underline=has_underline,
            has_insert_mark=has_insert_mark,
        )

        if rc21_score >= 0.60:
            # 강한 비유/관용 신호
            fit = 0.78 if not (has_bullets or has_underline or has_insert_mark) else 0.70
            add(
                "RC21",
                fit,
                "관용/비유 표현 강한 신호 감지",
                "핵심 비유/관용 표현이 문맥에서 무엇을 뜻하는지 설명해 보기",
            )
        elif rc21_score >= 0.45:
            # 중간 정도의 비유/관용 신호
            fit = 0.68 if not (has_bullets or has_underline or has_insert_mark) else 0.60
            add(
                "RC21",
                fit,
                "관용/비유 표현 신호 감지",
                "문장 전체 의미 속에서 표현이 맡는 역할을 정리하는 연습",
            )

    except Exception:
        pass

    if RE_CIRCLED.search(txt) and RE_INLINE_LEX.search(txt):
        add("RC30", 0.65, "①~⑤ 뒤 단일/짧은 어휘 후보", "문맥/콜로케이션 불일치 탐지")

    sem30 = _score_rc30_semantic(txt)
    if sem30 >= 0.35:
        add("RC30", sem30, "형식 없이 어휘·뉘앙스·콜로케이션 단서", "문맥상 어휘 적합성 점검")
        
    sem29 = _score_rc29_semantic(txt)
    if sem29 >= 0.30:
        add("RC29", sem29, "형식 없이 문법 메타 단서", "시제/수일치/전치사/관사 등 점검")

    struct29 = _score_rc29_structure(txt)
    if struct29 >= 0.35 and "RC29" in allowed_types:
        if (not notice_like) and (not RE_BIO.search(txt)) and (not strong_emotion_shift):
            rc29_ok = False
            if 80 <= tokens <= 220:
                rc29_ok = _llm_rc29_feasible(txt)

            if rc29_ok:
                fit = max(struct29, 0.62)
                reason = "형식 신호 없이도 문장 구조만으로 RC29(어법 판단) 출제가 가능(LLM 사전판정: 가능)"
            else:
                fit = struct29
                reason = "형식 신호는 없지만, 관계사/종속절 등 문법 포인트가 많은 설명문"

            add(
                "RC29",
                fit,
                reason,
                "관계사, 수일치, 시제, 분사구 등 문법 포인트 5곳을 골라 1곳만 틀리게 만드는 연습",
            )

    sent_cnt = max(1, len(re.findall(r"[.!?]+(?:\s|$)", txt)))
    if (RE_CHARTY.search(txt) or RE_TABLEY.search(txt)) and sent_cnt >= 5:
        add(
            "RC25",
            0.78,
            "표·그래프/통계 수치를 설명하는 지문(문장 5개 이상)",
            "지문 속 문장 5개를 그대로 선지로 써서 사실 판단 연습"
        )

    # --- RC26: 전기형(개인 생애) 지문만 강하게 추천 ---
    if RE_BIO.search(txt):
        # 첫 문장 기준으로 '집단/민족/문화 설명문'인지 가볍게 필터
        first_sent = re.split(r"[.!?]", txt, 1)[0]
        is_group_like = bool(re.search(
            r"\b(ethnic group|people|tribe|nation|society|community|culture)\b",
            first_sent,
            re.I,
        ))

        # 인칭대명사(he/she/his/her) 또는 고유명사(인명) 다수 + 연도 정보가 있으면 개인 전기로 본다.
        pron_hits = len(re.findall(r"\b(he|she|his|her)\b", txt, re.I))
        year_hits = len(re.findall(r"\b(18|19|20)\d{2}\b", txt))
        metrics = _basic_counts(txt)
        proper_hits = metrics.get("proper_like", 0)

        if (not is_group_like) and year_hits >= 1 and (pron_hits >= 1 or proper_hits >= 2):
            # ✅ 전형적인 '개인 전기'로 판정되는 경우에만 RC26을 강하게 추가
            add(
                "RC26",
                0.82,  # 이전 0.76 → 약간 상향
                "개인 전기: 출생·경력·연대기적 사건 나열",
                "연대표·생애 사건을 시간 순서대로 정리하는 연습"
            )
        # else:
        #   - RE_BIO는 잡혔으나 집단/문화 설명에 가깝거나 연대기/개인성이 약한 경우
        #   - RC26은 규칙 기반에서는 추가하지 않고, LLM 쪽에서만 (있다면) 약하게 작동
    if "RC35" in allowed_types:
        if _looks_rc35_expository_flow(txt, metrics, strong_emotion_shift):
            add(
                "RC35",
                0.72,  # 중간 이상 fit: 항상 후보에 보이도록
                "5문장 이상 단일 주제 설명문: RC35(무관한 문장 찾기) 출제 가능",
                "여러 문장 중 전체 흐름과 가장 어울리지 않는 문장을 고르는 연습",
            )

    if RE_ARGUMENT.search(txt):
        add("RC20", 0.70, "당위/권고 표현 감지", "주장·근거·반론 구조")

    #  RC19 – 감정 단어만 있을 때 vs 명확한 심경 변화일 때 구분
    if RE_EMOTION.search(txt):
        if strong_emotion_shift:
            add(
                "RC19",
                0.80,
                "부정/긍정 감정 + 전환 표현이 함께 나타나는 서사문",
                "초기·전환·최종 정서를 시간 순서대로 정리",
            )
        else:
            add(
                "RC19",
                0.60,
                "정서 어휘 감지",
                "초기·전환·최종 정서를 구분해 보는 연습",
            )

    abc_class = _classify_abc_for_rc36_37(txt, metrics, strong_emotion_shift)

    if abc_class == "RC36":
        add(
            "RC36",
            0.72,
            "(A)(B)(C) 라벨 + 설명문 구조: RC36(단락 순서 배열) 적합",
            "담화표지/지시어를 이용해 (A)(B)(C)의 자연스러운 순서를 추론",
        )
    elif abc_class == "RC37":
        add(
            "RC37",
            0.72,
            "(A)(B)(C) 라벨 + 연구/실험 또는 비정형 구조: RC37 적합",
            "가설-방법-결과/조건별 결과·해석 구조를 파악해 문장 위치·역할을 추론",
        )
    # "none"이면 RC36/RC37 둘 다 추천하지 않음
   # --- NEW: '깨끗한' 설명문에서의 RC38(문장 삽입) 후보 ---

   # --- NEW: '깨끗한' 설명문에서의 RC38(문장 삽입) 후보 ---
    if "RC38" in allowed_types and not RE_INSERT_PARENS.search(txt):
       if _looks_rc38_insertion_friendly(txt, metrics, strong_emotion_shift, notice_like):
           add(
               "RC38",
               0.72,
               "삽입표시가 없지만 전환/pivot 문장이 있는 설명문: RC38(문장 삽입) 출제 가능",
               "중간의 전환 문장이 어느 위치에 들어가야 글 흐름이 가장 자연스러운지 판단하는 연습",
           )
 
    # --- NEW: '깨끗한' 논증/비유 지문에서의 RC39(고난도 문장 삽입) 후보 ---
    if "RC39" in allowed_types and not RE_INSERT_PARENS.search(txt):
        if _looks_rc39_argument_insertion(txt, metrics, strong_emotion_shift, notice_like):
            add(
                "RC39",
                0.74,
                "비유/논증 전개 중간에 meta 문장이 들어가는 삽입형: RC39(고난도 문장 삽입) 출제 가능",
                "어디에서 논증의 방향이 바뀌거나 비유·비교가 깨지는지 판단하는 연습",
            )


    if RE_LOWER_PARENS.search(txt):
        add("RC41", 0.72, "(a)(b)(c) 소문자 라벨 감지: 세트형 적합", "문단별 핵심·연결관계 파악")
        add("RC42", 0.70, "(a)(b)(c) 소문자 라벨 감지: 세트형(고난도)", "세부 추론·상세 대조")

    set_scores = _score_set_signals(txt)
    if "RC41" in allowed_types and set_scores["rc41"] > 0.0:
        add("RC41", 0.60 + set_scores["rc41"], "(a)(b)(c)/Part/Section/참조 표지: 세트형(1)", "문단간 관계·핵심 파악")
    if "RC42" in allowed_types and set_scores["rc42"] > 0.0:
        add("RC42", 0.58 + set_scores["rc42"], "(a)(b)(c)/Part/Section/참조 표지: 세트형(2)", "세부 추론·대조/비교")

    if tokens >= 90 and not (RE_NOTICE_KEYS.search(txt) or RE_BIO.search(txt)) and not strong_emotion_shift:
        # 설명/분석 담화: 제목/주제/요지 + 빈칸/요약 계열
        add("RC24", 0.86, "설명/분석 담화: 제목 추론", "전체 흐름을 한 문구로 압축해 보는 연습")
        add("RC23", 0.84, "설명/분석 담화: 주제 파악", "글이 설명하는 핵심 개념을 한 문장으로 정리")
        add("RC22", 0.80, "설명/분석 담화: 요지 파악", "필자의 전체 주장·메시지를 정리")

        # ✅ RC31은 '핵심 개념 단어 빈칸'을 넣기 좋은 설명문에서만 주입
        if _looks_rc31_blank_friendly(txt, metrics):
            add("RC31", 0.84, "핵심 개념 단어 빈칸 적합", "핵심 명사구 위치에 '_____'")

        add("RC32", 0.78, "구/절 수준 빈칸 추론 가능", "원인-결과/전환 지점 공백")
        rc33_fit = 0.74
        if _looks_rc33_high_level(txt, metrics):
            rc33_fit = 0.84  # 기출 RC33 전형 패턴이면 좀 더 강하게
        add("RC33", rc33_fit, "고난도 구/절 빈칸", "요약/전환 절 수준")
        rc34_fit = 0.0
        if _looks_rc34_global_blank(txt, metrics):
            # 전형적인 RC34 패턴: 장문 + pivot 연결부가 뚜렷한 경우
            rc34_fit = 0.86 if tokens >= 170 else 0.83
        elif tokens >= 150:
            # 길이·구조는 충분히 RC34 후보지만, 패턴 매칭이 약한 경우(보통 난도)
            rc34_fit = 0.78

        if rc34_fit > 0.0:
            add(
                "RC34",
                rc34_fit,
                "장문 설명문: 글 흐름을 바꾸거나 인과를 잇는 구/절에 고난도 빈칸 가능",
                "첫·마지막 문장을 제외한 중간부 전환·인과 연결 절/구를 빈칸으로 생각해 보기",
            )

        # ★ RC40: '두 측면으로 요약 가능한' 설명문이면 더 강하게 추천
        rc40_fit = 0.72
        if _looks_rc40_ab_summary(txt, metrics):
            rc40_fit = 0.86 if tokens >= 150 else 0.83
        add(
            "RC40",
            rc40_fit,
            "핵심 개념을 (A)(B) 두 명사구로 압축 가능한 설명문",
            "(A)(B)에 들어갈 서로 다른 측면(문제/해결, 한계/보완, 원인/결과 등)을 찾아보기",
        )

    if tokens >= 220:
        add("RC41", 0.62, "설명문: 세트형(1) 후보(장문 조건 충족)", "-")
        add("RC42", 0.60, "설명문: 세트형(2) 후보(장문 조건 충족)", "-")

    # RC18: 편지/메일/공지 + 목적 표현 기반 후보 추가
    has_letter = bool(RE_LETTER_DEAR.search(txt) or RE_LETTER_CLOSE.search(txt))
    has_intent = bool(
        RE_INTENT_REQUEST.search(txt)
        or RE_INTENT_INQUIRY.search(txt)
        or RE_INTENT_GUIDE.search(txt)
        or RE_INTENT_PROMO.search(txt)
    )

    if has_letter:
        base_fit = 0.85 if has_intent else 0.80
        reason = "서신 포맷 + 목적/요청이 분명한 지문" if has_intent else "서신 포맷 감지"
        hint = "편지·이메일에서 작성 의도를 한 문장으로 요약"
        add("RC18", base_fit, reason, hint)
    else:
        # 편지 형식은 아니지만, 짧은 공지/안내 + 명확한 목적일 때도 RC18 후보로 포함
        if has_intent and tokens <= 120 and not (RE_CHARTY.search(txt) or RE_TABLEY.search(txt)):
            add(
                "RC18",
                0.70,
                "공지/안내문에서 참여·문의 목적이 분명한 지문",
                "문서의 전체 목적을 한 문장으로 정리",
            )

    cands = _inject_evergreen_candidates(cands, txt, allowed_types)

    merged: Dict[str, Dict] = {}
    for c in cands:
        t = c["type"]
        if t not in merged or c["fit"] > merged[t]["fit"]:
            merged[t] = c

    _apply_final_table_boosts(merged, txt)

    for t in list(merged.keys()):
        if t not in allowed_types:
            merged.pop(t, None)

    cands = sorted(merged.values(), key=lambda x: x["fit"], reverse=True)
    cands = _collapse_set_groups(cands)
    return cands[:12]
