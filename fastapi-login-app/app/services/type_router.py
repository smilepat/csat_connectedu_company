# app/services/type_router.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple

from app.services.llm_client import call_llm_json
from app.prompts.router_prompt import get_router_system, get_router_user
from app.services.routing_rules import (
    rule_based_candidates,
    _length_band,          # ← 길이 밴드 판정 함수 사용
    ALLOW_BY_LENGTH,       # ← 밴드별 허용 유형 집합
)

def _normalize_llm_candidates(raw: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    """
    LLM 라우터 응답을 안전하게 정규화.
    - raw 가 None / ok=False / 구조 불일치여도 빈 리스트 반환.
    - type은 'RC'로 시작하는 것만 허용.
    - fit ∈ [0, 1] 만 수용.
    """
    out: List[Dict[str, Any]] = []
    if not isinstance(raw, dict):
        return out
    # ok=False 면 사용하지 않음
    if raw is not None and raw.get("ok") is False:
        return out

    for c in raw.get("candidates", []) or []:
        try:
            t = str(c.get("type", "")).strip()
            if not (t and t.startswith("RC")):
                continue
            fit = float(c.get("fit", 0.0))
            if not (0.0 <= fit <= 1.0):
                continue
            reason = str(c.get("reason", ""))[:200]
            hint = (str(c.get("prep_hint", "")).strip() or "-")[:200]
            out.append({"type": t, "fit": fit, "reason": reason, "prep_hint": hint})
        except Exception:
            continue
    return out


def _merge_candidates(a: List[Dict], b: List[Dict]) -> List[Dict]:
    """
    a: LLM 후보, b: 규칙 후보
    LLM 55%, 규칙 45% 가중 병합.
    - 동일 type 은 가중합/최대치/문구 보강으로 통합
    - 다중 출처 합의(_votes>=2) 시 소폭 가점(+0.08, 상한 1.0)
    """
    merged: Dict[str, Dict] = {}

    def _add(src: List[Dict], weight: float):
        for c in src:
            t = c["type"]
            if t not in merged:
                merged[t] = {
                    "type": t,
                    "fit": float(c.get("fit", 0.0)) * weight,
                    "reason": str(c.get("reason", ""))[:200],
                    "prep_hint": (str(c.get("prep_hint", "")).strip() or "-")[:200],
                    "_votes": 1,
                    "_max": float(c.get("fit", 0.0)),
                }
            else:
                merged[t]["fit"] += float(c.get("fit", 0.0)) * weight
                merged[t]["_votes"] += 1
                merged[t]["_max"] = max(merged[t]["_max"], float(c.get("fit", 0.0)))
                # 더 짧고 명료한 reason 을 선호
                cur_r, nxt_r = merged[t].get("reason", ""), str(c.get("reason", ""))[:200]
                if nxt_r and (not cur_r or len(nxt_r) < len(cur_r)):
                    merged[t]["reason"] = nxt_r
                # prep_hint 는 비어 있으면 대체
                if (merged[t].get("prep_hint", "-") == "-") and (c.get("prep_hint", "-") != "-"):
                    merged[t]["prep_hint"] = (str(c.get("prep_hint", "")).strip() or "-")[:200]

    _add(a, 0.55)  # LLM
    _add(b, 0.45)  # 규칙

    for t, c in merged.items():
        # 다중 출처 합의 시 가점
        if c["_votes"] >= 2:
            c["fit"] = min(1.0, c["fit"] + 0.08)

        # NEW: RC19는 심경 변화 전용 유형이므로 소폭 추가 가점
        if t == "RC19":
            c["fit"] = min(1.0, c["fit"] + 0.03)

        c["fit"] = round(float(min(1.0, c["fit"])), 4)
        c.pop("_votes", None)
        c.pop("_max", None)
        # ★ 안내문 페어 보정: RC27이 있으면 RC28도 너무 뒤로 밀리지 않게 조정
        if "RC27" in merged and "RC28" in merged:
            r27 = merged["RC27"]["fit"]
            r28 = merged["RC28"]["fit"]

            # RC28 점수를 RC27 바로 아래(최대 0.08 차이)까지 끌어올리기
            if r28 < r27 - 0.08:
                merged["RC28"]["fit"] = round(min(1.0, r27 - 0.08), 4)        

        

    return sorted(merged.values(), key=lambda x: x["fit"], reverse=True)


def _llm_candidates(passage: str) -> List[Dict[str, Any]]:
    """
    LLM 호출 실패/파싱 실패/정책 실패 시에도 빈 리스트로 안전 반환.
    """
    system = get_router_system()
    user = get_router_user(passage)
    raw = call_llm_json(system=system, user=user, temperature=0.2, max_tokens=600)
    return _normalize_llm_candidates(raw)


def _filter_by_length_gate(passage: str, cands: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """
    ★ 최종 출력 전 길이 우선 게이트 강제 ★
      - ≤150 → ALLOW_BY_LENGTH['upto_rc33']만 허용
      - 151–199 → ALLOW_BY_LENGTH['upto_rc40']만 허용
      - ≥200 → ALLOW_BY_LENGTH['rc41_plus']만 허용
    반환: (band, filtered_candidates)
    """
    tokens = len((passage or "").split())
    band = _length_band(tokens)
    allowed = ALLOW_BY_LENGTH.get(band, ALLOW_BY_LENGTH["upto_rc33"])
    return band, [c for c in cands if c.get("type") in allowed]


def suggest_types(passage: str, top_k: int = 5) -> Dict[str, Any]:
    """
    규칙 후보 + LLM 후보 병합 후, 길이 게이트로 최종 제한.
    - 게이트 결과가 비면 완화 폴백: 게이트 미적용 상위 N 반환(서비스 일관성 목적)
    """
    # 1) 규칙 기반
    rule_cands = rule_based_candidates(passage)
    # 2) LLM 라우터
    llm_cands = _llm_candidates(passage)
    # 3) 병합/정렬
    merged = _merge_candidates(llm_cands, rule_cands)
    # 4) 길이 게이트
    band, gated = _filter_by_length_gate(passage, merged)

    # 게이트가 너무 엄격해 전부 소거될 때의 폴백(운영 안정성)
    final = gated
    gate_applied = True
    if not final:
        final = merged  # 게이트 미적용 상위 후보로 폴백
        gate_applied = False

    k = max(1, min(5, int(top_k or 5)))
    top = [c["type"] for c in final[:k]]

    return {
        "ok": True,
        "meta": {
            "band": band,
            "gate_applied": gate_applied,
            "tokens": len((passage or "").split()),
            "sources": {"llm": len(llm_cands), "rule": len(rule_cands)},
        },
        "candidates": final,
        "top": top,
    }
