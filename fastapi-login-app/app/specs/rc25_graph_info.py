# app/specs/rc25_graph_info.py
# RC25 — Answer-Verified + Content-First Autoregen + Answer Auto-Fix (2025-10-26)
#
# 핵심:
#  - LLM으로 ①~⑤ 진위를 판정(문장 배열 전달, 엄밀 규칙 적용)
#  - 거짓이 정확히 1개가 아니면 예외 → item_generator의 리젠 경로로 진입
#  - (신규) correct_answer 불일치 시, 옵션(auto_fix_answer=True)일 때 정답/해설을 자동 보정하여 성공 처리
#  - content_first_generate() 내장: 1차 생성→판정→실패 시 강화 프롬프트 재생성→그래도 실패면 자동 보정(①만 거짓)
#
# 사용:
#  - registry에서 RC25 → 이 스펙으로 매핑
#  - prompts/items/rc25.py의 SPEC 심볼은 이 클래스로 위임 권장:
#       from app.specs.rc25_graph_info import RC25Spec
#       SPEC = RC25Spec()
#
# 주의:
#  - item_generator.py는 이미 content_first_generate가 있으면 우선 이 경로를 사용하도록 작성돼 있음.

from __future__ import annotations

import asyncio
import json
import re
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

from app.specs.base import GenContext
from app.prompts.prompt_manager import PromptManager
from app.specs.utils import coerce_mcq_like
from app.core import openai_config


_CIRCLED = ["①", "②", "③", "④", "⑤"]
_RE_YEAR4 = re.compile(r"^\d{4}$")


# -----------------------
# Lightweight chart schema
# -----------------------
class _Dataset(BaseModel):
    label: str = Field(default="")
    data: List[float] = Field(default_factory=list)

    @field_validator("label", mode="before")
    @classmethod
    def _label(cls, v):
        return str(v or "").strip()

    @field_validator("data", mode="before")
    @classmethod
    def _data(cls, v):
        arr = v if isinstance(v, list) else [v]
        out: List[float] = []
        for x in arr:
            try:
                out.append(float(x))
            except Exception:
                out.append(0.0)
        return out


class _ChartData(BaseModel):
    type: str = "bar"
    title: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    datasets: List[_Dataset] = Field(default_factory=list)

    @field_validator("labels", mode="before")
    @classmethod
    def _labels(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.replace(",", "\n").splitlines() if x.strip()]
        return [str(x).strip() for x in (v or [])]

    @model_validator(mode="after")
    def _length_check(self):
        # 길이 불일치는 normalize에서 보정하므로 여기서는 통과
        return self


# -----------------------
# Item model (형식만 확인)
# -----------------------
class RC25Model(BaseModel):
    question: str
    passage: str
    options: List[str] = Field(default_factory=lambda: ["①", "②", "③", "④", "⑤"])
    correct_answer: str
    explanation: Optional[str] = ""
    chart_data: _ChartData

    @field_validator("correct_answer", mode="before")
    @classmethod
    def _answer(cls, v):
        s = str(v or "1").strip()
        return s if s in {"1", "2", "3", "4", "5"} else "1"

    @field_validator("options", mode="before")
    @classmethod
    def _opts(cls, v):
        lst = [str(o).strip() for o in (v or [])]
        return lst if len(lst) == 5 else ["①", "②", "③", "④", "⑤"]


