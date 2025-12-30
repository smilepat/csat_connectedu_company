# app/specs/passage_preprocessor.py
from __future__ import annotations
import re
from typing import Tuple
from app.services.llm_client import call_llm_json

_CIRCLED = "①②③④⑤"
_RE_CIRCLED = re.compile(r"[{}]".format(_CIRCLED))
_RE_CIRCLED_PAREN = re.compile(r"\(\s*[①②③④⑤]\s*\)")
_RE_UNDERLINE_TAG = re.compile(r"</?(u|ins)\b[^>]*>", re.IGNORECASE)
_RE_SPAN_UNDERLINE = re.compile(
    r"<span\b[^>]*style=['\"][^'\"]*text-decoration\s*:\s*underline[^'\"]*['\"][^>]*>", re.IGNORECASE
)
_RE_SPAN_CLOSE = re.compile(r"</span\s*>", re.IGNORECASE)
_RE_HTML_TAGS_TO_STRIP = (_RE_UNDERLINE_TAG, _RE_SPAN_UNDERLINE, _RE_SPAN_CLOSE)

# 빈 밑줄: 연속 '_' 3개 이상은 BLANK 토큰으로 잡아둠(후단에서 채움)
_RE_BLANK_UNDERSCORE = re.compile(r"_{3,}")

# 사례: "①reflects", "② informative"
# → 마커 삭제(단어는 보존), 나중에 LLM이 틀린 후보 1개만 바꿔줌
_RE_INLINE_MARKED_WORD = re.compile(
    r"([①②③④⑤])\s*([^\s)»”\"',.;:()]+(?:\s+[^\s)»”\"',.;:()]+){0,6})?"
)

def sanitize_passage_markup(text: str) -> Tuple[str, dict]:
    """
    1) 밑줄 형식 제거(텍스트 보존)
    2) ①~⑤ 마커 삭제
    3) 빈 밑줄(____)은 <<BLANK_n>>로 치환
    4) 통계(마커-후보) 수집: LLM 힌트로 보냄
    """
    original = text

    # 1) 밑줄 태그 제거(텍스트 보존)
    for pat in _RE_HTML_TAGS_TO_STRIP:
        text = pat.sub(lambda m: "" if m.re is _RE_SPAN_CLOSE else "", text)
    # 위에서 태그만 제거했으므로 <span ... underline>text</span> → "text"

    # 2) (①) 형태도 제거
    text = _RE_CIRCLED_PAREN.sub("", text)

    # 3) ①~⑤ + 인접 어절 통계 수집 (후보 사전)
    candidates = []  # e.g., [{"mark":"①","phrase":"reflects"}, ...]
    def _collect(m):
        mark = m.group(1)
        phrase = (m.group(2) or "").strip()
        if phrase:
            candidates.append({"mark": mark, "phrase": phrase})
        # 마커만 삭제, phrase는 그대로 남김
        return phrase

    text = _RE_INLINE_MARKED_WORD.sub(_collect, text)

    # 4) 남아있는 마커 단독 삭제(안전망)
    text = _RE_CIRCLED.sub("", text)

    # 5) 빈 밑줄을 BLANK 토큰으로
    blank_idx = 0
    def _blank(m):
        nonlocal blank_idx
        blank_idx += 1
        return f"<<BLANK_{blank_idx}>>"
    text = _RE_BLANK_UNDERSCORE.sub(_blank, text)

    # 공백 정돈
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text, {"candidates": candidates, "blank_count": blank_idx, "original": original}


def repair_semantics_with_llm(clean_text: str, meta: dict) -> str:
    """
    LLM에 지시:
    - candidates 중 문맥상 틀린 1개만 교체(나머지는 그대로)
    - <<BLANK_n>> 토큰은 문맥/문법 맞게 채우기
    - ①~⑤ 등 마커는 이미 제거됨. 반환은 JSON {"passage": "..."} ONLY
    """
    # 후보와 BLANK 개수를 프롬프트에 힌트로 제공
    cand_preview = "; ".join([f'{c["mark"]}:{c["phrase"]}' for c in meta.get("candidates", [])]) or "-"
    blank_count = meta.get("blank_count", 0)

    system = (
        "You are a careful English editor for CSAT passages.\n"
        "TASK:\n"
        "1) Exactly ONE of the previously marked candidates (①~⑤) was wrong. Replace ONLY that one with a contextually and grammatically correct alternative.\n"
        "2) Fill every placeholder token <<BLANK_n>> with a suitable word/phrase/sentence that fits the context and grammar.\n"
        "3) Do NOT add or remove other content. Keep length and meaning as close as possible to the original, aside from the required fixes.\n"
        "4) Output JSON ONLY, no code fences: {\"passage\": \"...\"}\n"
        "5) Do NOT re-introduce any ①~⑤ or placeholder tokens.\n"
    )

    user = (
        f"PASSAGE (markers removed, placeholders present):\n{clean_text}\n\n"
        f"Candidates previously marked (for your reference): {cand_preview}\n"
        f"Number of placeholders to fill: {blank_count}\n"
        'Return JSON only: {"passage": "<final fixed passage>"}'
    )

    out = call_llm_json(system=system, user=user, temperature=0.0, max_tokens=2000)
    # 안전망
    fixed = out.get("passage") if isinstance(out, dict) else None
    if not fixed or not isinstance(fixed, str):
        # 실패 시 최소한 placeholder만 제거
        fixed = re.sub(r"<<BLANK_\d+>>", "", clean_text).strip()
    return fixed


def retarget_for_item(item_id: str, passage: str, fill_mode: str = "erase") -> str:
    """
    item_pipeline.build_ctx_for_custom에서 호출됨.
    - 규칙(1)(2)(3)을 항상 적용
    - fill_mode는 일단 유지(향후 'fill_copy' 등 확장 여지), 현재는 'erase'만 사용
    """
    clean_text, meta = sanitize_passage_markup(passage)
    fixed = repair_semantics_with_llm(clean_text, meta)
    return fixed

def sanitize_user_passage(passage: str, *, strip_circled: bool = True, strip_underlines: bool = True) -> str:
    """
    Backwards-compat wrapper.
    현재 구현은 ①~⑤ / ( ① ) / <u>…</u> 등 표식을 제거하고 공백/언더스코어 치환을 적용한
    sanitized 텍스트를 리턴합니다. (LLM 치유는 하지 않음)
    """
    clean_text, _meta = sanitize_passage_markup(passage or "")
    return clean_text

def strip_annotations_for_rc29_30(passage: str) -> str:
    """
    Backwards-compat wrapper used by earlier RC29/RC30 patches.
    표식만 제거한 텍스트를 리턴 (LLM 치유는 하지 않음).
    """
    clean_text, _meta = sanitize_passage_markup(passage or "")
    return clean_text
