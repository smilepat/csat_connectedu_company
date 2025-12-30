# app/schemas/items_rc34.py
from pydantic import BaseModel, Field
from typing import Literal

class RC34Model(BaseModel):
    passage: str | None = None
    question: str
    options: list[str] = Field(min_length=5, max_length=5)
    correct_answer: Literal["1","2","3","4","5"]  # 검증 강화(선택)
    explanation: str | None = None  # ← 이름 변경