# -----------------------
# Spec
# -----------------------
class RC25Spec:
    id = "RC25"

    def __init__(self, *, auto_fix_answer: bool = True, llm_explain_on_fix: bool = True):
        """
        auto_fix_answer=True:
          - LLM 판정에서 false_count==1이고 false_index가 나왔는데
            correct_answer가 불일치하면, 예외 대신 정답/해설을 자동 보정하여 성공 처리.
        llm_explain_on_fix=True:
          - 정답을 보정할 때 해설을 LLM으로 간결하게 재작성(한국어, 1~3문장).            
        auto_fix_answer=False:
          - 불일치 시 예외를 던져 item_generator의 regenerate 경로로 보냄.
        """
        self.auto_fix_answer = auto_fix_answer
        self.llm_explain_on_fix = llm_explain_on_fix

    # -------- Prompt (생성용) --------
    def system_prompt(self) -> str:
        return (
            "CSAT English RC25 (Chart/Graph Analysis + MCQ). "
            "Return ONLY JSON with fields: {question, passage, options[5], correct_answer(1..5 as string), "
            "explanation, chart_data:{type, title, labels[], datasets:[{label, data[]}]}}. "
            "No markdown."
        )

    def build_prompt(self, ctx: GenContext) -> str:
        return PromptManager.generate(
            item_type=(ctx.get("item_id") or self.id),
            difficulty=(ctx.get("difficulty") or "medium"),
            topic_code=(ctx.get("topic") or "random"),
            passage=(ctx.get("passage") or ""),
            vocab_profile=ctx.get("vocab_profile"),
            enable_overlay=bool(ctx.get("enable_overlay", True)),
        )

    # -------- Normalize / helpers --------
    def _normalize_chart(self, chart: dict) -> dict:
        cd = dict(chart or {})
        cd["type"] = str(cd.get("type") or "bar").strip().lower()

        labels = cd.get("labels")
        if isinstance(labels, str):
            labels = [p.strip() for p in labels.replace(",", "\n").splitlines() if p.strip()]
        else:
            labels = [str(x).strip() for x in (labels or [])]
        L = len(labels)
        if L == 0:
            labels = ["X1", "X2"]; L = 2
        elif L == 1:
            labels = [labels[0], f"{labels[0]}_2"]; L = 2

        ds_in = cd.get("datasets") or []
        if not isinstance(ds_in, list):
            ds_in = [ds_in]

        norm: List[dict] = []
        for i, ds in enumerate(ds_in):
            if isinstance(ds, dict):
                lab = str(ds.get("label") or f"Series {i+1}").strip()
                data_raw = ds.get("data") or []
            else:
                lab = f"Series {i+1}"
                data_raw = ds
            data_raw = data_raw if isinstance(data_raw, list) else [data_raw]

            vals: List[float] = []
            for v in data_raw:
                try:
                    vals.append(float(v))
                except Exception:
                    vals.append(0.0)

            if len(vals) < L:
                vals = vals + [0.0] * (L - len(vals))
            elif len(vals) > L:
                vals = vals[:L]
            norm.append({"label": lab, "data": vals})

        if not norm:
            norm = [{"label": "Series 1", "data": [0.0] * L}]

        cd["labels"] = labels
        cd["datasets"] = norm
        return cd

    def _split_statements(self, passage: str) -> list[str]:
        text = passage or ""
        marks = [m.start() for m in re.finditer(r"[①②③④⑤]", text)]
        if len(marks) < 5:
            return []
        idxs = marks[:5] + [len(text)]
        segs = []
        for i in range(5):
            start = idxs[i] + 1
            end = idxs[i + 1]
            seg = re.sub(r"\s+", " ", text[start:end].strip())
            segs.append(seg)
        return segs

    def _bad_explanation(self, expl: str, fi: str) -> bool:
        """
        해설이 재작성 대상인지 판정:
        - 비어 있음 / 공백뿐
        - 템플릿 잔여물 ("{}", "[]") 포함
        - 정답 번호 표기 (e.g., "(3)")가 누락
        """
        if not expl or not str(expl).strip():
            return True
        s = str(expl).strip()
        if "{}" in s or "[]" in s:
            return True
        return f"({fi})" not in s
    
    # -------- Public: normalize (필수) --------
    def normalize(self, data: dict) -> dict:
        d = coerce_mcq_like(data or {})
        for k in ("question", "passage", "explanation"):
            if k in d:
                d[k] = str(d.get(k) or "").strip()

        opts = d.get("options")
        d["options"] = [str(x).strip() for x in opts] if (isinstance(opts, list) and len(opts) == 5) \
            else ["①", "②", "③", "④", "⑤"]

        try:
            iv = int(str(d.get("correct_answer", "1")).strip())
            d["correct_answer"] = str(iv if 1 <= iv <= 5 else 1)
        except Exception:
            d["correct_answer"] = "1"

        d["chart_data"] = self._normalize_chart(d.get("chart_data") or {})
        return d

    # -------- Fast precheck (값싼 컷; 실패 시 재생성 유도) --------
    def fast_precheck(self, d: dict) -> Tuple[bool, str]:
        cd = d.get("chart_data") or {}
        labels = cd.get("labels") or []
        datasets = cd.get("datasets") or []
        if not (isinstance(labels, list) and isinstance(datasets, list) and len(labels) >= 2 and len(datasets) >= 1):
            return False, "chart_minimal_structure"
        if len(self._split_statements(d.get("passage", ""))) != 5:
            return False, "need_five_numbered_statements"
        return True, "ok"

    # ---------------- LLM judge ----------------
    def _judge_prompt(self, statements: list[str], chart_data: dict) -> list[dict]:
        system = (
            "You are a strict CSAT RC25 verifier.\n"
            "You are given a chart (labels + datasets) and EXACTLY FIVE statements (①~⑤), already split.\n"
            "Decide which ONE statement is FALSE.\n"
            "Strict semantics:\n"
            "- 'steady increase' = strictly increases every year (no flat years).\n"
            "- 'remained unchanged' = exactly equal values across the referenced years.\n"
            "- 'double (twice)' = exactly 2x, not approximately.\n"
            "- 'lowest/highest/second-highest' = compare precise values; ties mean NOT strictly lowest/highest.\n"
            "- 'never exceeding X%' = strictly <= X% for all referenced years.\n"
            "Return JSON only: {\"truth\":[bool,bool,bool,bool,bool],\"false_index\":\"1..5\",\"reason\":\"brief English reason\"}"
        )
        payload = {"statements": statements, "chart_data": chart_data}
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
    
    def _explain_prompt(self, false_index: str, statements: list[str], chart_data: dict, judged_reason: str) -> list[dict]:
        """
        해설 재작성용 프롬프트: 한국어 1~3문장, 번호 일치, 표의 연/값 비교를 짧게 근거 제시.
        """
        system = (
            "당신은 한국 수능 영어 RC25 해설 작성자입니다.\n"
            "입력으로 도표(chart_data)와 5개의 진술(statements), 그리고 판정 결과로 나온 거짓 문항 번호(false_index)와 간단한 영어 이유(reason)가 주어집니다.\n"
            "한국어로 1~3문장, 간결하고 정확하게 해설을 쓰세요. 반드시 번호를 (3)처럼 표기하고, 표의 연도/수치를 간단히 언급해 근거를 제시하세요.\n"
            "불필요한 수사, 마크다운, 목록 금지. 도표에 없는 정보는 추론하지 마세요."
        )
        user_payload = {
            "false_index": false_index,
            "statements": statements,
            "chart_data": chart_data,
            "reason": judged_reason or ""
        }
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]

    async def _make_explanation_with_llm(self, false_index: str, statements: list[str], chart_data: dict, judged_reason: str, fallback_reason_ko: str = "") -> str:
        """
        LLM으로 해설을 짧게 생성. 실패 시 템플릿으로 백업.
        """
        try:
            messages = self._explain_prompt(false_index, statements, chart_data, judged_reason)
            # ⬇️ 해설은 "텍스트"를 기대하므로 parse_json=False
            text = await self._call_llm(messages, timeout_s=12.0, parse_json=False)
            text = (text or "").strip()
            if not text:
                raise ValueError("empty_explanation")
            # (선택) 번호 강제 포함 보정
            if f"({false_index})" not in text:
                text = f"The incorrect statement is ({false_index}). " + text
            return text
        except Exception:
            # 템플릿 백업(판정 reason 활용)
            base = f"The incorrect statement is ({false_index})."
            if fallback_reason_ko:
                return f"{base} {fallback_reason_ko}"
            return base    

    async def _call_llm(self, messages: list[dict], timeout_s: float = 16.0, parse_json: bool = True):
        """
        - parse_json=True: JSON 응답을 기대(판정/아이템 생성 경로)
        - parse_json=False: '순수 텍스트'를 기대(해설 생성 경로)
        """
        try:
            maybe = openai_config.chat_completion(messages=messages, timeout_s=timeout_s, trace_id=None)
        except TypeError:
            maybe = openai_config.chat_completion(messages)
        if asyncio.iscoroutine(maybe):
            raw = await asyncio.wait_for(maybe, timeout=timeout_s)
        else:
            loop = asyncio.get_running_loop()
            raw = await asyncio.wait_for(loop.run_in_executor(None, lambda: maybe), timeout=timeout_s)

        # raw → content 문자열
        if isinstance(raw, dict):
            content = raw.get("content") or raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            content = str(raw or "")

        if not parse_json:
            # 해설 경로: 파싱 없이 텍스트 그대로 반환
            return content

        # JSON 경로: content를 JSON으로 파싱
        try:
            return json.loads(content)
        except Exception:
            m = re.search(r"\{[\s\S]*\}\s*$", content)
            return json.loads(m.group(0)) if m else {}

    # -------- Local safeguard: 쉬운 거짓 후보 탐색 --------
    def _local_false_candidates(self, statements: list[str], chart: dict) -> list[int]:
        labels = chart.get("labels") or []
        datasets = chart.get("datasets") or []
        name_to_series = { (ds.get("label") or "").strip().lower(): ds for ds in datasets }

        def series(name: str):
            return name_to_series.get((name or "").strip().lower())

        false_idx = []

        for i, s in enumerate(statements):
            tl = s.strip().lower()

            # 'X doubled from YEAR to YEAR' (정확히 2배가 아닐 때 거짓)
            m = re.search(
                r"(?P<label>[a-z0-9–\- ._/]+?)\s+(?:has|had|was|were|showed|shows|with)?\s*"
                r"(?:doubled|double[d]?)\s+from\s+(?P<y1>\d{4})\s+to\s+(?P<y2>\d{4})",
                tl
            )
            if m and all(_RE_YEAR4.fullmatch(l or "") for l in labels):
                grp = (m.group("label") or "").strip().lower()
                y1, y2 = m.group("y1"), m.group("y2")
                if (y1 in labels) and (y2 in labels):
                    ix1, ix2 = labels.index(y1), labels.index(y2)
                    dsA = series(grp)
                    if dsA:
                        try:
                            v1 = float(dsA["data"][ix1]); v2 = float(dsA["data"][ix2])
                            if not (abs(v2 - 2.0 * v1) <= 1e-9):
                                false_idx.append(i)
                        except Exception:
                            pass

            # 'X showed a steady increase' (모든 연도에서 엄밀 증가가 아닐 때 거짓)
            m = re.search(
                r"(?P<label>[a-z0-9–\- ._/]+?)\s+(?:has|had|was|were|showed|shows|with)?\s*"
                r"(?:a\s+)?steady\s+increase",
                tl
            )
            if m and labels and datasets:
                grp = (m.group("label") or "").strip().lower()
                dsA = series(grp)
                if dsA:
                    try:
                        vals = [float(v) for v in dsA["data"][:len(labels)]]
                        strictly_inc = all(vals[j] > vals[j-1] for j in range(1, len(vals)))
                        if not strictly_inc:
                            false_idx.append(i)
                    except Exception:
                        pass

            # unchanged between YEAR and YEAR
            m = re.search(r"(?:unchanged|same).*?(?P<y1>\d{4}).*?(?:and|to)\s*(?P<y2>\d{4})", tl)
            if m and all(_RE_YEAR4.fullmatch(l or "") for l in labels):
                y1, y2 = m.group("y1"), m.group("y2")
                if y1 in labels and y2 in labels:
                    ix1, ix2 = labels.index(y1), labels.index(y2)
                    same_all = True
                    for ds in datasets:
                        if float(ds["data"][ix1]) != float(ds["data"][ix2]):
                            same_all = False
                            break
                    if not same_all:
                        false_idx.append(i)

            # 'A is twice B in YEAR'
            m = re.search(r"(?P<a>[a-z][a-z0-9 ._-]*)\s+(?:is|was)\s+(?:twice|double)\s+(?P<b>[a-z][a-z0-9 ._-]*)\s+in\s+(?P<y>\d{4})", tl)
            if m and all(_RE_YEAR4.fullmatch(l or "") for l in labels):
                A, B, Y = m.group("a"), m.group("b"), m.group("y")
                if Y in labels and series(A) and series(B):
                    ix = labels.index(Y)
                    va = float(series(A)["data"][ix]); vb = float(series(B)["data"][ix])
                    if vb == 0 or abs(va / vb - 2.0) > 1e-9:
                        false_idx.append(i)

            # lowest / highest / second-highest in YEAR
            if ("lowest" in tl) or ("second-highest" in tl) or ("highest" in tl):
                m = re.search(r"in\s+(?P<y>\d{4})", tl)
                if m and m.group("y") in labels:
                    iy = labels.index(m.group("y"))
                    vals = [(ds["label"], float(ds["data"][iy])) for ds in datasets]
                    mentioned = None
                    for ds_name, v in vals:
                        if ds_name and ds_name.strip().lower() in tl:
                            mentioned = (ds_name, v)
                            break
                    if mentioned:
                        ds_name, v = mentioned
                        vs = [x[1] for x in vals]
                        if "lowest" in tl and v != min(vs):
                            false_idx.append(i)
                        if "highest" in tl and v != max(vs):
                            false_idx.append(i)
                        if "second-highest" in tl:
                            sorted_vals = sorted(vals, key=lambda x: x[1], reverse=True)
                            if ds_name != sorted_vals[1][0]:
                                false_idx.append(i)

            # 'never exceeding X%'
            m = re.search(r"never exceeding\s*(?P<x>\d+(?:\.\d+)?)\s*%", tl)
            if m:
                try:
                    x = float(m.group("x"))
                    for ds in datasets:
                        key = (ds["label"] or "").strip().lower()
                        if key and key in tl:
                            if any(float(v) > x for v in ds["data"]):
                                false_idx.append(i)
                            break
                except Exception:
                    pass

        return sorted(set(false_idx))

    # -------- Content-first generate (내부 재생성/자가수정 루프) --------
    async def content_first_generate(self, ctx: GenContext) -> dict:
        """
        1) 1차 생성 (PromptManager)
        2) 문장 분리 + LLM 판정 → 실패면 강화프롬프트로 재생성(최대 3회)
        3) 그래도 실패면 예외를 던져 상위(item_generator)의 재생성 루프로 위임
        4) 정상일 때 normalize 후 반환 (정답은 판정값으로 세팅)
        """
        max_rounds = 3

        def _gen_prompt(hard: bool = False) -> str:
            base = PromptManager.generate(
                item_type=(ctx.get("item_id") or self.id),
                difficulty=(ctx.get("difficulty") or "medium"),
                topic_code=(ctx.get("topic") or "random"),
                passage=(ctx.get("passage") or ""),
                vocab_profile=ctx.get("vocab_profile"),
                enable_overlay=bool(ctx.get("enable_overlay", True)),
            )
            if not hard:
                return base
            add = (
                "\n\n[STRICT RC25 RULE]\n"
                "- Exactly ONE statement among ①~⑤ must be false. Others must be strictly true to the chart.\n"
                "- Prefer keeping ① as the false statement if possible.\n"
                "- Use precise terms: 'steady increase' means strictly increasing each year; 'double' means exactly 2x; "
                "'lowest/highest/second-highest' require strict ordering (ties invalidate strictness).\n"
            )
            return base + add

        async def _judge_ok(item: dict) -> Tuple[bool, str, str]:
            """(ok, false_index, reason)"""
            d = self.normalize(item)
            if self.fast_precheck(d)[0] is False:
                return (False, "", "fast_precheck_failed")
            stmts = self._split_statements(d.get("passage", ""))
            judged = await self._call_llm(self._judge_prompt(stmts, d.get("chart_data") or {}), timeout_s=16.0, parse_json=True)
            truth = judged.get("truth", [])
            fi = str(judged.get("false_index", "")).strip()
            if not (isinstance(truth, list) and len(truth) == 5 and fi in {"1","2","3","4","5"}):
                return (False, "", "judge_shape_invalid")
            if sum(1 for t in truth if not t) != 1:
                return (False, "", "false_count!=1")
            local_false = self._local_false_candidates(stmts, d.get("chart_data") or {})
            if len(local_false) >= 2:
                return (False, "", f"local_conflict:{local_false}")
            return (True, fi, (judged.get("reason", "") or "").strip())

        # 1) 1차 생성
        prompt1 = _gen_prompt(hard=False)
        item_raw = await self._call_llm(
            messages=[
                {"role": "system", "content": "CSAT English item generator. Return ONLY JSON."},
                {"role": "user", "content": prompt1},
            ],
            timeout_s=18.0,
            parse_json=True,
        )
        try:
            obj = item_raw if isinstance(item_raw, dict) else json.loads(
                re.search(r"\{[\s\S]*\}\s*$", str(item_raw)).group(0)
            )
        except Exception:
            obj = {}

        ok, fi, reason = await _judge_ok(obj)
        round_no = 0
        while (not ok) and round_no < max_rounds:
            round_no += 1
            prompt_hard = _gen_prompt(hard=True)
            regen = await self._call_llm(
                messages=[
                    {"role": "system", "content": "CSAT English item generator. Return ONLY JSON."},
                    {"role": "user", "content": prompt_hard},
                ],
                timeout_s=18.0,
                parse_json=True,
            )
            try:
                obj = regen if isinstance(regen, dict) else json.loads(
                    re.search(r"\{[\s\S]*\}\s*$", str(regen)).group(0)
                )
            except Exception:
                obj = {}
            ok, fi, reason = await _judge_ok(obj)

        if ok:
            obj = self.normalize(obj)
            obj["correct_answer"] = fi
            stmts = self._split_statements(obj.get("passage", ""))
            # 해설이 비었거나/번호 불일치/템플릿 잔여물("{}" 등) → LLM 재작성
            needs_expl = self._bad_explanation(obj.get("explanation", ""), fi)
            if needs_expl:
                # 간단 한국어 백업 사유(영→한 간단 변환; 여기서는 최소한의 템플릿만)
                fallback_ko = ""
                try:
                    if reason:
                        # 간단 매핑(영문 reason을 그대로 붙여도 되지만, 한국어 백업용은 비워둠)
                        fallback_ko = f"도표에서 해당 연도의 수치 변화를 보면 진술과 불일치합니다."
                except Exception:
                    pass
                if self.llm_explain_on_fix:
                    obj["explanation"] = await self._make_explanation_with_llm(fi, stmts, obj.get("chart_data") or {}, reason, fallback_reason_ko=fallback_ko)
                else:
                    obj["explanation"] = f"The incorrect statement is ({fi})."
            return obj

        # 3) 여전히 실패라면, 자동 보정 없이 상위 재생성 루프로 위임
        raise ValueError("llm_content_invalid_after_regen")

    # -------- Public: validate (엄격 + 자동 보정 옵션) --------
    async def validate(self, data: dict, content_only: bool = False):
        """
        - normalize → RC25Model(형식 확인)
        - fast_precheck 실패 시 예외 → item_generator가 리젠
        - LLM 판정(문장 배열 전달):
            * false_count != 1 → 예외 → 리젠
            * (옵션) correct_answer != false_index:
                - auto_fix_answer=True → 정답/해설을 자동 보정하고 성공 처리
                - auto_fix_answer=False → 예외 → 리젠
        - 로컬 세이프가드: 거짓 후보가 2개 이상이면 예외 → 리젠
        """
        d = self.normalize(data)
        RC25Model.model_validate(d)

        if content_only:
            return d

        ok, reason = self.fast_precheck(d)
        if not ok:
            raise ValueError(f"fast_precheck_failed:{reason}")

        statements = self._split_statements(d.get("passage", ""))
        chart = d.get("chart_data") or {}

        judged = await self._call_llm(self._judge_prompt(statements, chart), timeout_s=16.0, parse_json=True)
        truth = judged.get("truth", [])
        fi = str(judged.get("false_index", "")).strip()
        reason_txt = (judged.get("reason", "") or "").strip()

        if not (isinstance(truth, list) and len(truth) == 5):
            raise ValueError("llm_invalid_truth_array")

        false_count = sum(1 for t in truth if not t)
        if fi not in {"1", "2", "3", "4", "5"}:
            raise ValueError("llm_missing_false_index")

        local_false = self._local_false_candidates(statements, chart)
        if len(local_false) >= 2:
            raise ValueError(f"local_content_conflict:false_candidates={local_false}")

        if false_count != 1:
            raise ValueError(f"llm_content_invalid:false_count={false_count}")

        # ---- 신규: 정답/해설 자동 보정 분기 ----
        if d["correct_answer"] != fi:
            if self.auto_fix_answer:
                d["correct_answer"] = fi
                # 해설 재작성 필요 판단: 없음/번호 불일치/템플릿 잔여물("{}" 등)
                needs_rewrite = self._bad_explanation(d.get("explanation", ""), fi)
                if needs_rewrite:
                    # 간단 한국어 백업 사유
                    fallback_ko = ""
                    try:
                        if reason_txt:
                            fallback_ko = "도표 수치를 비교하면 해당 진술이 그래프와 일치하지 않습니다."
                    except Exception:
                        pass
                    if self.llm_explain_on_fix:
                        d["explanation"] = await self._make_explanation_with_llm(fi, statements, chart, reason_txt, fallback_reason_ko=fallback_ko)
                    else:
                        d["explanation"] = f"The incorrect statement is ({fi})." + (f" Reason: {reason_txt}" if reason_txt else "")
            else:
                raise ValueError(f"correct_answer_mismatch: expected {fi}, got {d['correct_answer']}")

        # 해설 기본 채움/검증(번호 누락/템플릿 잔여물 포함 시 재작성)
        if self._bad_explanation(d.get("explanation", ""), fi):
            if self.llm_explain_on_fix:
                d["explanation"] = await self._make_explanation_with_llm(fi, statements, chart, reason_txt)
            else:
                d["explanation"] = f"The incorrect statement is ({fi})." + (f" Reason: {reason_txt}" if reason_txt else "")

        return d

    # -------- Meta --------
    def json_schema(self) -> dict:
        return RC25Model.model_json_schema()

    def repair_budget(self) -> dict:
        # content-first가 먼저 시도되고, validate는 auto-fix로 마감 가능하므로 외부 regen은 2회면 충분
        return {"fixer": 0, "regen": 2, "timeout_s": 20}
