# app/prompts/prompt_manager.py

from __future__ import annotations

import importlib
import logging
import os
from types import ModuleType
from typing import Optional, Tuple

from app.prompts.prompt_data import ITEM_PROMPTS  # 레거시(폴백 및 overlay 저장소)
from app.prompts.micro_topics import choose_micro_topic
from app.specs.helpers import make_prompt_with_passage
from app.prompts.base import build_base

log = logging.getLogger("prompt_manager")

# 필요 시 운영 중에 확장하세요
LC_SET_IDS   = {"LC16", "LC17"}
LC_CHART_IDS = {"LC10", "LC11", "LC12"}

RC_BLANK_IDS  = {"RC34"}            # RC34 = 빈칸(표준 MCQ)
RC_INSERT_IDS = {"RC35"}            # RC35 = 삽입
RC_ORDER_IDS  = {"RC36", "RC37"}    # RC36/37 = 순서
RC_SET_RANGE  = ("RC", 41, 45)      # RC41~45 = 세트

ALIAS = {
    "RC_GENERIC": "RC_BLANK",
}

_CANONICAL_KEYS = {
    "LC_STANDARD", "LC_CHART", "LC_SET",
    "RC_BLANK", "RC_INSERTION", "RC_ORDER", "RC_SET",
}

# 캐논키 → 숫자 프롬프트 기본 폴백
DEFAULT_FALLBACK_BY_CANON = {
    "RC_BLANK": "RC34",
    "RC_INSERTION": "RC35",
    "RC_ORDER": "RC36",      # 필요시 37로 조정
    "RC_SET": "RC41",

    "LC_STANDARD": "LC01",
    "LC_CHART": "LC10",
    "LC_SET": "LC16",
}

DEBUG_PM = os.getenv("DEBUG_PM", "1").lower() in ("1", "true", "yes", "on")

def _dpm(msg: str):
    if DEBUG_PM:
        print(f"[PromptManager] {msg}")

def _in_range(code: str, prefix: str, start: int, end: int) -> bool:
    code = (code or "").upper()
    if not code.startswith(prefix):
        return False
    try:
        n = int(code[len(prefix):])
        return start <= n <= end
    except Exception:
        return False

def _rc_number(code: str) -> Optional[int]:
    code = (code or "").upper()
    if not code.startswith("RC"):
        return None
    try:
        return int(code[2:])
    except Exception:
        return None

def normalize_key(code: str | None) -> str:
    """
    - 언더스코어/하이픈이 있으면 SET로 정규화
    - 명시 매핑(LC/RC 특정 번호) 우선
    - 그 외 RC 번호(18~40)는 기본적으로 RC_BLANK로 폴백
    """
    k = (code or "").upper().strip()
    if not k:
        return "RC_BLANK"

    # 0) alias
    if k in ALIAS:
        return ALIAS[k]

    # 1) 이미 캐논이면 그대로
    if k in _CANONICAL_KEYS:
        return k

    # 2) 범위 표기 → SET
    if k.startswith("LC") and ("_" in k or "-" in k):
        return "LC_SET"
    if k.startswith("RC") and ("_" in k or "-" in k):
        return "RC_SET"

    # 3) LC 패밀리
    if k in LC_SET_IDS:
        return "LC_SET"
    if k in LC_CHART_IDS:
        return "LC_CHART"
    if k.startswith("LC"):
        return "LC_STANDARD"

    # 4) RC 패밀리 (명시)
    if k in RC_BLANK_IDS:
        return "RC_BLANK"
    if k in RC_INSERT_IDS:
        return "RC_INSERTION"
    if k in RC_ORDER_IDS:
        return "RC_ORDER"
    if _in_range(k, *RC_SET_RANGE):
        return "RC_SET"

    # 5) RC 번호 범위 기반 폴백 (18~40 → RC_BLANK 기본 처리)
    n = _rc_number(k)
    if n is not None:
        if 18 <= n <= 40:
            return "RC_BLANK"     # 템플릿이 없으면 RC34로 폴백되도록 설계
        # 기타 번호는 그대로 유지(템플릿이 직접 있을 수 있음)
        return k

    # 6) 그 외는 그대로
    return k


