# app/specs/rc25_graph_info.py
from __future__ import annotations
import asyncio, json, re
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
class RC25Spec:
    id = "RC25"

    def __init__(self, *, auto_fix_answer: bool = True, llm_explain_on_fix: bool = True):
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
            labels = ["X1", "X2"]
            L = 2
        elif L == 1:
            labels = [labels[0], f"{labels[0]}_2"]
            L = 2

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
                vals += [0.0] * (L - len(vals))
            elif len(vals) > L:
                vals = vals[:L]
            norm.append({"label": lab, "data": vals})
        if not norm:
            norm = [{"label": "Series 1", "data": [0.0] * L}]
        cd["labels"], cd["datasets"] = labels, norm
        return cd

    def _split_statements(self, passage: str) -> list[str]:
        text = passage or ""
        marks = [m.start() for m in re.finditer(r"[①②③④⑤]", text)]
        if len(marks) < 5:
            return []
        idxs = marks[:5] + [len(text)]
        segs = []
        for i in range(5):
            start, end = idxs[i] + 1, idxs[i + 1]
            segs.append(re.sub(r"\s+", " ", text[start:end].strip()))
        return segs

    def _bad_explanation(self, expl: str, fi: str) -> bool:
        if not expl or not str(expl).strip():
            return True
        s = str(expl).strip()
        if "{}" in s or "[]" in s:
            return True
        return f"({fi})" not in s

    # -------- normalize --------
    def normalize(self, data: dict) -> dict:
        d = coerce_mcq_like(data or {})
        for k in ("question", "passage", "explanation"):
            if k in d:
                d[k] = str(d.get(k) or "").strip()
        opts = d.get("options")
        d["options"] = (
            [str(x).strip() for x in opts]
            if (isinstance(opts, list) and len(opts) == 5)
            else ["①", "②", "③", "④", "⑤"]
        )
        try:
            iv = int(str(d.get("correct_answer", "1")).strip())
            d["correct_answer"] = str(iv if 1 <= iv <= 5 else 1)
        except Exception:
            d["correct_answer"] = "1"
        d["chart_data"] = self._normalize_chart(d.get("chart_data") or {})
        return d

    # -------- Fast precheck --------
    def fast_precheck(self, d: dict) -> Tuple[bool, str]:
        cd = d.get("chart_data") or {}
        labels, datasets = cd.get("labels") or [], cd.get("datasets") or []
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

    def _explain_prompt(
        self,
        false_index: str,
        statements: list[str],
        chart_data: dict,
        judged_reason: str,
    ) -> list[dict]:
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
            "reason": judged_reason or "",
        }
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]

    async def _make_explanation_with_llm(
        self,
        false_index: str,
        statements: list[str],
        chart_data: dict,
        judged_reason: str,
        fallback_reason_ko: str = "",
    ) -> str:
        """
        LLM으로 해설을 짧게 생성. 실패 시 템플릿으로 백업.
        """
        try:
            messages = self._explain_prompt(false_index, statements, chart_data, judged_reason)
            text = await self._call_llm(messages, timeout_s=12.0, parse_json=False)
            text = (text or "").strip()
            if not text:
                raise ValueError("empty_explanation")
            if f"({false_index})" not in text:
                text = f"The incorrect statement is ({false_index}). " + text
            return text
        except Exception:
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

        if isinstance(raw, dict):
            content = raw.get("content") or raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            content = str(raw or "")

        if not parse_json:
            return content

        try:
            return json.loads(content)
        except Exception:
            m = re.search(r"\{[\s\S]*\}\s*$", content)
            return json.loads(m.group(0)) if m else {}

    # -------- Local safeguard: 쉬운 거짓 후보 탐색 --------
    def _local_false_candidates(self, statements: list[str], chart: dict) -> list[int]:
        labels = chart.get("labels") or []
        datasets = chart.get("datasets") or []
        name_to_series = {(ds.get("label") or "").strip().lower(): ds for ds in datasets}

        def series(name: str):
            return name_to_series.get((name or "").strip().lower())

        false_idx = []

        for i, s in enumerate(statements):
            tl = s.strip().lower()

            # 'X doubled from YEAR to YEAR'
            m = re.search(
                r"(?P<label>[a-z0-9–\- ._/]+?)\s+(?:has|had|was|were|showed|shows|with)?\s*"
                r"(?:doubled|double[d]?)\s+from\s+(?P<y1>\d{4})\s+to\s+(?P<y2>\d{4})",
                tl,
            )
            if m and all(_RE_YEAR4.fullmatch(l or "") for l in labels):
                grp = (m.group("label") or "").strip().lower()
                y1, y2 = m.group("y1"), m.group("y2")
                if (y1 in labels) and (y2 in labels):
                    ix1, ix2 = labels.index(y1), labels.index(y2)
                    dsA = series(grp)
                    if dsA:
                        try:
                            v1 = float(dsA["data"][ix1])
                            v2 = float(dsA["data"][ix2])
                            if not (abs(v2 - 2.0 * v1) <= 1e-9):
                                false_idx.append(i)
                        except Exception:
                            pass

            # 'X showed a steady increase'
            m = re.search(
                r"(?P<label>[a-z0-9–\- ._/]+?)\s+(?:has|had|was|were|showed|shows|with)?\s*"
                r"(?:a\s+)?steady\s+increase",
                tl,
            )
            if m and labels and datasets:
                grp = (m.group("label") or "").strip().lower()
                dsA = series(grp)
                if dsA:
                    try:
                        vals = [float(v) for v in dsA["data"][: len(labels)]]
                        strictly_inc = all(vals[j] > vals[j - 1] for j in range(1, len(vals)))
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
            m = re.search(
                r"(?P<a>[a-z][a-z0-9 ._-]*)\s+(?:is|was)\s+(?:twice|double)\s+(?P<b>[a-z][a-z0-9 ._-]*)\s+in\s+(?P<y>\d{4})",
                tl,
            )
            if m and all(_RE_YEAR4.fullmatch(l or "") for l in labels):
                A, B, Y = m.group("a"), m.group("b"), m.group("y")
                if Y in labels and series(A) and series(B):
                    ix = labels.index(Y)
                    va = float(series(A)["data"][ix])
                    vb = float(series(B)["data"][ix])
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
            d = self.normalize(item)
            if self.fast_precheck(d)[0] is False:
                return False, "", "fast_precheck_failed"
            stmts = self._split_statements(d.get("passage", ""))
            judged = await self._call_llm(
                self._judge_prompt(stmts, d.get("chart_data") or {}), timeout_s=16.0, parse_json=True
            )
            truth = judged.get("truth", [])
            fi = str(judged.get("false_index", "")).strip()
            if not (isinstance(truth, list) and len(truth) == 5 and fi in {"1", "2", "3", "4", "5"}):
                return False, "", "judge_shape_invalid"
            if sum(1 for t in truth if not t) != 1:
                return False, "", "false_count!=1"
            local_false = self._local_false_candidates(stmts, d.get("chart_data") or {})
            if len(local_false) >= 2:
                return False, "", f"local_conflict:{local_false}"
            return True, fi, (judged.get("reason", "") or "").strip()

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
            needs_expl = self._bad_explanation(obj.get("explanation", ""), fi)

            if needs_expl:
                fallback_ko = ""
                try:
                    if reason:
                        fallback_ko = "도표에서 해당 연도의 수치 변화를 보면 진술과 불일치합니다."
                except Exception:
                    pass

                if self.llm_explain_on_fix:
                    obj["explanation"] = await self._make_explanation_with_llm(
                        fi,
                        stmts,
                        obj.get("chart_data") or {},
                        reason,
                        fallback_reason_ko=fallback_ko,
                    )
                else:
                    obj["explanation"] = f"The incorrect statement is ({fi})."

            return obj  # ✅ if ok 블록 안에서 리턴

        # ✅ while 루프 다 돌았는데도 ok가 안 된 경우에만 이 예외 발생
        raise ValueError("llm_content_invalid_after_regen")

    # -------- Public: validate (엄격 + 자동 보정 옵션) --------
    async def validate(self, data: dict, content_only: bool = False):
        d = self.normalize(data)
        RC25Model.model_validate(d)

        if content_only:
            return d

        ok, reason = self.fast_precheck(d)
        if not ok:
            raise ValueError(f"fast_precheck_failed:{reason}")

        statements = self._split_statements(d.get("passage", ""))
        chart = d.get("chart_data") or {}

        judged = await self._call_llm(
            self._judge_prompt(statements, chart), timeout_s=16.0, parse_json=True
        )
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

        if d["correct_answer"] != fi:
            if self.auto_fix_answer:
                d["correct_answer"] = fi
                needs_rewrite = self._bad_explanation(d.get("explanation", ""), fi)
                if needs_rewrite:
                    fallback_ko = ""
                    try:
                        if reason_txt:
                            fallback_ko = "도표 수치를 비교하면 해당 진술이 그래프와 일치하지 않습니다."
                    except Exception:
                        pass
                    if self.llm_explain_on_fix:
                        d["explanation"] = await self._make_explanation_with_llm(
                            fi, statements, chart, reason_txt, fallback_reason_ko=fallback_ko
                        )
                    else:
                        d["explanation"] = (
                            f"The incorrect statement is ({fi})."
                            + (f" Reason: {reason_txt}" if reason_txt else "")
                        )
            else:
                raise ValueError(
                    f"correct_answer_mismatch: expected {fi}, got {d['correct_answer']}"
                )

        if self._bad_explanation(d.get("explanation", ""), fi):
            if self.llm_explain_on_fix:
                d["explanation"] = await self._make_explanation_with_llm(
                    fi, statements, chart, reason_txt
                )
            else:
                d["explanation"] = (
                    f"The incorrect statement is ({fi})."
                    + (f" Reason: {reason_txt}" if reason_txt else "")
                )

        return d

    # -------- Meta --------
    def json_schema(self) -> dict:
        return RC25Model.model_json_schema()

    def repair_budget(self) -> dict:
        return {"fixer": 0, "regen": 2, "timeout_s": 20}

    # ===== quote 모드 지원 =====
    def has_quote_support(self) -> bool:
        return True

    def quote_build_prompt(self, passage: str) -> str:
        """
        인용 모드 전용 프롬프트.
        - 원본 PASSAGE 텍스트는 '절대' 수정/삭제/재배열 금지.
        - ①~⑤가 없으면, '선택지로 사용할 다섯 문장' 앞에만 ①~⑤를 추가한다.
        - 이미 ①~⑤가 있다면, 새로 추가/삭제하지 말고 그대로 둔다.
        - 그 외의 글자/띄어쓰기는 변경하지 않는다.
        """
        return (
            "You are generating a CSAT English RC25 item (chart/graph-based NOT-true question) in QUOTE mode.\n"
            "\n"
            "STRICT QUOTE MODE RULES:\n"
            "1) You are given a PASSAGE that MUST be preserved EXACTLY.\n"
            "   - DO NOT paraphrase, translate, reorder, insert, or delete any words or sentences.\n"
            "   - The ONLY allowed modification is to INSERT the circled numerals ①, ②, ③, ④, ⑤\n"
            "     immediately BEFORE five sentences that will serve as the options.\n"
            "   - If the passage already contains any of ①~⑤, DO NOT remove or move them.\n"
            "2) After your edit, each of ①, ②, ③, ④, ⑤ must appear EXACTLY ONCE in the passage.\n"
            "3) Apart from these numerals, every other character (including spacing and line breaks)\n"
            "   must remain identical to the original PASSAGE.\n"
            "4) Use the information in the passage to design a chart_data object and one false statement among ①~⑤.\n"
            "\n"
            "OUTPUT FORMAT (JSON ONLY):\n"
            "{\n"
            '  \"question\": \"...\",  // Korean question (e.g. \"다음 도표의 내용과 일치하지 <u>않는</u> 것은?\")\n'
            '  \"passage\": \"...\",   // Original passage, only with ①~⑤ inserted before five option sentences\n'
            '  \"options\": [\"①\",\"②\",\"③\",\"④\",\"⑤\"],\n'
            '  \"correct_answer\": \"1\"..\"5\" as string,\n'
            '  \"explanation\": \"...\", // Korean explanation mentioning the wrong option like (3)\n'
            "  \"chart_data\": {\n"
            "     \"type\": \"bar\" | \"line\" | \"...\",\n"
            "     \"title\": \"...\",\n"
            "     \"labels\": [ ... ],\n"
            "     \"datasets\": [ { \"label\": \"...\", \"data\": [ ... ] }, ... ]\n"
            "  }\n"
            "}\n"
            "\n"
            "Again: DO NOT CHANGE the PASSAGE text other than inserting ①~⑤ before five sentences.\n"
            "PASSAGE (to preserve):\n"
            + (passage or "")
        )

    def quote_postprocess(self, passage: str, llm_json: dict) -> dict:
        """
        - LLM이 반환한 JSON을 normalize + 검증.
        - passage에서 ①~⑤를 제거하면 '원본 passage'와 동일해야 한다는 조건을 강제.
        """
        obj = self.normalize(llm_json or {})
        p_new = obj.get("passage") or ""
        p_orig = passage or ""

        # ①~⑤ 개수 검사
        counts = [
            len(re.findall(r"①", p_new)),
            len(re.findall(r"②", p_new)),
            len(re.findall(r"③", p_new)),
            len(re.findall(r"④", p_new)),
            len(re.findall(r"⑤", p_new)),
        ]
        if not all(c == 1 for c in counts):
            raise ValueError(f"RC25(quote): each numeral ①~⑤ must appear exactly once, got {counts}")

        # ①~⑤ 제거 후 원본 passage와 동일한지 검사(공백만 정규화)
        def _norm_text(s: str) -> str:
            # circled numerals 제거 + 연속 공백 정규화
            s = re.sub(r"[①②③④⑤]", "", s)
            s = re.sub(r"\s+", " ", s)
            return s.strip()

        if _norm_text(p_new) != _norm_text(p_orig):
            raise ValueError("RC25(quote): passage text must be identical to original except for ①~⑤ inserts")

        # options / correct_answer 보정
        obj["options"] = ["①", "②", "③", "④", "⑤"]
        ca = str(obj.get("correct_answer", "1")).strip()
        obj["correct_answer"] = ca if ca in {"1", "2", "3", "4", "5"} else "1"

        # fast_precheck (5개 문장 분리 + chart 최소 구조)
        ok, reason = self.fast_precheck(obj)
        if not ok:
            raise ValueError(f"RC25(quote): fast_precheck failed: {reason}")

        return obj

    def quote_validate(self, item: dict) -> None:
        """
        quote 모드 최종 검증:
        - options, correct_answer 형식 확인
        - passage 안 ①~⑤ 각 1회
        - _split_statements 결과 5개 문장
        - chart_data 최소 구조
        """
        assert item.get("options") == _CIRCLED, "RC25(quote): options must be ['①','②','③','④','⑤']"
        assert str(item.get("correct_answer")) in {"1", "2", "3", "4", "5"}, (
            "RC25(quote): correct_answer must be '1'..'5'"
        )

        p = item.get("passage") or ""
        counts = [
            len(re.findall(r"①", p)),
            len(re.findall(r"②", p)),
            len(re.findall(r"③", p)),
            len(re.findall(r"④", p)),
            len(re.findall(r"⑤", p)),
        ]
        if not all(c == 1 for c in counts):
            raise AssertionError(f"RC25(quote): passage must contain each numeral once, got {counts}")

        segs = self._split_statements(p)
        if len(segs) != 5:
            raise AssertionError("RC25(quote): must have 5 numbered statements")

        cd = item.get("chart_data") or {}
        labels, datasets = cd.get("labels") or [], cd.get("datasets") or []
        if not (isinstance(labels, list) and isinstance(datasets, list) and len(labels) >= 2 and len(datasets) >= 1):
            raise AssertionError("RC25(quote): chart_data minimal structure not satisfied")
