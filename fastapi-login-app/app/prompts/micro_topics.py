# app/prompts/micro_topics.py
from __future__ import annotations
import json
import random
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Optional

DEFAULT_JSON_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "micro_topics.json"

class MicroTopicsError(Exception):
    pass

@lru_cache(maxsize=1)
def load_micro_topics(path: Optional[str | Path] = None) -> Dict[str, List[str]]:
    """
    micro_topics.json을 로드하고 캐싱합니다.
    - path를 생략하면 DEFAULT_JSON_PATH를 사용합니다.
    - 파일이 없거나 JSON이 깨졌을 때는 MicroTopicsError를 던집니다.
    """
    p = Path(path) if path else DEFAULT_JSON_PATH
    if not p.exists():
        raise MicroTopicsError(f"micro_topics.json not found: {p}")

    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise MicroTopicsError("micro_topics.json root must be an object mapping topic_code -> list[str]")
        # 값 유효성 간단 체크
        for k, v in data.items():
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                raise MicroTopicsError(f"Invalid micro topics for key '{k}': must be list[str]")
        return data
    except json.JSONDecodeError as e:
        raise MicroTopicsError(f"Invalid JSON in micro_topics.json: {e}") from e

def get_micro_list(topic_code: str, *, path: Optional[str | Path] = None) -> List[str]:
    data = load_micro_topics(path)
    return data.get(topic_code, [])

def choose_micro_topic(
    topic_code: str,
    *,
    rng: Optional[random.Random] = None,
    path: Optional[str | Path] = None
) -> Optional[str]:
    """
    topic_code에 해당하는 미세 토픽을 1개 랜덤 선택하여 반환합니다.
    - rng를 주면 재현 가능한 선택(시드 고정)이 가능합니다.
    - 토픽이 없으면 None을 반환합니다.
    """
    lst = get_micro_list(topic_code, path=path)
    if not lst:
        return None
    r = rng or random
    return r.choice(lst)

def choose_n_unique(
    topic_code: str,
    n: int,
    *,
    rng: Optional[random.Random] = None,
    path: Optional[str | Path] = None
) -> List[str]:
    """
    topic_code에서 서로 다른 미세 토픽 n개를 샘플링합니다.
    리스트 길이가 n보다 짧으면 전체를 반환합니다.
    """
    lst = get_micro_list(topic_code, path=path)
    if not lst:
        return []
    if n >= len(lst):
        return lst[:]  # 전부 반환
    r = rng or random
    return r.sample(lst, k=n)
