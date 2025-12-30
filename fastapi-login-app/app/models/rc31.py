# app/models/rc31.py
from pydantic import BaseModel, Field, conlist, field_validator

class RC31Item(BaseModel):
    question: str = Field(pattern=r"^다음 글의 빈칸에 들어갈 말로 가장 적절한 것은\?$")
    passage: str
    options: conlist(str, min_length=5, max_length=5)
    correct_answer: int
    explanation: str

    @field_validator("passage")
    @classmethod
    def blank_once(cls, v):
        if v.count("_____") != 1:
            raise ValueError("passage must contain exactly one blank '_____'")
        return v

    @field_validator("correct_answer")
    @classmethod
    def ca_range(cls, v):
        if not (1 <= v <= 5): raise ValueError("correct_answer must be 1..5")
        return v
