# app/services/llm_client.py
from __future__ import annotations
import json, re, time, os, traceback, ast
from typing import Any, Dict, Callable, Optional

from app.core.openai_config import chat_completion, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS

DEFAULT_TIMEOUT_S = 30

# 가장 마지막에 닫히는 JSON 객체 후보
# (이전에는 마지막 '{'부터 문자열 끝까지를 잡았지만,
#  실제로는 앞뒤 설명 텍스트가 섞일 수 있어 사용하지 않도록 함)
# _JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}$")

# ``` 또는 ```json 펜스 제거
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.I | re.M)

# 스마트 따옴표 정규화 맵
_SMART_QUOTES = {
    # 큰따옴표 계열은 JSON 문자열을 깨뜨릴 수 있으므로 건드리지 않는다.
    # "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
    # "\u2033": '"',

    # 작은따옴표/프라임 기호만 안전하게 ' 로 정규화
    "\u2018": "'", "\u2019": "'", "\u2032": "'",
}
# 트레일링 콤마 제거( }, ] 직전 )
_RE_TRAILING_COMMA = re.compile(r",\s*([}\]])")

_CIRCLED = "①②③④⑤"

DEBUG_LLM = os.getenv("DEBUG_LLM", "1").lower() in ("1", "true", "yes", "on")

# ✅ 개행(\n), 캐리지리턴(\r), 탭(\t) 포함 모든 제어문자 제거
CONTROL_CHARS_RE = re.compile(r'[\x00-\x1F]')


def _strip_code_fences(txt: str) -> str:
    return _FENCE_RE.sub("", txt or "").strip()


def _normalize_quotes(s: str) -> str:
    for k, v in _SMART_QUOTES.items():
        s = s.replace(k, v)
    return s


def strip_control_chars(s: str) -> str:
    try:
        return CONTROL_CHARS_RE.sub(' ', s or '')
    except Exception:
        return s or ''


def strip_controls_deep(obj):
    """dict/list 내 모든 str 필드에서 제어문자 제거"""
    if isinstance(obj, dict):
        return {k: strip_controls_deep(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [strip_controls_deep(v) for v in obj]
    if isinstance(obj, str):
        return strip_control_chars(obj)
    return obj


def _quote_bare_circled(s: str) -> str:
    """
    문자열 바깥에 단독으로 존재하는 ①~⑤를 "①"처럼 감싼다.
    - JSON 문자열 내부는 건드리지 않기 위해 간단한 상태머신 사용.
    """
    out = []
    in_str = False
    esc = False
    for ch in s:
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue
        else:
            if ch == '"':
                in_str = True
                out.append(ch)
                continue
            if ch in _CIRCLED:
                out.append(f'"{ch}"')
            else:
                out.append(ch)
    return "".join(out)


def _extract_outer_json_block(s: str) -> str:
    """
    - 문자열이 곧바로 JSON이면 그대로 반환
    - 아니면 본문 안에서 JSON 객체 부분만 추출:
      · 첫 '{'부터 마지막 '}'까지를 잘라낸다.
      · 둘 다 없으면 에러.
    """
    s = s.strip()
    # 바로 로드 가능한지 1차 시도
    try:
        json.loads(s)
        return s
    except Exception:
        pass

    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response.")
    return s[start : end + 1]


def _preclean_jsonish(raw: str) -> str:
    """
    모델 응답(JSON스러움)을 파싱하기 전에 안전하게 정리:
      1) 코드펜스 제거
      2) 스마트 따옴표 → 표준 따옴표
      3) 문자열 바깥의 ①~⑤ 를 강제로 따옴표로 감싸기
      4) 트레일링 콤마 제거
      5) 가장 바깥 { ... } 블록 추출
    """
    s = _strip_code_fences(raw)
    s = _normalize_quotes(s)
    s = _quote_bare_circled(s)
    s = _RE_TRAILING_COMMA.sub(r"\1", s)
    s = _extract_outer_json_block(s)
    return s


def _extract_json(txt: str) -> Dict[str, Any]:
    """
    모델이 설명 + JSON을 섞어 보낼 때, 본문에서 JSON만 안전하게 추출.
    강화 포맷터를 통해 흔한 파싱 실패 요인을 제거.
    """
    s = _preclean_jsonish(txt or "")

    # 1차: 표준 JSON 파싱 시도
    try:
        return json.loads(s)
    except Exception as json_err:
        # 2차: Python literal 스타일을 ast.literal_eval로 파싱 시도
        try:
            obj = ast.literal_eval(s)
            # dict 또는 list만 유효한 결과로 인정
            if isinstance(obj, (dict, list)):
                return obj
        except Exception:
            # literal_eval도 실패하면 원래 에러 다시 올리기
            raise json_err
        # literal_eval 성공했지만 타입이 dict/list가 아니면 에러
        raise json_err


def _retry(fn: Callable[[], Dict[str, Any]], retries: int = 2, backoff: float = 0.8) -> Optional[Dict[str, Any]]:
    last = None
    for i in range(retries + 1):
        try:
            return fn()
        except Exception as e:
            last = e
            if DEBUG_LLM:
                # 요약 로그만 남기고, 스택트레이스는 마지막 1회만 선택적으로
                print(f"[call_llm_json] attempt {i+1}/{retries} failed: {e}")
            if i < retries:
                time.sleep(backoff * (i + 1))
    # 🔇 스택트레이스 과다 출력 방지: 필요 시에만
    if DEBUG_LLM and last:
        # print_exception(last)  # ← 주석 처리(혹은 환경변수로 토글)
        print("[call_llm_json] giving up after retries")
    return None


def call_llm_json(
    *,
    system: str,
    user: str,
    temperature: float = 0.3,
    max_tokens: int = 4000,
    trace_id: Optional[str] = None,
    timeout_s: Optional[float] = None,
    retries: int = 2,   # ← 기본 2회 재시도
) -> Dict[str, Any]:
    """
    openai_config.chat_completion()을 감싸 JSON을 반환.
    - Azure/OpenAI/Gemini 모두 openai_config의 설정을 그대로 따릅니다.
    - 모델이 JSON만 반환하지 않아도 본문에서 JSON을 추출합니다.
    - 실패 시 예외 대신 {"ok": False, "candidates": []} 반환(상위 서비스가 폴백 가능).
    """
    def _once() -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        text = chat_completion(
            messages,
            trace_id=trace_id,
            temperature=temperature if temperature is not None else DEFAULT_TEMPERATURE,
            max_tokens=max_tokens if max_tokens is not None else min(DEFAULT_MAX_TOKENS, 1000),
            timeout_s=timeout_s if timeout_s is not None else DEFAULT_TIMEOUT_S,
        )
        # LLM 원문 -> 제어문자 제거 -> JSON 추출기
        raw_text = text or ""
        print("&&&&&&&&&&&&&&&&&&&&&&&&", raw_text)
        clean_text = CONTROL_CHARS_RE.sub(' ', raw_text)
        data = _extract_json(clean_text)          # ✅ 여기서 JSON 파싱 (json.loads → literal_eval 폴백 포함)
        return strip_controls_deep(data)          # ✅ 파싱 결과 정리

    # ✅ 재시도는 바깥 한 군데에서만!
    data = _retry(_once, retries=retries, backoff=0.8)
    if data is None:
        return {"ok": False, "candidates": []}
    if isinstance(data, dict) and "ok" not in data:
        data["ok"] = True
    return data
