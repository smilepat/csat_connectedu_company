# app/specs/utils.py  (기존 파일에 추가)
from typing import List, Dict, Any
import re

ANSWER_MAP = {
    "①":"1","②":"2","③":"3","④":"4","⑤":"5",
    "A":"1","B":"2","C":"3","D":"4","E":"5",
    "a":"1","b":"2","c":"3","d":"4","e":"5",
    "1":"1","2":"2","3":"3","4":"4","5":"5",
}

def standardize_answer(v: Any) -> str:
    s = str(v or "").strip()
    # "정답: ④" 같은 노이즈 제거
    s = re.sub(r"^(정답|answer)\s*[:：]\s*", "", s, flags=re.IGNORECASE)
    return ANSWER_MAP.get(s, s)

def tidy_options(opts: Any) -> List[str]:
    """
    다양한 옵션 표현을 리스트[str] 5개로 노멀라이즈 시도:
      - 리스트[str]
      - 리스트[dict{label/text}]
      - dict {"A": "...", "B": "..."} / {"1":"..."} / {"①":"..."}
      - 문자열 한 덩어리일 때 줄 단위 분해 등
    """
    # 1) dict 형태
    if isinstance(opts, dict):
        # 키를 정렬: 1..5 or A..E or ①..⑤
        ordered = []
        # 키 후보들
        for key_order in [
            ["1","2","3","4","5"],
            ["A","B","C","D","E"],
            ["a","b","c","d","e"],
            ["①","②","③","④","⑤"],
        ]:
            if all(k in opts for k in key_order):
                ordered = [str(opts[k]).strip() for k in key_order]
                break
        if not ordered:
            # 숫자/문자 키 추출 후 정렬 시도
            pairs = list(opts.items())
            pairs.sort(key=lambda kv: str(kv[0]))
            ordered = [str(v).strip() for _, v in pairs]
        xs = [x for x in ordered if x]
        return xs

    # 2) 리스트
    if isinstance(opts, list):
        xs = []
        for o in opts:
            if isinstance(o, dict):
                # {"label":"A","text":"..."} / {"option":"..."} / {"value":"..."}
                cand = o.get("text") or o.get("option") or o.get("value") or ""
                xs.append(str(cand).strip())
            else:
                xs.append(str(o or "").strip())
        xs = [x for x in xs if x]
        return xs

    # 3) 문자열: 줄 단위 분해, 접두 라벨 제거 ("A) ", "① " 등)
    if isinstance(opts, str):
        lines = [ln.strip() for ln in re.split(r"[\r\n]+", opts) if ln.strip()]
        xs = []
        for ln in lines:
            ln = re.sub(r"^(?:[ABCDE①②③④⑤1-5][\)\].:\-]\s*)", "", ln)
            xs.append(ln.strip())
        xs = [x for x in xs if x]
        return xs

    return []