# -------------------- 신규: 모듈 기반 템플릿 로더 --------------------

def _key_to_module_name(key: str) -> str:
    """
    "LC01" -> "lc01"
    "RC25" -> "rc25"
    "RC41_45" -> "rc41_45"
    "LC16-17" -> "lc16_17"
    """
    k = (key or "").strip().lower()
    return k.replace("-", "_")

def _import_item_module(key: str) -> Optional[ModuleType]:
    modname = f"app.prompts.items.{_key_to_module_name(key)}"
    _dpm(f"trying import: {modname}")
    try:
        import importlib
        importlib.invalidate_caches()   # ★ 새 파일/수정 반영
        mod = importlib.import_module(modname)
        _dpm(f"import ok: {modname} -> {getattr(mod, '__file__', '?')}")
        return mod
    except ModuleNotFoundError:
        _dpm(f"import miss: {modname}")
        return None
    except Exception as e:
        log.exception(f"Error importing module {modname}: {e}")
        return None

def _load_item_template(key: str) -> Tuple[Optional[str], Optional[dict], Optional[str]]:
    mod = _import_item_module(key)
    if mod:
        content = getattr(mod, "PROMPT", None)
        spec = getattr(mod, "SPEC", None)
        title = spec.get("title") if isinstance(spec, dict) else None
        clen = len(content.strip()) if isinstance(content, str) else -1
        _dpm(f"[{key}] symbols -> has_PROMPT={isinstance(content, str)} len={clen} has_SPEC={isinstance(spec, dict)} title={title!r}")
        if isinstance(content, str) and content.strip():
            return content, (spec if isinstance(spec, dict) else None), title
    # (이하 레거시 분기 동일)
    legacy = ITEM_PROMPTS.get(key)
    if isinstance(legacy, dict):
        content = legacy.get("content")
        spec = legacy.get("spec")
        title = legacy.get("title")
        clen = len(content.strip()) if isinstance(content, str) else -1
        _dpm(f"[{key}] legacy -> has_content={isinstance(content, str)} len={clen} has_spec={isinstance(spec, dict)}")
        if isinstance(content, str) and content.strip():
            return content, (spec if isinstance(spec, dict) else None), title
    return None, None, None


