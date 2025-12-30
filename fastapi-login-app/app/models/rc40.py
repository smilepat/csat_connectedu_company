# app/models/rc40.py
from pydantic import BaseModel, Field, conlist, field_validator

class RC40Item(BaseModel):
    question: str = Field(pattern=r"^다음 글의 내용을 한 문장으로 요약하고자 한다\. 빈칸 \(A\), \(B\)에 들어갈 말로 가장 적절한 것은\? \[3점\]$")
    passage: str
    summary_template: str
    options: conlist(str, min_length=5, max_length=5)
    correct_answer: int
    explanation: str

    @field_validator("summary_template")
    @classmethod
    def ab_underlines(cls, v):
        # 최소한 A/B 존재 + <u> 태그 존재 확인
        if "(A)" not in v or "(B)" not in v or "<u" not in v:
            raise ValueError("summary_template must include underlined (A) and (B)")
        return v

    @field_validator("correct_answer")
    @classmethod
    def ca_range(cls, v):
        if not (1 <= v <= 5): raise ValueError("correct_answer must be 1..5")
        return v
