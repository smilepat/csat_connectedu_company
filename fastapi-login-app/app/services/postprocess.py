# app/services/postprocess.py
def sanitize_html(data: dict) -> dict:
    # 밑줄 태그는 살리고 기타 위험 기호를 최소 정리
    def clean(s: str) -> str:
        if not isinstance(s, str): return s
        return s.replace("**", "")
    out = {}
    for k, v in data.items():
        if isinstance(v, str):
            out[k] = clean(v)
        elif isinstance(v, list):
            out[k] = [clean(x) if isinstance(x, str) else x for x in v]
        else:
            out[k] = v
    return out

