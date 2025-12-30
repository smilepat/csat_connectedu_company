# app/routes/suggest_types.py
from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict
from app.services.type_router import suggest_types  # ✅ 코어 라우터 재사용

router = APIRouter(prefix="/api")

class SuggestReq(BaseModel):
    passage: str
    top_k: int | None = 6

@router.post("/suggest_types")
def post_suggest_types(req: SuggestReq) -> Dict[str, Any]:
    try:
        result = suggest_types(req.passage, top_k=req.top_k or 6)
        # result = {"candidates":[{type:"RC22", fit:..., reason:..., prep_hint:...}, ...],
        #           "top":["RC22","RC31",...]}
        return {"ok": True, **result}
    except Exception as e:
        # 500 내지 말고 프론트가 처리할 수 있도록 200 + ok:false
        return {"ok": False, "error": f"suggest_types failed: {e.__class__.__name__}: {e}"}    
