# app/schemas/items_lc.py
from typing import Optional, Literal, List, Any, Union
from pydantic import BaseModel, Field, HttpUrl
try:
    # pydantic v2
    from pydantic import TypeAdapter
    V2 = True
except ImportError:
    V2 = False

# 1) 단일형
class LCStandardModel(BaseModel):
    type: Literal["LC_STANDARD"]
    transcript: str = Field(min_length=1)
    question: str = Field(min_length=1)
    options: List[str] = Field(min_length=5, max_length=5)
    correct_answer: Literal["1","2","3","4","5"]
    explanation: Optional[str] = None
    audio_url: Optional[HttpUrl] = None

# 2) 도표형
class LCChartModel(BaseModel):
    type: Literal["LC_CHART"]
    transcript: str = Field(min_length=1)
    question: str = Field(min_length=1)
    options: List[str] = Field(min_length=5, max_length=5)
    correct_answer: Literal["1","2","3","4","5"]
    explanation: Optional[str] = None
    # chart_data는 프론트에서 정규화되므로 백엔드는 관대하게 허용
    chart_data: Any

# 3) 세트 컨테이너
class LCSetChild(BaseModel):
    question: str = Field(min_length=1)
    options: List[str] = Field(min_length=5, max_length=5)
    correct_answer: Literal["1","2","3","4","5"]
    explanation: Optional[str] = None

class LCSetModel(BaseModel):
    type: Literal["LC_SET"]
    set_instruction: Optional[str] = None
    transcript: Optional[str] = None  # 세트 지문(대본)
    questions: List[LCSetChild] = Field(min_length=1)

# 4) Fixer/재생성용 Union 스키마
def lc_union_json_schema() -> dict:
    if V2:
        return TypeAdapter(Union[LCStandardModel, LCChartModel, LCSetModel]).json_schema()
    # v1 fallback: 가장 보수적으로 단일형 스키마 반환 (필요시 수동 oneOf 구성)
    return LCStandardModel.schema()
