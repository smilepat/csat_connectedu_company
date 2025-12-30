# rc26_person_mismatch.py (기존 rc26_connective_function.py 대체)

from __future__ import annotations
from app.specs._base_mcq import BaseMCQSpec

class RC26Spec(BaseMCQSpec):
    """
    RC26: 인물 정보 불일치
    - 주어진 인물/인물군에 대한 글을 읽고, 5개의 진술 중 지문과 일치하지 않는 것(1개)을 고르는 유형
    - 스키마는 BaseMCQSpec(MCQModel)과 동일: question, passage, options[5], correct_answer('1'~'5'), explanation
    - 맞춤 생성에서도 불필요한 실패를 막기 위해 의미론 추가검사는 하지 않음(형태 검증은 베이스에서 수행)
    """
    id = "RC26"

    def system_prompt(self) -> str:
        return (
            "CSAT English RC26 (인물 정보 불일치). "
            "Given a passage describing a person (biographical/profile text), "
            "create five Korean statements about the person; exactly one must contradict the passage. "
            "Return ONLY JSON matching the schema. Use ONLY the provided passage."
        )

    # 추가 의미론 검사 제거: Base의 스키마 검증만 사용
    def extra_checks(self, data: dict):
        return

    def repair_budget(self) -> dict:
        # 기본값 유지(필요시 여유를 조금 더 주고 싶다면 timeout_s를 18~20으로 올리세요)
        return {"fixer": 1, "regen": 1, "timeout_s": 15}
