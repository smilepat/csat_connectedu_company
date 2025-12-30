from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field

# v2/v1 호환용
try:
    from pydantic import model_validator
    V2 = True
except ImportError:
    from pydantic import root_validator
    V2 = False

class RCSetChild(BaseModel):
    question: str = Field(min_length=1)
    options: List[str] = Field(min_length=5, max_length=5)
    correct_answer: Literal["1","2","3","4","5"]
    explanation: Optional[str] = None

class RCSetModel(BaseModel):
    # extra 필드(item_type 등) 들어와도 무시
    if V2:
        model_config = {"extra": "ignore"}
    else:
        class Config:
            extra = "ignore"

    type: Literal["RC_SET"]
    set_instruction: Optional[str] = None
    passage: Optional[str] = None
    passage_parts: Optional[Dict[str, str]] = None
    questions: List[RCSetChild] = Field(min_length=1)

    if V2:
        @model_validator(mode="after")
        def _at_least_one_passage(self):
            if not (self.passage or self.passage_parts):
                raise ValueError("Either 'passage' or 'passage_parts' must be provided.")
            return self
    else:
        @root_validator
        def _at_least_one_passage(cls, values):
            if not (values.get("passage") or values.get("passage_parts")):
                raise ValueError("Either 'passage' or 'passage_parts' must be provided.")
            return values
