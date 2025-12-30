# app/specs/base.py
from typing import Protocol, TypedDict, Any

class GenContext(TypedDict, total=False):
    difficulty: str | None
    topic: str | None
    item_id: str | None          # ✅ 추가: 실제 프롬프트 키를 담기 위함
    passage: str | None   # ✅ 추가: 외부에서 넘어온 지문

class ItemSpec(Protocol):
    id: str
    def build_prompt(self, ctx: GenContext) -> str: ...
    def normalize(self, data: dict) -> dict: ...
    def validate(self, data: dict): ...        # Pydantic v2 모델 인스턴스 리턴
    def json_schema(self) -> dict: ...
    def repair_budget(self) -> dict: ...       # {"fixer":1, "regen":1, "timeout_s":12}
