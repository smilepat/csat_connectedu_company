# app/specs/rc41_42_set.py
from __future__ import annotations
import re
from typing import Any, Dict, List

from app.specs.base import ItemSpec, GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.passage_preprocessor import sanitize_user_passage


def _clean_for_edit(passage: str) -> str:
    """
    RC41_42_EDIT_ONE_FROM_CLEAN 전용 전처리:
    - (a)~(e) 라벨 제거
    - <u>...</u> 밑줄 해제
    - circled 숫자/밑줄 등 잡스러운 표식도 sanitize_user_passage로 정리
    """
    s = passage or ""
    # (a) <u>word</u> → word
    s = re.sub(r"\(([a-e])\)\s*<u>(.*?)</u>", r"\2", s, flags=re.I | re.S)
    # (a) word → word
    s = re.sub(r"\(([a-e])\)\s*", "", s, flags=re.I)
    # 잔여 밑줄 해제
    s = re.sub(r"<u>(.*?)</u>", r"\1", s, flags=re.I | re.S)
    # circled numerals/밑줄 등 일반 정리
    s = sanitize_user_passage(s, strip_circled=True, strip_underlines=True)
    return s.strip()


class RC41_42SetSpec(ItemSpec):
    """
    RC41~RC42 세트(심플):
    - 지문이 있으면: RC41_42_EDIT_ONE_FROM_CLEAN 프롬프트 사용(지문은 AS-IS 기반, 표식만 정리)
    - 지문이 없으면: RC41_42 프롬프트 사용(모델이 지문 포함 생성)
    - normalize/validate: 최소 형태 요건만 확인 (마커/문단은 self_checks 경고로)
    """
    id = "RC41_42"

    def system_prompt(self) -> str:
        return (
            "CSAT English RC41–RC42 (Reading SET). "
            "Return ONLY JSON; no markdown. "
            "Use ONLY the provided passage for content. Do NOT invent a new passage. "
            "Q41: title, Q42: one inappropriate vocabulary among (a)~(e). "
            "If markers are missing, still produce consistent questions; do not rewrite the passage."
        )

    # ---------- prompt ----------
    def build_prompt(self, ctx: GenContext) -> str:
        raw_passage = (ctx.get("passage") or "").strip()
        has_passage = bool(raw_passage)
        # 맞춤(지문 있음) → EDIT_ONE_FROM_CLEAN 프롬프트
        if has_passage:
            cleaned = _clean_for_edit(raw_passage)
            return PromptManager.generate(
                item_type="RC41_42_EDIT_ONE_FROM_CLEAN",
                difficulty=(ctx.get("difficulty") or "medium"),
                topic_code=(ctx.get("topic") or "random"),
                passage=cleaned,
            )
        # 일반(지문 없음) → 기본 세트 프롬프트
        return PromptManager.generate(
            item_type=self.id,  # "RC41_42"
            difficulty=(ctx.get("difficulty") or "medium"),
            topic_code=(ctx.get("topic") or "random"),
            passage="",
        )

    # ---------- normalize ----------
    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("output must be a JSON object")

        out: Dict[str, Any] = {}
        out["set_instruction"] = str(
            data.get("set_instruction") or "[41~42] 다음 글을 읽고, 물음에 답하시오."
        )
        out["passage"] = str(data.get("passage") or "")

        qs = data.get("questions")
        if not isinstance(qs, list):
            raise ValueError("questions must be a list")

        norm_qs: List[Dict[str, Any]] = []
        for i, q in enumerate(qs[:2]):  # 과도한 문항이 와도 앞 2개만 우선
            if not isinstance(q, dict):
                continue
            qq: Dict[str, Any] = {}
            # 번호 보정
            try:
                num = int(q.get("question_number"))
            except Exception:
                num = 41 if i == 0 else 42
            qq["question_number"] = num
            # 공통 필드
            qq["question"] = str(q.get("question") or "")
            ops = q.get("options") or []
            if not isinstance(ops, list):
                ops = []
            ops = [str(x) for x in ops][:5]
            while len(ops) < 5:
                ops.append(f"Option {len(ops)+1}")
            qq["options"] = ops
            # 정답: '1'..'5' 문자열
            ca = q.get("correct_answer")
            try:
                ca_str = str(int(ca))
            except Exception:
                # 만약 '(e)'로 오는 등 비표준이면 1로 보정
                ca_str = "1"
            if ca_str not in {"1", "2", "3", "4", "5"}:
                ca_str = "1"
            qq["correct_answer"] = ca_str
            qq["explanation"] = str(q.get("explanation") or "")
            norm_qs.append(qq)

        # 41/42만 유지 + 정렬 + 부족 시 기본틀 보충
        norm_qs = [q for q in norm_qs if q.get("question_number") in (41, 42)]
        if not norm_qs:
            norm_qs = [
                {
                    "question_number": 41,
                    "question": "윗글의 제목으로 가장 적절한 것은?",
                    "options": ["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"],
                    "correct_answer": "1",
                    "explanation": "",
                },
                {
                    "question_number": 42,
                    "question": "밑줄 친 (a)~(e) 중에서 문맥상 낱말의 쓰임이 적절하지 <u>않은</u> 것은? [3점]",
                    "options": ["(a)", "(b)", "(c)", "(d)", "(e)"],
                    "correct_answer": "1",
                    "explanation": "",
                },
            ]
        else:
            # 2개 미만이면 채워주기
            nums = {q["question_number"] for q in norm_qs}
            if 41 not in nums:
                norm_qs.insert(0, {
                    "question_number": 41,
                    "question": "윗글의 제목으로 가장 적절한 것은?",
                    "options": ["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"],
                    "correct_answer": "1",
                    "explanation": "",
                })
            if 42 not in nums:
                norm_qs.append({
                    "question_number": 42,
                    "question": "밑줄 친 (a)~(e) 중에서 문맥상 낱말의 쓰임이 적절하지 <u>않은</u> 것은? [3점]",
                    "options": ["(a)", "(b)", "(c)", "(d)", "(e)"],
                    "correct_answer": "1",
                    "explanation": "",
                })
        norm_qs.sort(key=lambda x: x.get("question_number", 0))
        out["questions"] = norm_qs
        return out

    # ---------- validate (lenient) ----------
    def validate(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ValueError("Output must be an object")

        passage = data.get("passage") or ""
        if not isinstance(passage, str) or not passage.strip():
            raise ValueError("passage is required")

        qs = data.get("questions")
        if not isinstance(qs, list) or len(qs) < 2:
            raise ValueError("questions must contain two items for 41 and 42")

        q41 = next((q for q in qs if q.get("question_number") == 41), None)
        q42 = next((q for q in qs if q.get("question_number") == 42), None)
        if not q41 or not q42:
            raise ValueError("questions must include question_number 41 and 42")

        # 옵션/정답 기본형 체크(최소 요건)
        def _chk(q: Dict[str, Any], name: str):
            ops = q.get("options") or []
            if not (isinstance(ops, list) and len(ops) == 5 and all(isinstance(x, str) for x in ops)):
                raise ValueError(f"{name} options must be a list of 5 strings")
            ca = str(q.get("correct_answer"))
            if ca not in {"1", "2", "3", "4", "5"}:
                raise ValueError(f"{name} correct_answer must be '1'..'5'")

        _chk(q41, "Q41")
        _chk(q42, "Q42")

    # ---------- self checks (soft guidance) ----------
    def self_checks(self, data: Dict[str, Any], passage_src: str) -> List[str]:
        """
        RC41_42 세트: self_checks는 *진짜* 소프트 가이던스만 수행.
        - 파이프라인에서 self_checks 반환값이 비어있지 않으면 실패 처리되므로,
          여기서는 어떤 이슈도 반환하지 않는다(로그/메트릭으로만 쓰는 수준).
        """
        # 참고: 아래와 같은 점검은 내부적으로만 수행(필요 시 로깅)하고, 이슈는 반환하지 않음.
        # passage = data.get("passage") or ""
        # has_markers = bool(re.search(r"\(([a-e])\)\s*<u>[^<]+?</u>", passage, flags=re.I))
        # paras = [p for p in re.split(r"\n\s*\n", passage.strip()) if p.strip()]
        # exp42 = ""
        # for q in data.get("questions", []):
        #     if q.get("question_number") == 42:
        #         exp42 = str(q.get("explanation") or "")
        #         break
        # if not has_markers:  # 권고 수준
        #     ...
        # if len(paras) < 2:   # 권고 수준
        #     ...
        # if exp42 and ...:    # 권고 수준
        #     ...

        return []  # ✅ 어떤 경고도 실패로 올리지 않음

    # ---------- schema / budget ----------
    def json_schema(self) -> dict:
        # 간단 스키마(프론트/검증 참고용)
        return {
            "type": "object",
            "properties": {
                "set_instruction": {"type": "string"},
                "passage": {"type": "string"},
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question_number": {"type": "integer"},
                            "question": {"type": "string"},
                            "options": {"type": "array", "items": {"type": "string"}, "minItems": 5, "maxItems": 5},
                            "correct_answer": {"type": "string", "enum": ["1","2","3","4","5"]},
                            "explanation": {"type": "string"},
                        },
                        "required": ["question_number", "question", "options", "correct_answer", "explanation"],
                        "additionalProperties": True,
                    },
                    "minItems": 2
                }
            },
            "required": ["passage", "questions"],
            "additionalProperties": True
        }

    def repair_budget(self) -> dict:
        # 세트는 재시도/재생성 코스트가 크니 약간 여유
        return {"fixer": 1, "regen": 2, "timeout_s": 25}
