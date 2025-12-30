# app/prompts/router_prompt.py
from __future__ import annotations
from typing import Dict

"""
문항 '추천/라우팅' 전용 프롬프트.
- 생성 프롬프트(app/prompts/prompt_data.py)와 분리 유지!
- 출력은 항상 JSON ONLY.
- RC29/RC30 등 패턴 신호(①~⑤, <u>...</u>)를 강하게 반영.
"""

ROUTER_SYSTEM: str = (
    "You are a cautious, rule-abiding CSAT item-type recommender. "
    "Given a passage, you will recommend suitable RC types from a fixed whitelist. "
    "Never generate an item. Return JSON ONLY (no prose, no markdown). "
    "Be conservative in scoring; prefer precision over recall."
)

ROUTER_USER_TMPL: str = """[PASSAGE]
{passage}

[RC_WHITELIST]
RC18, RC19, RC20, RC21, RC22, RC23, RC24, RC25, RC26, RC27, RC28, RC29, RC30, RC31, RC32, RC33, RC34, RC35, RC36, RC37, RC38, RC39, RC40

[OUTPUT_FORMAT]  // STRICT JSON ONLY
{{
  "candidates": [
    {{
      "type": "RC22",              // must be in RC_WHITELIST
      "fit": 0.00 to 1.00,         // float; 2-decimals; higher is better
      "reason": "≤120 chars why this fits (signals/structure)",
      "prep_hint": "≤120 chars; actionable test-prep hint or '-'"
    }},
    ...
  ],
  "top": ["RC22","RC31","RC40"]   // best 1–5 types by fit (desc), subset of candidates
}}

[STRICTNESS & VALIDATION]
- DO NOT output anything except a single JSON object.
- All "type" must be unique and from RC_WHITELIST.
- "top" must be a subset of "candidates" (1–5 items), sorted by fit desc.
- Sort "candidates" by fit desc; include at most 12.
- Use 2 decimals for "fit" (e.g., 0.87). If uncertain, lower the score.
- If nothing is ≥0.35, still return plausible 3–5 candidates with lower scores (e.g., 0.20–0.34), but never leave "top" empty.

[CLASSIFICATION RUBRIC]
Score by discourse/structure cues + explicit pattern signals. Penalize when cues conflict.
Use these strong signals (if present, consider RCs accordingly):

1) Pattern signals (very strong when present):
   - Circled numerals ①②③④⑤ or variants (1)~(5), ( ① )~( ⑤ ), ㉠~㉣.
   - Underline tags <u>...</u> or explicit "underlined".
   - Paragraph labels (A)(B)(C) or [A][B][C].
   - In some pipelines (quote mode), these markers may be removed by preprocessing.
     → Do NOT rely only on these; also use sentence structure and content.

2) Discourse/structure mapping (primary hints):
   - RC27/RC28: Notices/official forms (Title:, Date:, Location:, Eligibility:, Registration:, Fee:, Contact:).
   - RC25: Charts/tables/statistical descriptions with many numbers/percentages and comparisons.
     * Look for passages that describe data in graphs/tables: years (e.g., 1997 and 2017),
       percentages, ranks, or shares for multiple groups (countries, regions, age groups,
       rural vs. urban, etc.).
     * Give RC25 a high fit only when the passage already contains at least five distinct
       factual sentences that could each be used as an option without rewriting the passage.
       If there are fewer than five such sentences, lower the fit for RC25 or omit it.
     * Typical signals: “% / percentage points”, “ranked first/second/third”, “higher/lower
       than”, “among the countries”, “from YEAR to YEAR”, “in each age group”.
   - RC26: Biographical chronology; life events timeline.
   - RC22: Main idea/gist of an explanatory/analytical passage (what the passage mainly says about its topic).
   - RC23: Topic/theme of an explanatory/analytical passage with a single central concept developed throughout.
     * Use RC23 when the passage is an expository or analytical essay (not a letter, notice, or narrative),
       with no emotional journey and no clear sender/recipient, and the whole text is about one core idea
       explained with reasons, examples, or implications.
     * Pattern signals like ①~⑤, <u>…</u>, or (A)(B)(C) are NOT required for RC23. Even if such
       patterns are absent (or removed), still include RC23 if the discourse structure matches this description.
   - RC24: Appropriate title/heading for the whole passage (short phrase that captures the passage as a whole).
   - RC31: Single-core-concept word or short noun-phrase blank in an expository/analytical essay.
     * Use RC31 when the passage is a single-topic explanatory text (no letter/notice/biography/narrative),
       and removing ONE key concept word would create a clear semantic gap in the main argument.
     * Avoid RC31 for notices, letters, biographical timelines, emotional narratives, or texts with
       strong format markers for other types (①~⑤ options, ( ① ) insertion anchors, (A)(B)(C) labels, etc.).
   - RC32: Phrase/clause-level blanks where the missing span is local (within one sentence) and mainly encodes
     a simple relation such as cause–effect, contrast, or example.
   - RC33: Higher-difficulty phrase/clause-level blanks where the missing span controls a key logical link
     (e.g., summary of previous content, turning point, or abstract generalization).
   - RC34: High-difficulty phrase/clause blank in a relatively long expository essay (≈150–260 words), where
     the blanked span is a mid-passage pivot or bridge clause (e.g., in turn / it follows that / however / thus).
     * Even if the original passage has NO blank, still consider RC34 when you could remove exactly ONE such
       pivot/bridge span and create a challenging blank.
   - RC40: AB-type summary items, where two short noun phrases (A) and (B) capture the core content
     of the passage in a paired way.
     * Use RC40 especially when the passage is a single-topic expository text that can naturally be
       summarized as TWO complementary or contrasting aspects (e.g., limitation vs. compensation,
       problem vs. solution, cause vs. result, traditional view vs. new view).
     * Prefer RC40 when the author repeatedly contrasts or pairs two ideas (both A and B, not only A
       but B, while A, B, whereas A, B, etc.), and each of these can be named by a short noun phrase.
     * Avoid RC40 for notices, letters, biographical timelines, short narratives with emotional change,
       or texts that are already better served by charts/sets or blank types.
   - RC18: Purpose/intent of formal letter/notice/email.
     * Strong signals: greetings like "Dear Mr. Smith,", "To whom it may concern,", "Dear Friends,"
       and closings like "Sincerely,", "Best regards,", "Yours truly," or similar sign-offs.
     * Intent phrases: "I would like to ask/request...", "Please let me know...", 
       "I am writing to inquire...", "I would like to know...", "I want immediate action...",
       "I could not find any information...", "This is how you participate."
     * Use RC18 when the passage is a letter, email, or short notice with a single clear purpose
       (requesting a change, complaining, inviting, giving participation instructions, or asking
       for information).
   - RC19: Emotional change across narrative segments.
     * Strong signals: initial negative/positive emotion → opposite polarity later,
       explicit turning-point markers ("However", "But then", "Finally", "At last",
       "After ~"), and physical/emotional reactions shifting (e.g., shaking → steady,
       nervous → relieved).
     * Prefer RC19 over RC22–RC24 when the passage is a short narrative centered
       on a single character’s emotional journey.
   - RC20: Prescriptive/argumentative structure.
     * Strong signals: “should”, “must”, “ought to”, “have to/need to/has to”,
       “it is necessary/important/essential/critical to…”, 
       “it is desirable that we…”, explicit recommendations, proposals,
       or statements about what people ought to do.
   - RC21: Meaning of underlined figurative/idiomatic expression.
   - RC35: Irrelevant sentence among ①~⑤ (one sentence breaks cohesion).
   - RC36/RC37: Paragraph ordering; intro + (A)(B)(C) shuffling.
     * RC36: 단일 개념/설명을 (A)(B)(C)로 나눈 일반 설명문(정의·예시·보충 설명) 배열.
     * RC37: 연구/실험/데이터 보고나 단계적 논증(조건→결과, 균형, 모형 등)을
       (A)(B)(C)로 나눈 지문의 배열.
   - RC38: Sentence insertion in expository/analytical passages.
     * Strong pattern case: passages with explicit anchors like ( ① ) … ( ⑤ ).
     * Also consider RC38 even WITHOUT such anchors when:
       - the passage is a single-topic expository/analytical essay, and
       - there is a mid-passage pivot/transition sentence (e.g., "Yes, ...",
         "However, ...", "In fact, ...", "By way of example, ...",
         "Without ~, ...", "Once ~, ...") whose best location must be chosen
         among several plausible positions.
   - RC39: Higher-difficulty sentence insertion in argumentative / analogy-based passages.
     * The missing sentence usually comments on the ARGUMENT itself
       (e.g., "At the next step in the argument, however, the analogy breaks down.",
       "Still, it is arguable that ...", "Nevertheless, this line of reasoning fails when ...").
     * Prefer RC39 when:
       - the passage explicitly talks about an "argument", "analogy",
         "line of reasoning", or "logic", and
       - there is a sharp contrast or reversal (e.g., "by contrast", "in contrast",
         "nevertheless", "nonetheless", "still,", "on the other hand") between
         two parts of the passage.
   - RC29/RC30: Grammar/lexical appropriateness with underlined tokens and ①~⑤ options
                OR, in quote mode, structurally rich sentences where 5 short spans
                could be underlined without rewriting the passage.

3) RC29 vs RC30 (clarify):
   - RC29: 문법/구문/어법 오류(시제/수일치/대명사/전치사/형용사-부사 등) 중심.
     * Even without visible ①~⑤ or <u>…</u>, include RC29 when:
       - the passage is an expository/analytical text (≈80–230 words),
       - there are at least 4–5 complex sentences with relative clauses,
         subordinators, or participial phrases,
       - you could, in principle, select 5 short spans (1–3 tokens) so that
         exactly ONE can be made ungrammatical while the others stay correct.
   - RC30: 어휘/낱말의 쓰임 적절성 중심(어휘 의미/뉘앙스/콜로케이션/반의어-유의어 선택).
   - If underlined tokens + ①~⑤ exist but the error nature is unclear, include BOTH RC29 and RC30 with moderate scores (e.g., 0.45–0.65) and explain briefly.

4) Edge cases:
   - Even without explicit instruction sentences, if the PASSAGE itself contains ①~⑤ and <u>...</u>, consider RC29/RC30 as candidates.
   - Even if ①~⑤ and <u>...</u> have been stripped by preprocessing, still consider RC29/RC30 when
     the sentence structure or word choice strongly suggests grammar or lexical judgment.
   - If only (A)(B)(C) paragraph labels appear, prefer RC36/RC37.
   - If anchors ( ① ) … ( ⑤ ) appear within a paragraph for insertion, prefer RC38/RC39.
   - Even if such anchors have been stripped in preprocessing, still consider RC38
     when the passage has a clear mid-passage pivot sentence that could be moved.
   - When the passage centers on an analogy or explicit argument and there is a
     point where the analogy/argument "breaks down" or is contrasted, lean toward RC39.     
   - If the passage looks like a notice/form, prefer RC27/RC28 even without labels.

5) RC22 vs RC23 vs RC24 (disambiguation for explanatory essays):
   - For long expository/analytical passages that explain one central concept with reasons, examples,
     and implications (no story, no emotional journey, no clear sender/recipient):
     * Always include RC23 with a relatively high fit (e.g., ≥0.70) as the primary "topic/theme" type.
   - RC22 is for the main idea/gist (what the passage mainly says about its topic), often phrased
     as a concise statement that captures the author’s overall point.
   - RC24 is for the best title/heading; it focuses on a short phrase that would work well as the title.
   - The same passage can support RC22, RC23, and RC24 simultaneously, but for pure expository essays
     with a single core concept, RC23 should usually have the highest fit among these three.  
      
6) Length hints for blank types:
   - Prefer RC31–RC33 for short-to-medium passages (≈80–190 words).
   - Prefer RC34 only for longer expository passages (≈150–260 words) with clear logical pivots
     (e.g., however, therefore, in turn, it follows that, as a result).
   - Use RC40 when a medium-to-long expository passage (≈100–260 words) can be summed up as two
     short noun-phrase aspects (A) and (B) rather than a single sentence-length summary.

[SCORING GUIDANCE]
- 0.80–1.00: Strong direct match (multiple strong signals + discourse alignment).
- 0.60–0.79: Clear match with minor ambiguity.
- 0.40–0.59: Plausible but uncertain; competing types exist.
- 0.20–0.39: Weak; include only if nothing better.
- Reduce fit when cues conflict (e.g., chart-like data but narrative essay).
- Prefer fewer, higher-confidence candidates; cap at 12.

[REASONS & HINTS]
- "reason": reference concrete signals succinctly (e.g., "①~⑤ + <u>…</u> → lexical choice"
             or "multiple relative clauses allow RC29").
- "prep_hint": 1 actionable tip (e.g., "Check collocation/nuance for underlined word",
               "Check tense and subject–verb agreement near the underlined part"), or "-" if none.

[REMINDERS]
- Do not alter or rewrite the passage.
- Do not output markdown or explanations outside JSON.
- Be conservative; if uncertain between RC29 and RC30, include both with differentiated reasons.

- RC29/RC30 (Grammar/Lexis):
  * Underline/①~⑤ markers are OPTIONAL.
  * If the passage implies lexical appropriateness/nuance/collocation or contrasts that hinge on word choice,
    include RC30 as a candidate with moderate fit (0.40–0.65) even without markers.
  * If the passage has multiple complex clauses (relative/subordinate/participial) and would allow
    selecting 5 short spans (1–3 tokens) for a grammar judgment, include RC29 as a candidate even
    without markers.
  * Prefer RC30 when the issue is semantic/nuance/collocation; prefer RC29 for morpho-syntax/grammar.

[EXAMPLES_OF_SIGNALS]  // DO NOT echo in output; for your internal guidance
- Variants to treat as circled choices: "①", "②", "③", "④", "⑤", "(1)", "(2)", "(3)", "(4)", "(5)", "( ① )", "( ② )", etc.
- Underline markers may appear as "<u>word</u>", "<u> phrase </u>", or text explicitly saying "underlined".

[FINAL]
Return the JSON object now. No prose.
"""

ROUTER_PROMPTS: Dict[str, str] = {
    "SYSTEM": ROUTER_SYSTEM,
    "USER_TMPL": ROUTER_USER_TMPL,
}

def get_router_system() -> str:
    """라우터 시스템 프롬프트 반환 (외부에서 일관된 접근용)."""
    return ROUTER_PROMPTS["SYSTEM"]

def get_router_user(passage: str) -> str:
    """지문을 주입한 라우터 유저 프롬프트 생성."""
    return ROUTER_PROMPTS["USER_TMPL"].format(passage=passage)
