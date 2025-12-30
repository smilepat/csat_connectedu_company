# app/schemas/export_docx.py
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union, Dict

# ── 이미지/차트/표 ────────────────────────────────────────────────
class ImageSpec(BaseModel):
    data_url: str                 # "data:image/png;base64,..." 또는 순수 base64
    caption: Optional[str] = None
    width_mm: Optional[int] = 140
    boxed: Optional[bool] = False
    title: Optional[str] = None

class ChartDataset(BaseModel):
    label: Optional[str] = None
    data: List[float]

class ChartData(BaseModel):
    type: str  # 'bar' | 'line'
    title: Optional[str] = None
    labels: List[str]
    datasets: List[ChartDataset]

class TableData(BaseModel):
    headers: List[str]
    rows: List[List[Any]]
    title: Optional[str] = None

# ── 문제 스키마 ──────────────────────────────────────────────────
class LabeledOption(BaseModel):
    label: str
    text: str

class SubItem(BaseModel):
    question: Optional[str] = None
    options: List[str] = Field(default_factory=list)
    optionsLabeled: Optional[List[LabeledOption]] = None
    answer: Optional[Any] = None
    explain: Optional[str] = None
    given_sentence: Optional[str] = None           # ✅ 주어진 문장 (빈 문자열은 프런트에서 보내지 않도록 권장)
    summary_template: Optional[str] = None
    chart_data: Optional[Union[ChartData, TableData]] = None
    image_base64: Optional[str] = None
    images: Optional[List[ImageSpec]] = None

class ExportItem(BaseModel):
    order: int
    question: Optional[str] = None
    passage: Optional[str] = None
    passage_paragraphs: Optional[List[str]] = None
    options: List[str] = Field(default_factory=list)
    optionsLabeled: Optional[List[LabeledOption]] = None
    answer: Optional[Any] = None
    explain: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    chart_data: Optional[Union[ChartData, TableData]] = None
    image_base64: Optional[str] = None
    images: Optional[List[ImageSpec]] = None
    summary_template: Optional[str] = None
    given_sentence: Optional[str] = None           # ✅ ExportItem 레벨에도 추가
    subItems: Optional[List[SubItem]] = None
    item_name: Optional[str] = None

class ExportPayload(BaseModel):
    title: str = "시험지"
    description: Optional[str] = None
    mode: str = Field(pattern="^(student|answer|explain)$")
    items: List[ExportItem] = Field(default_factory=list)
    answers_at_end: bool = True
    explain_at_end: bool = True
