from pydantic import BaseModel, Field, validator
from typing import List

class RC28Model(BaseModel):
    question: str
    passage: str
    options: List[str] = Field(min_length=5, max_length=5)
    correct_answer: int  # 1..5
    explanation: str

    @validator("correct_answer")
    def _ca(cls, v):
        if not (1 <= v <= 5):
            raise ValueError("correct_answer must be 1..5")
        return v