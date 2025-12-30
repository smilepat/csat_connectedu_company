# app/specs/registry.py
import re
from typing import Optional
from app.specs.base import ItemSpec
from .lc06_payment_amount import LC06Spec
from .rc34_mcq import RC34Spec
from .rc_generic_mcq import RCGenericMCQSpec
from .lc_standard import LCStandardSpec
from .rc_set import RCSetSpec
from .rc22_mainpoint import RC22Spec
from .rc21_underlined_inference import RC21Spec
from .rc19_emotion import RC19Spec
from .rc20_argument import RC20Spec
from .rc18_purpose import RC18Spec
from .rc23_topic import RC23Spec
from .rc24_title import RC24Spec
from .rc25_graph_info import RC25Spec
from .rc26_connective_function import RC26Spec
from .rc27_irrelevant_sentence import RC27Spec
from .rc28_detail_true_false import RC28Spec
from .rc29_grammar import RC29Spec
from .rc30_lexical_appropriateness import RC30Spec
from .rc32_blank_phrase import RC32Spec
from .rc33_blank_clause import RC33Spec
from .rc35_insertion import RC35Spec
from .rc36_order_easy import RC36Spec
from .rc37_order_hard import RC37Spec
from .rc38_insertion_sentence import RC38Spec
from .rc39_insertion_paragraph import RC39Spec

from .rc31_blank_word import RC31Spec
from .rc40_summary import RC40Spec
from .rc41_42_set import RC41_42SetSpec
from .rc43_45_set import RC43_45SetSpec
from .auto_from_prompt_data import build_auto_specs

SPEC_REGISTRY = {
    "RC18": RC18Spec(),
    "RC19": RC19Spec(),
    "RC20": RC20Spec(),
    "RC21": RC21Spec(),   
    "RC22": RC22Spec(),
    "RC23": RC23Spec(),   
    "RC24": RC24Spec(),    
    "RC25": RC25Spec(),
    "RC26": RC26Spec(),
    "RC27": RC27Spec(),
    "RC28": RC28Spec(),
    "RC29": RC29Spec(),
    "RC30": RC30Spec(),          
    "RC31": RC31Spec(),
    "RC32": RC32Spec(),
    "RC33": RC33Spec(),
    "RC35": RC35Spec(),
    "RC36": RC36Spec(),
    "RC37": RC37Spec(),
    "RC38": RC38Spec(),
    "RC39": RC39Spec(),    
    "RC40": RC40Spec(),
    "RC34": RC34Spec(),
    "RC41_42": RC41_42SetSpec(),
    "RC43_45": RC43_45SetSpec(),    
    "RC_GENERIC": RCGenericMCQSpec(),
}

_LC_SPEC = LCStandardSpec()
_RC_SET_SPEC = RCSetSpec()

def register_family(prefix: str, start: int, end: int, spec: ItemSpec):
    for i in range(start, end + 1):
        SPEC_REGISTRY[f"{prefix}{i:02d}"] = spec

# LC01~LC17
register_family("LC", 1, 17, _LC_SPEC)
SPEC_REGISTRY["LC06"] = LC06Spec()
# RC41~RC45 (개별 번호용) → 세트는 아래 정규식으로 잡음
register_family("RC", 41, 45, _RC_SET_SPEC)

_missing_auto_ids = [f"RC{i:02d}" for i in range(26, 31) if f"RC{i:02d}" not in SPEC_REGISTRY]
if _missing_auto_ids:
    SPEC_REGISTRY.update(build_auto_specs(_missing_auto_ids))

SPEC_REGISTRY.update({
    "RC41": RC41_42SetSpec(),
    "RC42": RC41_42SetSpec(),
})
SPEC_REGISTRY.update({
    "RC43": RC43_45SetSpec(),
    "RC44": RC43_45SetSpec(),
    "RC45": RC43_45SetSpec(),
})
# ✅ 숫자 범위 패턴만 세트로 인식: RC##_## 또는 RC##-##
_RC_SET_RANGE = re.compile(r"^RC\d{2}[_-]\d{2}$")

def get_spec(item_id: str) -> Optional[ItemSpec]:
    code = (item_id or "").upper().strip()
    spec = SPEC_REGISTRY.get(code)
    if spec:
        return spec

    if code.startswith("LC"):
        return _LC_SPEC

    # 🔧 기존: "_"만 들어가면 세트로 간주하던 문제 → 숫자 범위일 때만 세트
    if _RC_SET_RANGE.match(code):
        return _RC_SET_SPEC

    # 폴백
    return SPEC_REGISTRY.get("RC_GENERIC")