class PromptManager:
    """
    Overlay-aware PromptManager

    병합 순서(최종 user 메시지):
    1) base_system = build_base(vocab_profile)
    2) overlay_text (있으면)
    3) item_template["content"] (또는 items/<id>.PROMPT)
    4) difficulty_instructions[difficulty] (있으면)
    5) topic/detail/micro-topic (있으면)
    6) passage 주입(있으면)
    7) OUTPUT RULES (공통)
    """

    difficulty_instructions = {
        "easy": (
            "\n\n**난이도 조정**: 쉬운 수준으로 만들어주세요.\n"
            "- 추상성: Kim(2012) 2–3 (낮음)\n"
            "- 문장 길이: 10–14 words/sentence\n"
            "- 절 개수: ≤ 1.3 clauses/sentence\n"
            "- 종속절 비율: ≤ 0.25\n"
            "- 어휘: 기본~중간(Basic~Lower-Intermediate), CSAT 허용 어휘 중 하위권 중심\n"
            "- 문체: 단문 중심, 단순 접속사 위주, 친숙 주제\n"
            "- 명사화 제한: 불필요한 명사형 전환은 금지, 동사·형용사 중심 표현 사용"
        ),
        "medium": (
            "- 문체: 단문+복문 혼합, 보통 수준의 추상화와 정보 밀도\n"
            "- 명사화 제한: 지나친 명사화 피하기, 동사/형용사 기반 서술 유지"
        ),
        "hard": (
            "\n\n**난이도 조정**: 어려운 수준으로 만들어주세요.\n"
            "- 추상성: Kim(2012) 6–8 (상중~상)\n"
            "- 문장 길이: 18–24 words/sentence\n"
            "- 절 개수: 1.8–2.4 clauses/sentence\n"
            "- 종속절 비율: 0.45–0.70\n"
            "- 어휘: 상중~상(Upper-Intermediate~Advanced), 고빈도 학술어 일부 허용\n"
            "- 문체: 복문 비중↑, 종속절·분사구문·명사화 증가 가능 (단, 남용 금지)\n"
            "- 명사화 제한: 반드시 필요한 경우에만 사용, 과도한 정보 압축식 명사화 금지"
        ),
    }

    # (레거시) 상위 카테고리 레벨 지시
    topic_instructions = {
        "humanities":        "\n\n**주제(상위)**: 인문과학(철학·종교·언어·문학·교육 등)과 관련된 내용으로 작성하세요.",
        "social_science":    "\n\n**주제(상위)**: 사회과학(정치·경제·사회·문화·행정/경영·복지/건강 등)과 관련된 내용으로 작성하세요.",
        "natural_science":   "\n\n**주제(상위)**: 자연과학(물리·화학·생물·지구과학·환경·공학 등)과 관련된 내용으로 작성하세요.",
        "practical_writing": "\n\n**주제(상위)**: 실용문(개인·가정·학교·사회·직장·문화생활·상식 등)과 관련된 내용으로 작성하세요.",
    }

    # ✅ 세부 코드 → 강한 제약 지시
    detail_topic_instructions = {
        # ---------- 인문과학 ----------
        "philosophy":            "\n\n**주제(세부)**: ‘철학’ 관련 핵심 개념·사상·논증을 중심 주제로 하세요.",
        "religion":              "\n\n**주제(세부)**: ‘종교’의 신념·의례·역사·문화적 맥락 중 하나 이상을 중심으로 하세요.",
        "language":              "\n\n**주제(세부)**: ‘언어’의 구조·의미·사용·획득·변화 등 언어학적 관점을 다루세요.",
        "literature":            "\n\n**주제(세부)**: ‘문학’의 장르·작품·주제·기법·비평 관점을 중심으로 하세요.",
        "education":             "\n\n**주제(세부)**: ‘교육’의 목적·방법·평가·학습 이론·교육환경 중 하나 이상을 다루세요.",
        "general_humanities":    "\n\n**주제(세부)**: 인문과학 전반(철학·종교·언어·문학·교육 등)의 종합적 쟁점을 다루세요.",

        # ---------- 사회과학 ----------
        "political_diplomacy":   "\n\n**주제(세부)**: ‘정치/외교’의 제도·이론·사례·국제관계를 다루세요.",
        "economy":               "\n\n**주제(세부)**: ‘경제’의 시장·정책·금융·무역·행동경제학 등 핵심 개념을 다루세요.",
        "society":               "\n\n**주제(세부)**: ‘사회’의 계층·가족·교육·미디어·범죄·도시 등 사회학적 쟁점을 다루세요.",
        "culture":               "\n\n**주제(세부)**: ‘문화’의 생성·전파·수용·콘텐츠·정체성·다문화 관련 이슈를 다루세요.",
        "administration_management": "\n\n**주제(세부)**: ‘행정/경영’의 조직·의사결정·전략·정책 집행·공공/기업 사례를 다루세요.",
        "welfare_health":        "\n\n**주제(세부)**: ‘복지/건강’의 제도·정책·공중보건·보건의료 접근성을 다루세요.",
        "general_social_sciences":"\n\n**주제(세부)**: 사회과학 전반(정치·경제·사회·문화·행정/경영·복지/건강)의 통합적 주제를 다루세요.",

        # ---------- 자연과학 ----------
        "physics":               "\n\n**주제(세부)**: ‘물리’의 법칙·모형·실험·응용(예: 역학·전자기·양자 등)을 다루세요.",
        "chemistry":             "\n\n**주제(세부)**: ‘화학’의 물질·반응·구조·열역학·동역학·재료 응용을 다루세요.",
        "biology":               "\n\n**주제(세부)**: ‘생물’의 생명 현상·진화·유전·생태·생명공학 등을 다루세요.",
        "earth_science":         "\n\n**주제(세부)**: ‘지구과학’(지질·기상·해양·천문) 관련 개념·현상·탐구를 다루세요.",
        "environment":           "\n\n**주제(세부)**: ‘환경’의 오염·기후변화·보전·순환·정책·기술적 대응을 다루세요.",
        "engineering":           "\n\n**주제(세부)**: ‘공학’의 설계·시스템·알고리즘·제조·인프라·신기술 응용을 다루세요.",
        "general_natural_sciences":"\n\n**주제(세부)**: 자연과학 전반(물리·화학·생물·지구과학·환경·공학)의 융합적 주제를 다루세요.",

        # ---------- 실용문 ----------
        "personal_life":         "\n\n**주제(세부)**: ‘개인생활(취미·여가·건강·일상·소비 등)’의 실제적 상황과 문제 해결을 다루세요.",
        "family_life":           "\n\n**주제(세부)**: ‘가정생활(의복·음식·주거·가사·가족 행사)’의 정보·절차·의사소통을 다루세요.",
        "school_life":           "\n\n**주제(세부)**: ‘학교생활(수업·과제·평가·활동·진로)’의 안내·요청·보고·설득 등을 다루세요.",
        "social_life":           "\n\n**주제(세부)**: ‘사회생활(대인관계·모임·민원·공적 절차)’의 실제적 의사소통을 다루세요.",
        "work_life":             "\n\n**주제(세부)**: ‘직장생활(채용·보고·협업·규정·성과)’의 문서·메시지·지침·절차를 다루세요.",
        "culture_life":          "\n\n**주제(세부)**: ‘문화생활(공연·전시·여행·행사·예약·이용 안내)’의 실용 정보를 다루세요.",
        "common_sense":          "\n\n**주제(세부)**: ‘상식(안전·교통·재난·생활법률·금융기초·디지털 기본)’의 안내·주의·절차를 다루세요.",
    }

    # --------- Overlay 탐색기 (레거시 저장소 활용) ---------
    @classmethod
    def _get_overlay(cls, chosen_key: str, canonical_key: str) -> str:
        """
        오버레이 탐색 우선순위:
        1) _OVERLAYS[chosen_key]
        2) _OVERLAYS[f"{chosen_key}_OVERLAY"]
        3) _OVERLAYS[f"OVERLAY_{canonical_key}"]
        4) _OVERLAYS["OVERLAY_DEFAULT"]
        """
        store = ITEM_PROMPTS.get("_OVERLAYS", {}) or {}
        def _pull(k: str) -> str:
            v = store.get(k)
            if isinstance(v, str):
                return v.strip()
            if isinstance(v, dict):
                return (v.get("content") or "").strip()
            return ""

        for key in (chosen_key, f"{chosen_key}_OVERLAY", f"OVERLAY_{canonical_key}", "OVERLAY_DEFAULT"):
            ov = _pull(key)
            if ov:
                _dpm(f"overlay hit: {key} (len={len(ov)})")
                return ov

        _dpm("overlay MISS → use empty overlay")
        return ""

    @classmethod
    def _build_topic_instruction(cls, topic_code: str | None) -> str:
        if not topic_code or topic_code == "random":
            log.info("[PromptManager] topic_code is 'random' or empty -> no topic instruction")
            return ""

        inst = cls.detail_topic_instructions.get(topic_code, "")
        if not inst:
            log.warning(f"[PromptManager] topic_code MISS: {topic_code} (no instruction found)")
            return ""

        # ✅ 미세 토픽 랜덤 선택 + 주입
        micro = choose_micro_topic(topic_code)
        if micro:
            inst += f"\n- 세부 주제(미세): {micro} 를 반드시 반영하세요."
            log.info(f"[PromptManager] micro-topic chosen for '{topic_code}': {micro}")
        else:
            log.warning(f"[PromptManager] no micro-topics for '{topic_code}'")

        return inst

    @classmethod
    def generate(
        cls,
        item_type: str,
        difficulty: str = "medium",
        topic_code: str = "random",
        passage: str | None = None,
        vocab_profile: str | None = None,
        enable_overlay: bool = True,
    ) -> str:
        """
        템플릿 선택 우선순위:
        1) 원본 키(예: LC03, RC26, RC43_45)
        2) 범위형이면 첫 구간 키(예: RC43_45 -> RC43, LC16-17 -> LC16)
        3) 캐논 키(LC_STANDARD/LC_CHART/LC_SET/RC_BLANK/…)
        4) 캐논→숫자 폴백(LC_SET->LC16, RC_SET->RC41, RC_BLANK->RC34 …)
        """
        raw = (item_type or "").upper().strip()

        # 1) BASE: base.py 일원화
        base = build_base(vocab_profile=vocab_profile)
        if not isinstance(base, str) or not base.strip():
            raise ValueError("build_base() returned empty/None system prompt")

        _dpm(f"generate() in | raw={raw!r} difficulty={difficulty!r} topic={topic_code!r} passage_len={len(passage or '')} vocab={vocab_profile!r} overlay={enable_overlay}")

        # 후보 키 탐색
        candidates: list[str] = []
        if raw:
            candidates.append(raw)  # 원본 키 최우선

        # 범위형(세트) → 첫 구간 키도 후보에 추가
        first_key = None
        for delim in ("_", "-"):
            if delim in raw:
                first_key = raw.split(delim)[0]
                break
        if first_key and first_key not in candidates:
            candidates.append(first_key)

        # 캐논 키
        canonical_key = normalize_key(raw)
        if canonical_key and canonical_key not in candidates:
            candidates.append(canonical_key)

        # 캐논 → 숫자 폴백
        numeric_fallback = DEFAULT_FALLBACK_BY_CANON.get(canonical_key)
        if numeric_fallback and numeric_fallback not in candidates:
            candidates.append(numeric_fallback)

        _dpm(f"candidates order = {candidates}")
        _dpm(f"has RC41_42 prompt? {'RC41_42' in ITEM_PROMPTS}, has RC43_45 prompt? {'RC43_45' in ITEM_PROMPTS}")

        # 템플릿 로드 (모듈 우선, 레거시 폴백)
        item_content = None
        item_spec = None
        item_title = None
        chosen_key = None

        for k in candidates:
            content, spec, title = _load_item_template(k)
            _dpm(f"candidate '{k}' -> hit={bool(content)}")
            if content:
                item_content = content
                item_spec = spec
                item_title = title
                chosen_key = k
                _dpm(f"template hit = {k} (module={'yes' if _import_item_module(k) else 'no'}, legacy={'yes' if k in ITEM_PROMPTS else 'no'})")
                break

        if not item_content:
            tried = ", ".join(candidates) or raw
            raise ValueError(f"프롬프트를 찾을 수 없습니다: tried [{tried}]")

        # ---------- Overlay ----------
        overlay_text = ""
        if enable_overlay:
            overlay_text = cls._get_overlay(chosen_key, canonical_key)

        # ---------- 병합 ----------
        # 1) 전역
        prompt = base

        # 2) 오버레이
        if overlay_text:
            prompt += "\n\n" + overlay_text

        # 3) 템플릿 본문
        prompt += "\n\n" + item_content

        # 4) 난이도/토픽 지시
        diff_inst = cls.difficulty_instructions.get(difficulty, "")
        if diff_inst:
            _dpm(f"difficulty instruction applied: {difficulty}")
            prompt += diff_inst
        else:
            _dpm(f"difficulty='{difficulty}' -> no extra instruction")

        topic_inst = cls._build_topic_instruction(topic_code)
        if topic_inst:
            prompt += topic_inst  # ✅ 토픽 지시를 먼저 붙임

        # 5) 어휘 프로필(선택) — 항목 출력 필드 보강 힌트
        if vocab_profile:
            prompt += (
                f"\n\n**Vocabulary Profile**: Use \"{vocab_profile}\" level vocabulary. "
                f"Output also includes: \"vocabulary_difficulty\": \"{vocab_profile}\", \"low_frequency_words\": []"
            )

        # 6) passage 주입
        if passage:
            prompt = make_prompt_with_passage(prompt, passage)
            try:
                _dpm(f"passage attached: {len(passage)} chars")
            except Exception:
                pass
        else:
            _dpm("[PM] passage missing or empty → no passage block injected")

        # 7) OUTPUT RULES
        prompt += (
            "\n\n# OUTPUT RULES\n"
            "- Output only a valid JSON object. No extra text or markdown.\n"
            "- All passages/transcripts must be in English. Questions/explanations in Korean.\n"
            "- The theme MUST align with the specified topic detail. If misaligned, regenerate internally and return only the final JSON."
        )

        return prompt
