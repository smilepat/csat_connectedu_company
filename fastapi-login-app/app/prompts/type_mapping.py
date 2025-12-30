# app/prompts/type_mapping.py
from __future__ import annotations
import re
from typing import Optional, Set

# 디버그 토글 (원하면 환경변수로 관리해도 됩니다)
DEBUG_TM = True
def _dtm(msg: str) -> None:
    if DEBUG_TM:
        print(f"[type_mapping] {msg}")

# 허용 번호형 RC 코드: RC18~RC40 (단일형만 그대로 통과)
_ALLOWED_RC: Set[str] = {f"RC{i:02d}" for i in range(18, 41)}  # RC18~RC40

# 세트 범위 표기 정규식: RC##_## 또는 RC##-##
_RC_SET_RANGE_RE = re.compile(r"^RC\d{2}[_-]\d{2}$")
_RC_NUMERIC_RE   = re.compile(r"^RC(\d{2})$")

# UI에서 보내는 상위 타입 → 실제 ITEM_PROMPTS의 키 (프롬프트 id)
# ※ RC_TITLE은 제목 유형이므로 RC24로 매핑
TYPE_TO_ITEM_ID: dict[str, str] = {
    # 목적/요지/주제/제목/요약 등
    "RC_PURPOSE": "RC18",
    "RC_EMOTION": "RC19",
    "RC_ARGUMENT": "RC20",
    "RC_INFERENCE": "RC21",
    "RC_SUMMARY": "RC22",   # 요약문 완성은 RC40 별도
    "RC_TITLE":   "RC24",   # 제목 → RC24

    # 불일치/일치/차트
    "RC_CHART":           "RC25",
    "RC_MISMATCH":        "RC26",
    "RC_NOTICE_MISMATCH": "RC27",
    "RC_NOTICE_MATCH":    "RC28",

    # 문법/어휘
    "RC_GRAMMAR": "RC29",
    "RC_VOCAB":   "RC30",

    # 빈칸 계열: 대표로 RC34 사용 (31~34 중 하나 선택)
    "RC_BLANK": "RC34",

    # 무관한 문장
    "RC_IRRELEVANT": "RC35",

    # 순서/삽입
    "RC_ORDER":     "RC36",   # RC37도 가능
    "RC_INSERTION": "RC38",   # RC39도 가능

    # 세트 문항
    "RC_SET": "RC41_42",      # 고급 세트는 아래 후보에서 자동 선택
    # 필요 시 "RC_SET_ADV": "RC43_45" 추가 가능
}

# 보조: 세트 계열 자동 확장 후보 (존재하는 키 우선)
SET_ITEM_CANDIDATES = ["RC41_42", "RC43_45"]


def _first_existing(cands: list[str], keys: Optional[Set[str]]) -> Optional[str]:
    if not cands:
        return None
    if not keys:
        return cands[0]
    for c in cands:
        if c in keys:
            return c
    return None


def resolve_item_id_from_type(
    item_type: str | None,
    *,
    prefer_set: str | None = None,        # "RC41_42" 또는 "RC43_45"를 선호할 때
    item_prompts_keys: Set[str] | None = None,
) -> str:
    """
    UI/라우터가 보낸 타입을 실제 프롬프트 id(item_id)로 변환.

    우선순위/규칙:
      0) 세트 코드("RC41_42","RC43_45")는 그대로 통과 (패스스루)
      1) 숫자형 RC: 
         - RC18~RC40 → 그대로 사용
         - RC41/RC42 → RC41_42로 승격 (세트 프롬프트 사용)
         - RC43/RC44/RC45 → RC43_45로 승격
      2) 세트 범위("RC41-42","RC43_45") → 존재 확인 후 선택
      3) 캐논키(예: "RC_BLANK","RC_ORDER") → 숫자/세트 매핑
      4) 최종 폴백: RC34
    """
    if not item_type:
        return "RC34"

    code = item_type.upper().strip()
    _dtm(f"resolve in: {code!r}")

    # 0) 세트 코드는 그대로 패스스루
    if code in {"RC41_42", "RC43_45"}:
        _dtm(f"pass-through set code: {code}")
        return code

    # 1) 숫자형 처리
    m = _RC_NUMERIC_RE.match(code)
    if m:
        n = int(m.group(1))
        # RC18~RC40 → 단일형 그대로
        if 18 <= n <= 40:
            _dtm(f"numeric single kept: RC{n:02d}")
            return code
        # RC41/RC42 → RC41_42 승격
        if n in (41, 42):
            if item_prompts_keys and "RC41_42" not in item_prompts_keys:
                _dtm("promote RC41/42 -> RC41_42 (ITEM_PROMPTS missing), fallback to RC34")
                return "RC34"
            _dtm("promote RC41/42 -> RC41_42")
            return "RC41_42"
        # RC43/RC44/RC45 → RC43_45 승격
        if n in (43, 44, 45):
            if item_prompts_keys and "RC43_45" not in item_prompts_keys:
                _dtm("promote RC43/44/45 -> RC43_45 (ITEM_PROMPTS missing), fallback to RC34")
                return "RC34"
            _dtm("promote RC43/44/45 -> RC43_45")
            return "RC43_45"
        # 그 외 번호는 지원 안 함 → 폴백
        _dtm(f"unsupported numeric RC{n:02d} → fallback RC34")
        return "RC34"

    # 2) 세트 범위 코드 그대로 들어오는 경우 ("RC41-42", "RC43_45" 등)
    if _RC_SET_RANGE_RE.match(code):
        if item_prompts_keys and code in item_prompts_keys:
            _dtm(f"direct set-range hit: {code}")
            return code
        # 존재하지 않으면 후보에서 선택
        cands: list[str] = []
        if prefer_set:
            cands.append(prefer_set)
        cands.extend([c for c in SET_ITEM_CANDIDATES if c != prefer_set])
        chosen = _first_existing(cands, item_prompts_keys)
        _dtm(f"set-range fallback choose: {chosen or 'RC41_42'}")
        return chosen or "RC41_42"

    # 3) 캐논키 매핑 (존재 확인)
    mapped = TYPE_TO_ITEM_ID.get(code)
    if mapped:
        # 매핑 결과가 prompt에 없으면 세트 후보로 대체
        if item_prompts_keys and mapped not in item_prompts_keys:
            if code in ("RC_SET", "RC_SET_ADV", "RC_LONGSET"):
                cands: list[str] = []
                if prefer_set:
                    cands.append(prefer_set)
                cands.extend([c for c in SET_ITEM_CANDIDATES if c != prefer_set])
                chosen = _first_existing(cands, item_prompts_keys)
                _dtm(f"canon '{code}' -> mapped '{mapped}' missing, choose set: {chosen or 'RC41_42'}")
                return chosen or "RC41_42"
        _dtm(f"canon '{code}' -> mapped '{mapped}'")
        return mapped

    # 4) 이미 구체 ITEM_PROMPTS 키를 직접 받은 경우 (예: "RC22", "RC41_42")
    if item_prompts_keys and code in item_prompts_keys:
        _dtm(f"direct ITEM_PROMPTS hit: {code}")
        return code

    # 5) 최종 폴백
    _dtm("fallback -> RC34")
    return "RC34"