def coerce_mcq_like(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    흔한 별칭/변형 필드명을 표준 필드로 매핑:
      - question: {"question","prompt","stem","질문"}
      - options: {"options","choices","선지","보기","answers"}
      - correct_answer: {"correct_answer","answer","answer_key","정답","correct","label"}
      - rationale: {"rationale","explanation","해설"}
    """
    x = dict(d or {})

    # question
    for k in ["question","prompt","stem","질문","문항","문제"]:
        if k in x and not x.get("question"):
            x["question"] = x.get(k)

    # options
    for k in ["options","choices","선지","보기","answers","answer_choices"]:
        if k in x and not x.get("options"):
            x["options"] = x.get(k)

    # correct_answer
    for k in ["correct_answer","answer","answer_key","정답","correct","label","solution","key"]:
        if k in x and not x.get("correct_answer"):
            x["correct_answer"] = x.get(k)

    # rationale
    for k in ["rationale","explanation","해설","reasoning","analysis"]:
        if k in x and not x.get("rationale"):
            x["rationale"] = x.get(k)

    # 표준화
    x["question"] = str(x.get("question") or "").strip()
    x["options"] = tidy_options(x.get("options"))
    x["correct_answer"] = standardize_answer(x.get("correct_answer"))
    if "rationale" in x:
        x["rationale"] = str(x.get("rationale") or "").strip()

    return x

def strip_code_fence(text: str | None) -> str:
    """
    모델 응답에 종종 붙는 ```json ... ``` 코드 펜스를 제거합니다.
    양 끝의 백틱 블록을 떼고, 남은 본문만 반환합니다.
    """
    if not isinstance(text, str):
        return "" if text is None else str(text)
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        # 첫 줄( ``` 또는 ```json ) 제거
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # 마지막 줄의 ``` 제거
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t
def coerce_transcript(value: Any) -> str:
    """
    다양한 transcript 입력(문자열/배열/객체)을 표준 문자열로 정규화.
    허용 예:
      - "문자열 그대로"
      - ["한 줄", "또 한 줄"]
      - [{"speaker":"M","text":"Hi"}, {"speaker":"W","text":"Hello"}]
      - {"dialogue":[...], "context":"..."} 같은 객체(있으면 dialogue 우선)
    """
    if value is None:
        return ""
    # 이미 문자열
    if isinstance(value, str):
        return value.strip()

    # 배열: 문자열 배열 or 객체 배열(speaker/text)
    if isinstance(value, list):
        lines: list[str] = []
        for it in value:
            if isinstance(it, str):
                lines.append(it.strip())
            elif isinstance(it, dict):
                sp = str(it.get("speaker") or "").strip()
                tx = str(it.get("text") or "").strip()
                if sp and tx:
                    lines.append(f"{sp}: {tx}")
                elif tx:
                    lines.append(tx)
        return "\n".join([ln for ln in lines if ln])

    # 객체: dialogue/lines/utterances 우선, 아니면 문자열 필드 추려서 합침
    if isinstance(value, dict):
        for key in ("dialogue", "lines", "utterances"):
            if isinstance(value.get(key), (list, tuple)):
                return coerce_transcript(value.get(key))
        # fallback: 대표 필드 모아서 텍스트화
        parts = []
        for k in ("speaker", "text", "context", "content"):
            v = value.get(k)
            if isinstance(v, str):
                parts.append(v.strip())
        return "\n".join([p for p in parts if p])

    # 최후: 문자열 캐스팅
    return str(value).strip()
def ensure_dialogue_newlines(text: str) -> str:
    """
    transcript가 한 줄로 붙어 있을 때 화자 태그(M:/W: 등) 앞에 줄바꿈 삽입.
    이미 줄바꿈이 있으면 그대로 둔다.
    """
    if not isinstance(text, str):
        return text
    s = text.strip()
    if "\n" in s:
        return s
    # 공백 정규화
    s = re.sub(r"\s+", " ", s)
    # 화자 태그 세트(필요 시 확장: 남:, 여:, A:, B:, Q:, S: ...)
    speaker_pat = r"(?:M|W|Man|Woman|남|여|Q|S)"
    # 문자열 시작이 아닌 곳에서 화자태그 앞에 줄바꿈 삽입
    s = re.sub(rf"\s+(?={speaker_pat}\s*:)", "\n", s)
    return s

def extract_json_block(text: str) -> str:
    """
    본문에서 가장 큰 중괄호 JSON 블록을 추출합니다. 실패하면 원문 반환.
    """
    if not isinstance(text, str):
        return ""
    m = re.search(r"\{(?:[^{}]|(?R))*\}", text, flags=re.S)  # 중첩 허용 정규식
    return m.group(0) if m else text

def parse_json_loose(text: str) -> Any:
    """
    코드펜스 제거 → 바로 json.loads → 실패 시 중괄호 블록 추출 후 재시도.
    """
    t = strip_code_fence(text)
    try:
        return json.loads(t)
    except Exception:
        jb = extract_json_block(t)
        return json.loads(jb)