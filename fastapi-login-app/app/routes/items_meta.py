# app/routes/items_meta.py

from fastapi import APIRouter, HTTPException
from app.prompts.prompt_manager import PromptManager

router = APIRouter(prefix="/api/items", tags=["items-meta"])

@router.get("/types")
def get_all_item_types():
    return {
        "types": PromptManager.get_all_types(),
        "listening": PromptManager.get_listening_types(),
        "reading": PromptManager.get_reading_types()
    }

@router.get("/spec/{item_type}")
def get_item_spec(item_type: str):
    spec = PromptManager.get_spec(item_type)
    if not spec:
        raise HTTPException(status_code=404, detail="문항 스펙을 찾을 수 없습니다.")
    return spec

@router.get("/title/{item_type}")
def get_item_title(item_type: str):
    title = PromptManager.get_title(item_type)
    if not title:
        raise HTTPException(status_code=404, detail="문항 제목을 찾을 수 없습니다.")
    return {"title": title}

@router.get("/is_set/{item_type}")
def is_set_type(item_type: str):
    return {"is_set": PromptManager.is_set_type(item_type)}
