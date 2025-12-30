# app/routes/generate_one.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.item_pipeline import generate_multi_from_passage

router = APIRouter()

class GenerateOneReq(BaseModel):
    passage: str
    item_type: str            # 예: "RC22"
    difficulty: Optional[str] = "medium"
    seed: Optional[int] = None

@router.post("/generate_one")
def generate_one(req: GenerateOneReq):
    """
    단일 문항을 생성해서 바로 반환.
    generate_multi_from_passage()의 1개 결과(envelope)만 그대로 넘깁니다.
    """
    items = generate_multi_from_passage(
        passage=req.passage,
        types=[req.item_type],
        n_per_type=1,
        difficulty=req.difficulty,
        seed=req.seed,
    )
    if items and len(items) > 0:
        return items[0]
    return {"ok": False, "message": "생성 실패", "error": {"detail": "empty"}}
