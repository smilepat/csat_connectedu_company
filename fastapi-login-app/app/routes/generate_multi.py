# app/routes/generate_multi.py
from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, conlist
from typing import Optional, List

from app.services.item_pipeline import generate_multi_from_passage

router = APIRouter(prefix="/api")

class GenerateReq(BaseModel):
    passage: str
    types: conlist(str, min_length=1)
    n_per_type: int = 1
    difficulty: Optional[str] = None
    seed: Optional[int] = None

@router.post("/generate_multi")
def post_generate_multi(req: GenerateReq):
    try:
        items = generate_multi_from_passage(
            passage=req.passage,
            types=req.types,
            n_per_type=req.n_per_type,
            difficulty=req.difficulty,
            seed=req.seed,
        )
        # 성공/부분성공/부분실패 상관없이 항상 200 + JSON
        return JSONResponse(content={"ok": True, "items": items}, media_type="application/json")
    except Exception as e:
        # ★ 여기서 500을 막고, 프론트가 그릴 수 있는 표준 형태로 돌려줍니다.
        return JSONResponse(
            content={
                "ok": False,
                "message": "생성 호출 처리 중 오류가 발생했습니다.",
                "error": {"detail": f"{e.__class__.__name__}: {e}"},
            },
            media_type="application/json",
            status_code=200,
        )
