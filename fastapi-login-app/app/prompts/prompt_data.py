# app/prompts/prompt_data.py

ITEM_PROMPTS = {
"BASE_INSTRUCTION": """
You are an expert CSAT English item writer for Korea’s College Scholastic Ability Test.
Follow these permanent rules:

1) Item types: Listening / Reading only; adhere to official CSAT formats.
2) Language rule: Passages/transcripts in English; question and explanations in Korean.
3) Audience: Korean high-school CSAT takers; align with the national curriculum and achievement standards.
4) Output always includes:
   - [passage] (English)
   - [question] (Korean)
   - [options] (5 choices)
   - One correct answer (number 1–5) and four plausible distractors.
5) Use CSAT-appropriate vocabulary and structures.
6) Return well-formed JSON for downstream validation. No extra fields, no commentary.

If any later instructions conflict with these, the **later, item-specific instructions take priority** for that item.
""",
    "LC01": {
            "title": "듣기 1번 - 목적 파악",
            "content": """Create a CSAT Listening Item 1 (Purpose Identification) following these specifications:

    ## ITEM CHARACTERISTICS & METHODOLOGY

    ### Assessment Objective
    - **Core Skill**: Identifying the speaker's purpose in formal announcements
    - **Cognitive Process**: Listen → Identify speaker's intent → Match with purpose options
    - **Difficulty Level**: Basic comprehension with clear purpose indicators

    ### Discourse Type & Structure
    - **Format**: Formal monologue (announcement, notice, or public address)
    - **Structure Pattern**: Greeting → Identity/Role → Main announcement → Details → Closing
    - **Content Flexibility**: Any institutional context (school, office, public facility, organization)
    - **Speaker Role**: Official announcer, administrator, or authority figure

    ### Language Specifications
    - **Transcript Length**: 60-80 words (approximately 30-40 seconds)
    - **Sentence Complexity**: Simple to moderate (1-2 clauses per sentence)
    - **Vocabulary Level**: High-frequency, concrete vocabulary
    - **Speech Rate**: Standard conversational pace with clear articulation
    - **Vocabulary Profile**:
      "vocabulary_difficulty": "CSAT",
      "low_frequency_words": []

    ### Question Format Requirements
    - **Stem**: "다음을 듣고, [남자/여자]가 하는 말의 목적으로 가장 적절한 것을 고르시오."
    - **Options**: 5 Korean purpose statements ending with "~하려고"
    - **Correct Answer**: Must directly correspond to the speaker's main intent
    - **Distractors**: Related but secondary purposes, unmentioned purposes, opposite purposes

    ### Content Generation Guidelines
    - Create diverse announcement scenarios (schedule changes, policy updates, event notifications)
    - Ensure the purpose is clearly identifiable but requires active listening
    - Include realistic institutional contexts and appropriate formal language
    - Maintain consistency with Korean high school institutional environments

    **Required JSON Output Format:**
    {
    "question": "다음을 듣고, [남자/여자]가 하는 말의 목적으로 가장 적절한 것을 고르시오.",
    "transcript": "[60-80 word formal announcement in English]",
    "options": ["목적1하려고", "목적2하려고", "목적3하려고", "목적4하려고", "목적5하려고"],
    "correct_answer": [1-5],
    "explanation": "[Korean explanation of why the answer is correct]",
    "vocabulary_difficulty": "CSAT",
    "low_frequency_words": []    
    }""",
            "spec": {
                "type": "standard",
                "components": ["question", "transcript", "options"],
                "processing_hints": {}
            }
        },

    "LC02": {
            "title": "듣기 2번 - 의견 파악",
            "content": """Create a CSAT Listening Item 2 (Opinion Identification) following these specifications:

    ## ITEM CHARACTERISTICS & METHODOLOGY

    ### Assessment Objective
    - **Core Skill**: Identifying a speaker's opinion in conversational dialogue
    - **Cognitive Process**: Track dialogue → Identify target speaker → Extract consistent viewpoint
    - **Difficulty Level**: Basic comprehension with clear opinion markers

    ### Discourse Type & Structure
    - **Format**: Two-person dialogue with alternating speakers (M:/W:)
    - **Structure Pattern**: Topic introduction → Opinion expression → Supporting reasons → Conclusion
    - **Content Flexibility**: Any everyday topic requiring personal opinions or recommendations
    - **Interaction Type**: Advice-giving, preference sharing, or persuasion scenarios

    ### Language Specifications
    - **Transcript Length**: 80-100 words (approximately 40-50 seconds)
    - **Sentence Complexity**: Simple sentences with basic connectors
    - **Vocabulary Level**: Everyday conversational vocabulary
    - **Speech Rate**: Natural conversational pace with clear speaker distinction
        - **Vocabulary Profile**:
      "vocabulary_difficulty": "CSAT",
      "low_frequency_words": []

    ### Question Format Requirements
    - **Stem**: "대화를 듣고, [남자/여자]의 의견으로 가장 적절한 것을 고르시오."
    - **Options**: 5 Korean opinion statements (declarative or prescriptive)
    - **Correct Answer**: Must reflect the target speaker's consistent viewpoint throughout dialogue
    - **Distractors**: Other speaker's opinion, partial opinions, unmentioned views, opposite views

    ### Content Generation Guidelines
    - Create natural conversational scenarios about activities, choices, or recommendations
    - Ensure one speaker maintains a clear, consistent opinion with supporting reasons
    - Include realistic everyday contexts familiar to Korean high school students
    - Use clear opinion markers and supporting language patterns

    **Required JSON Output Format:**
    {
    "question": "대화를 듣고, [남자/여자]의 의견으로 가장 적절한 것을 고르시오.",
    "transcript": "[80-100 word dialogue with M:/W: speaker indicators]",
    "options": ["의견1이다", "의견2해야 한다", "의견3이다", "의견4해야 한다", "의견5이다"],
    "correct_answer": [1-5],
    "explanation": "[Korean explanation of the speaker's opinion]"
    }""",
            "spec": {
                "type": "standard",
                "components": ["question", "transcript", "options"],
                "processing_hints": {
                    "transcript": "speaker_separation"
                }
            }
        },

    "LC03": {
            "title": "듣기 3번 - 요지 파악",
            "content": """Create a CSAT Listening Item 3 (Main Point Identification) following these specifications:

    ## ITEM CHARACTERISTICS & METHODOLOGY

    ### Assessment Objective
    - **Core Skill**: Identifying the main point of an advice-giving monologue
    - **Cognitive Process**: Listen to advice → Extract central message → Identify key takeaway
    - **Difficulty Level**: Intermediate comprehension requiring synthesis of advice content

    ### Discourse Type & Structure
    - **Format**: Advice-giving monologue with instructional tone
    - **Structure Pattern**: Problem/situation → Advice/solution → Reasoning → Benefits/results
    - **Content Flexibility**: Any topic suitable for giving practical advice or tips
    - **Speaker Role**: Advisor, expert, or experienced person sharing guidance

    ### Language Specifications
    - **Transcript Length**: 100-120 words (approximately 50-60 seconds)
    - **Sentence Complexity**: Moderate complexity with some subordination
    - **Vocabulary Level**: Mix of concrete and moderately abstract terms
    - **Speech Rate**: Measured pace appropriate for advice delivery
    - **Vocabulary Profile**:
      "vocabulary_difficulty": "CSAT",
      "low_frequency_words": []    

    ### Question Format Requirements
    - **Stem**: "다음을 듣고, [남자/여자]가 하는 말의 요지로 가장 적절한 것을 고르시오."
    - **Options**: 5 Korean statements expressing main points or central messages
    - **Correct Answer**: Must capture the essential advice or main message
    - **Distractors**: Supporting details, partial points, related but not central ideas, opposite advice

    ### Content Generation Guidelines
    - Create advice scenarios on topics like study methods, life skills, or personal development
    - Ensure the main point is clearly supported by reasoning and examples
    - Include practical, actionable advice relevant to Korean high school students
    - Maintain a helpful, instructional tone throughout

    **Required JSON Output Format:**
    {
    "question": "다음을 듣고, [남자/여자]가 하는 말의 요지로 가장 적절한 것을 고르시오.",
    "transcript": "[100-120 word advice-giving monologue in English]",
    "options": ["요지1이다", "요지2이다", "요지3이다", "요지4이다", "요지5이다"],
    "correct_answer": [1-5],
    "explanation": "[Korean explanation of the main point]"
    }""",
            "spec": {
                "type": "standard",
                "components": ["question", "transcript", "options"],
                "processing_hints": {}
            }
        },
"LC04": {
  "title": "듣기 4번 - 그림 내용 불일치",
  "content": """Create a CSAT Listening Item 4 (Picture Content Mismatch) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Identifying mismatches between visual and auditory information
- **Cognitive Process**: Process visual elements → Listen to descriptions → Compare and identify discrepancies
- **Difficulty Level**: Basic visual-auditory integration with concrete elements

### Discourse Type & Structure
- **Format**: Two-person dialogue describing visual elements
- **Structure Pattern**: Scene setting → Systematic description of visual elements → Detailed observations
- **Content Flexibility**: Any observable scene with multiple identifiable objects, people, or activities
- **Interaction Type**: Collaborative observation and description

### Language Specifications
- **Transcript Length**: 70-90 words (approximately 35-45 seconds)
- **Sentence Complexity**: Simple descriptive sentences
- **Vocabulary Level**: Concrete, observable vocabulary (colors, shapes, positions, actions)
- **Speech Rate**: Clear, descriptive pace with emphasis on visual details
- **Vocabulary Profile**:
  "vocabulary_difficulty": "CSAT",
  "low_frequency_words": []

### Question Format Requirements
- **Stem**: "대화를 듣고, 그림에서 대화의 내용과 일치하지 <u>않는</u> 것을 고르시오."
- **Options**: 5 Korean descriptions of visual elements that appear in the picture
- **Correct Answer**: Must be the one element that contradicts the dialogue description
- **Distractors**: Elements that match the dialogue description exactly

### Content Generation Guidelines
- Create scenes with 5-7 clearly identifiable visual elements
- Ensure 4 elements are accurately described and 1 is contradicted in the dialogue
- Include realistic settings like parks, markets, classrooms, or public spaces
- Use precise descriptive language for colors, positions, quantities, and states

### Required JSON Output Format
{
  "question": "대화를 듣고, 그림에서 대화의 내용과 일치하지 <u>않는</u> 것을 고르시오.",
  "transcript": "[70-90 word descriptive dialogue with M:/W: indicators]",
  "options": ["시각요소1", "시각요소2", "시각요소3", "시각요소4", "시각요소5"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of the mismatch]",
  "image_prompt": "Cartoon-style black-and-white exam illustration of a flea market. Include a tree with a sign reading 'FLEA MARKET' pointing right, a tent canopy decorated with small flower patterns, a chair with a speaker under the tent, a table with three white vases, and a girl holding a balloon. IMPORTANT: In the transcript the balloon is described as a star shape, but in the illustration draw the balloon as a crown shape to create the mismatch. Exam-style line drawing, minimal shading, simple and clear composition."
}""",
  "spec": {
    "type": "standard",
    "components": ["question", "transcript", "options", "image_prompt"],
    "processing_hints": {
      "transcript": "speaker_separation"
    },
    "special_features": ["picture_description", "image_generation"]
  }
},
"LC05": {
    "title": "듣기 5번 - 할 일 파악",
    "content": """Create a CSAT Listening Item 5 (Task Identification) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Identifying specific tasks assigned to a particular speaker
- **Cognitive Process**: Track task distribution → Identify speaker roles → Extract specific assignments
- **Difficulty Level**: Basic task tracking with clear assignment indicators

### Discourse Type & Structure
- **Format**: Two-person dialogue about task distribution or preparation
- **Structure Pattern**: Situation setup → Task review → Role assignment → Confirmation of responsibilities
- **Content Flexibility**: Any collaborative activity requiring task distribution (events, projects, preparations)
- **Interaction Type**: Planning, organizing, or preparation conversations

### Language Specifications
- **Transcript Length**: 80-100 words (approximately 40-50 seconds)
- **Sentence Complexity**: Simple to moderate with clear task indicators
- **Vocabulary Level**: Action-oriented vocabulary related to tasks and responsibilities
- **Speech Rate**: Natural conversational pace with clear task assignments
- **Vocabulary Profile**:
  "vocabulary_difficulty": "CSAT",
  "low_frequency_words": []

### Question Format Requirements
- **Stem**: "대화를 듣고, [남자/여자]가 할 일로 가장 적절한 것을 고르시오."
- **Options**: 5 Korean task descriptions using action verbs
- **Correct Answer**: Must be the specific task clearly assigned to the target speaker
- **Distractors**: Tasks assigned to the other speaker, completed tasks, mentioned but unassigned tasks

### Content Generation Guidelines
- Create realistic preparation scenarios for events, projects, or activities
- Ensure clear task assignments with explicit responsibility indicators
- Include contexts familiar to Korean students (school events, group projects, family activities)
- Use clear assignment language and confirmation patterns

**Required JSON Output Format:**
{
  "question": "대화를 듣고, [남자/여자]가 할 일로 가장 적절한 것을 고르시오.",
  "transcript": "[80-100 word task distribution dialogue with M:/W: indicators]",
  "options": ["할일1", "할일2", "할일3", "할일4", "할일5"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of the assigned task]"
}""",
    "spec": {
        "type": "standard",
        "components": ["question", "transcript", "options"],
        "processing_hints": {
            "transcript": "speaker_separation"
        }
    }
},
"LC06": {
  "title": "듣기 6번 - 지불 금액(암산 정수 계산형, 최종 금액 미제시·누수 차단)",
  "content": """Create a CSAT Listening Item 6 (Payment Amount) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Calculating payment amounts through mental arithmetic
- **Cognitive Process**: Extract clear numerical info → Apply one simple discount or condition → Multiply quantities → Compute final total
- **Difficulty Level**: Intermediate, designed for quick mental calculation (2 steps, maximum 3)

### Discourse Type & Structure
- **Format**: Transactional dialogue (e.g., ticket booking, ordering food, buying items)
- **Structure Pattern** (5 turns min, 10 turns max):
  1) Inquiry / need
  2) Unit price(s) stated (integers only)
  3) Discount/condition stated (integer-result only)
  4) Quantity confirmation (may repeat numbers once)
  5) **Payment action phrase** (no numbers) → END

### CRITICAL ANTI-LEAK GUARDRAILS
- **HARD BAN**: The **consumer’s final payment amount** must **never** appear in the transcript.
- The transcript **must not** contain any utterance that computes/sums/quotes the total (e.g., “That’ll be…”, “It comes to…”, “The total is…”, “Altogether…”).
- The **last TWO turns must contain ZERO digits, currency symbols, or number words** (e.g., $, dollar(s), won, 백/천/만, 숫자 0–9).
- The customer **must not ask** “How much will it be?” / “총 얼마인가요?”류 질문. Instead, they only express intent to pay.
- The clerk **must not** perform or verbalize any calculation (e.g., “Let me calculate…”, “계산해 드릴게요”). The ending must be an **action phrase only** (e.g., “I’ll ring it up.”, “결제 도와드리겠습니다.”).
- If any leak-like phrase or pattern appears, **regenerate the transcript** and enforce the guardrails.

### Cognitive Load Reduction Principles
- **All numbers must be integers** (prices/quantities/discounts → integer results).
- Use easy integers (10, 15, 20, multiples of 5); one simple condition only.
- Repeat key numbers once; add a micro-pause cue after numbers (“… okay.”) to aid mental processing.
- Any discount or condition applied must result in an **integer final total** (no decimals allowed).

### Language Specifications
- Transcript Length: 100–120 words (50–60 seconds)
- Sentence Complexity: Moderate (no long embeddings)
- Vocabulary: Everyday commercial
- Speech Rate: Clear; slightly slower on numbers
- **Vocabulary Profile**:
  "vocabulary_difficulty": "CSAT",
  "low_frequency_words": []

### Question Format Requirements
- **Stem**: "대화를 듣고, [남자/여자]가 지불할 금액을 고르시오."
- **Options**: 5 integer amounts, close in value
- **Correct Answer**: Not in transcript; must be computed by the test-taker
- **Distractors**: Common mental-math mistakes (no-discount, miscount quantity, misapplied condition)
- **Option Spacing Rule**: All five options must differ from each other by at least 2.

### Content Generation Guidelines
- Realistic scenario (tickets/café/theme park/transport).
- Mental calculation time ≤ 15s; no layered rules.
- **Final payment amount must not appear** in the dialogue.
- **Dialogue must end with an action phrase** (no numerals in the last two turns).

### NEGATIVE LIST (Forbidden Phrases)
- EN: "That’ll be", "It comes to", "The total is", "Altogether", "Let me calculate", "That is $", "You’ll pay", "How much will it be?"
- KO: "총액/합계/금액은", "합쳐서/모두 합하면", "계산해 드리면", "…원입니다/입니다", "얼마예요?/얼마인가요?"

### FORBIDDEN PATTERNS (Regex cues for validation)
- `(?i)\\b(that('|’)ll be|it comes to|total is|altogether|let me calculate)\\b`
- `[$€£₩]\\s*\\d`
- `\\b(총액|합계|금액|모두 합하면|합치면)\\b.*\\d`
- `\\b(얼마(예요|인가요))\\b`
- **Last two turns**: disallow digits/currency/number words.

**Required JSON Output Format:**
{
  "question": "대화를 듣고, [남자/여자]가 지불할 금액을 고르시오.",
  "transcript": "[100–120 word transactional dialogue with M:/W: indicators; unit prices, quantities, condition only; NO final total; last two turns contain no numerals or currency.]",
  "options": ["$정수금액1", "$정수금액2", "$정수금액3", "$정수금액4", "$정수금액5"],
  "correct_answer": [1-5],
  "explanation": "[계산 과정을 단계별로 서술하되 최종 금액 숫자는 쓰지 말고, 마지막에 '따라서 정답은 ○번이다'로만 표기]"
}""",
  "spec": {
    "type": "standard",
    "components": ["question", "transcript", "options"],
    "processing_hints": { "transcript": "speaker_separation" },
    "special_features": [
      "multi-step integer calculation",
      "no explicit total in transcript",
      "last-two-turns digit-free",
      "no numeric answer leakage",
      "test-taker must compute"
    ]
  }
},
"LC07": {
    "title": "듣기 7번 - 이유 파악",
    "content": """Create a CSAT Listening Item 7 (Reason Identification) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Identifying specific reasons for inability to participate in events
- **Cognitive Process**: Track invitation → Identify refusal → Extract actual reason from multiple possibilities
- **Difficulty Level**: Intermediate comprehension requiring reason discrimination

### Discourse Type & Structure
- **Format**: Two-person dialogue about event participation
- **Structure Pattern**: Invitation/suggestion → Interest but inability → Reason exploration → Actual reason revelation
- **Content Flexibility**: Any social event or activity invitation scenario
- **Interaction Type**: Social invitation and polite refusal with explanation

### Language Specifications
- **Transcript Length**: 90-110 words (approximately 45-55 seconds)
- **Sentence Complexity**: Moderate with causal expressions and explanations
- **Vocabulary Level**: Social and explanatory vocabulary
- **Speech Rate**: Natural conversational pace with clear reason indicators
- **Vocabulary Profile**:
  "vocabulary_difficulty": "CSAT",
  "low_frequency_words": []

### Question Format Requirements
- **Stem**: "대화를 듣고, [남자/여자]가 [이벤트]에 갈 수 <u>없는</u> 이유를 고르시오."
- **Options**: 5 Korean reason statements using causal expressions
- **Correct Answer**: Must be the actual reason explicitly stated by the speaker
- **Distractors**: Suggested but rejected reasons, related but incorrect reasons, opposite situations

### Content Generation Guidelines
- Create realistic social invitation scenarios
- Include multiple potential reasons but make one clearly correct
- Ensure the actual reason is explicitly stated, not just implied
- Use contexts relevant to Korean student social life

**Required JSON Output Format:**
{
  "question": "대화를 듣고, [남자/여자]가 [이벤트]에 갈 수 <u>없는</u> 이유를 고르시오.",
  "transcript": "[90-110 word invitation dialogue with M:/W: indicators]",
  "options": ["이유1때문에", "이유2해야 해서", "이유3때문에", "이유4해야 해서", "이유5때문에"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of the reason]"
}""",
    "spec": {
        "type": "standard",
        "components": ["question", "transcript", "options"],
        "processing_hints": {
            "transcript": "speaker_separation"
        }
    }
},
"LC08": {
    "title": "듣기 8번 - 언급되지 <u>않은</u> 것",
    "content": """Create a CSAT Listening Item 8 (Not Mentioned) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Identifying information not mentioned in event-related dialogue
- **Cognitive Process**: Track mentioned information → Compare with options → Identify omissions
- **Difficulty Level**: Intermediate information tracking with systematic checking

### Discourse Type & Structure
- **Format**: Two-person dialogue about event information
- **Structure Pattern**: Event discovery → Information gathering → Detail confirmation → Additional inquiries
- **Content Flexibility**: Any event, program, or activity with multiple informational aspects
- **Interaction Type**: Information exchange and inquiry

### Language Specifications
- **Transcript Length**: 90-110 words (approximately 45-55 seconds)
- **Sentence Complexity**: Moderate with information-dense content
- **Vocabulary Level**: Informational and descriptive vocabulary
- **Speech Rate**: Natural pace with clear information delivery
- **Vocabulary Profile**:
  "vocabulary_difficulty": "CSAT",
  "low_frequency_words": []

### Question Format Requirements
- **Stem**: "대화를 듣고, [Event/Program/Activity in English]에 관해 언급되지 <u>않은</u> 것을 고르시오."
- **Options**: 5 Korean information categories related to the topic
- **Correct Answer**: Must be the information category not mentioned in the dialogue
- **Distractors**: Information categories explicitly mentioned in the dialogue

### Content Generation Guidelines
- Create information-rich dialogues about events or programs
- Ensure 4 information categories are clearly mentioned and 1 is omitted
- Include realistic event contexts with typical information needs
- Use systematic information patterns familiar to Korean students

**Required JSON Output Format:**
{
  "question": "대화를 듣고, [Event/Program/Activity in English]에 관해 언급되지 <u>않은</u> 것을 고르시오.",
  "transcript": "[90-110 word information dialogue with M:/W: indicators]",
  "options": ["정보항목1", "정보항목2", "정보항목3", "정보항목4", "정보항목5"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of what was not mentioned]"
}""",
    "spec": {
        "type": "standard",
        "components": ["question", "transcript", "options"],
        "processing_hints": {
            "transcript": "speaker_separation"
        }
    }
},
"LC09": {
    "title": "듣기 9번 - 내용 불일치",
    "content": """Create a CSAT Listening Item 9 (Content Mismatch) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Identifying factual inconsistencies between monologue content and options
- **Cognitive Process**: Process announcement information → Compare with factual statements → Identify contradictions
- **Difficulty Level**: Intermediate factual verification with detailed information

### Discourse Type & Structure
- **Format**: Formal announcement monologue
- **Structure Pattern**: Introduction → Event details → Schedule information → Procedures → Additional information
- **Content Flexibility**: Any formal event or program announcement
- **Speaker Role**: Official announcer or event organizer

### Language Specifications
- **Transcript Length**: 110-130 words (approximately 55-65 seconds)
- **Sentence Complexity**: Moderate with detailed factual information
- **Vocabulary Level**: Formal and informational vocabulary
- **Speech Rate**: Clear, measured pace appropriate for announcements
- **Vocabulary Profile**:
  "vocabulary_difficulty": "CSAT",
  "low_frequency_words": []

### Event Name Extraction Rules (CRITICAL)
- **From the transcript, extract the official event/program name (e.g., "Ecosystem Exploration Day").
- **Preserve the exact English name and capitalization as spoken; do not translate it.
- **If multiple names appear, choose the main event being announced (first full proper name in the introduction).
- **If no explicit event name is given, construct a concise, specific proper name from context (e.g., "School Wetlands Field Trip").

### Question Format Requirements
- **Stem**: "[이벤트]에 관한 다음 내용을 듣고, 일치하지 <u>않는</u> 것을 고르시오."
- **Format**: "「{event_name}」에 관한 다음 내용을 듣고, 일치하지 <u>않는</u> 것을 고르시오."
- **Do NOT output placeholders like "[이벤트]". If the event name cannot be extracted, synthesize a plausible proper name from the transcript and use it instead.
- **Options**: 5 Korean factual statements about the announced content
- **Correct Answer**: Must be the statement that contradicts the announcement
- **Distractors**: Statements that accurately reflect the announcement content

### Content Generation Guidelines
- Create detailed event announcements with specific factual information
- Ensure 4 statements match the content exactly and 1 contradicts it
- Include realistic institutional or public event contexts
- Use precise factual language and clear information structure

### Self-Check Before Output (MANDATORY)
- The question must contain 「 and 」 with the actual event name, not any placeholders.
- correct_answer must be a number 1–5.
- The transcript must be English only; the question/explanation must be Korean.
- If the question contains [ or ], regenerate the question to use the required format.

**Required JSON Output Format:**
{
  "question": "「{event_name}」에 관한 다음 내용을 듣고, 일치하지 <u>않는</u> 것을 고르시오.",
  "transcript": "[110-130 word formal announcement in English]",
  "options": ["사실1", "사실2", "사실3", "사실4", "사실5"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of the contradiction]"
}""",
    "spec": {
        "type": "standard",
        "components": ["question", "transcript", "options"],
        "processing_hints": {}
    }
},
"LC10": {
  "title": "듣기 10번 - 표 정보 확인",
  "content": """Create a CSAT Listening Item 10 (Chart Information) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- Core Skill: Integrating auditory criteria with visual chart information for elimination and final selection
- Cognitive Process: Sequential elimination → Apply each criterion in order → Narrow down to final choice
- Difficulty Level: Intermediate multi-modal information integration

### Discourse Type & Structure
- Format: Two-person dialogue about selection from chart options
- Structure Pattern: Need identification → Chart consultation → Criteria specification → Step-by-step elimination → Final decision
- Content Flexibility: Any selection scenario with multiple criteria (products, services, options)
- Interaction Type: Collaborative decision-making with criteria application

### Language Specifications
- Transcript Length: 90-110 words (approximately 45-55 seconds)
- Sentence Complexity: Moderate with comparative and conditional expressions
- Vocabulary Level: Comparative and criteria-based vocabulary
- Speech Rate: Natural pace with clear criteria articulation
- **Vocabulary Profile**:
  "vocabulary_difficulty": "CSAT",
  "low_frequency_words": []

### Question Format Requirements
- Stem: "다음 표를 보면서 대화를 듣고, [화자]가 구입할 [상품]을 고르시오."
- Options: 5 chart entries representing different combinations of attributes
- Correct Answer: Must be the option that satisfies all stated criteria
- Distractors: Options that satisfy some but not all criteria

---

## ADDITIONAL STRUCTURAL CONSTRAINTS

### Listening Item Structure (LC10 Chart)
1. Chart: 5 items × 4 attributes.
2. Transcript: Criteria must be presented strictly in the same order as chart columns (Attribute 1 → 2 → 3 → 4).
3. Sequential Elimination:
   - At each stage, exactly **one option** must be eliminated.
   - Process: 5 → 4 → 3 → 2 → 1 remaining.

### Elimination Rules by Attribute
- **Attribute 1 (Price/Fee)**: Must use either an upper limit (≤ B) or a unique extreme (lowest/highest) so that exactly one option is eliminated.
- **Attribute 2 (Length/Weight/People/Time)**: Must use either a lower bound (≥ N) or a time condition (e.g., after T) to eliminate exactly one option.
- **Attribute 3 (Category like Color/Material)**: Must use a restriction such as “no X,” with the distribution designed so that among the remaining 3, only one has X → leaving 2 candidates.
- **Attribute 4 (Binary Feature such as Yes/No, A/B)**: The final 2 candidates must be identical in Attributes 1–3 but opposite in Attribute 4. The speaker preference at the end decides the unique correct answer.

### Final Selection Rule
- After applying Attribute 1–3, exactly two options remain.
- These two options must have identical values in Attributes 1–3 but opposite values in Attribute 4.
- The final dialogue statement must explicitly state a preference for Attribute 4, ensuring a unique answer.

---

## STRICT OUTPUT CONTRACT (DO NOT VIOLATE)
- Output JSON only. No extra text.
- Must include: item_type, question, transcript, chart_data, options, correct_answer, explanation.
- item_type must be "LC_CHART".
- transcript: English dialogue (90-110 words) with speaker markers M:/W:.
- chart_data must be exactly this shape (no markdown, no object-array, no datasets):
  {
    "headers": ["Item", "Attribute 1", "Attribute 2", "Attribute 3", "Attribute 4"],
    "rows": [
              ["1", "...", "...", "...", "..."],
              ["2", "...", "...", "...", "..."],
              ["3", "...", "...", "...", "..."],
              ["4", "...", "...", "...", "..."],
              ["5", "...", "...", "...", "..."]
            ]
  }
- The first header (identifier) is fixed to "Item" and the values must be "1"~"5".
- All headers and rows must be in English only (ASCII).
- All cells must be strings (or numbers) only; HTML/markdown prohibited.
- options must be exactly ["1","2","3","4","5"] (same identifiers).
- correct_answer must be an integer 1–5 (number).
- explanation must be in Korean and must justify why the chosen row satisfies all stated criteria from the dialogue.
""",
  "spec": {
    "type": "standard",
    "components": ["question", "transcript", "chart_data", "options"],
    "processing_hints": {
      "transcript": "speaker_separation"
    },
    "special_features": ["chart_integration", "sequential_elimination"]
  }
},
"LC11": {
    "title": "듣기 11번 - 짧은 대화 응답",
    "content": """Create a CSAT Listening Item 11 (Short Response Inference) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Inferring appropriate responses to final statements in short dialogues
- **Cognitive Process**: Follow dialogue context → Analyze final statement → Select logical response
- **Difficulty Level**: Advanced contextual inference requiring pragmatic understanding

### Discourse Type & Structure
- **Format**: Brief two-person dialogue (2-3 exchanges)
- **Structure Pattern**: Situation setup → Problem/request → Final statement requiring response
- **Content Flexibility**: Any everyday situation requiring immediate, contextually appropriate responses
- **Interaction Type**: Problem-solving, request-response, or social interaction

### Language Specifications
- **Transcript Length**: 60-80 words (approximately 30-40 seconds)
- **Sentence Complexity**: Simple to moderate with clear contextual cues
- **Vocabulary Level**: Everyday conversational vocabulary
- **Speech Rate**: Natural conversational pace
- **Vocabulary Profile**:
  "vocabulary_difficulty": "CSAT+O3000",
  "low_frequency_words": ["예: permit", "예: schedule"]

### Formatting Instructions for Transcript
- 대화문은 M: (남자 화자), W: (여자 화자) 표기를 사용한다.
- 남자가 먼저 말하고, 여자가 마지막에 말하며, 그 마지막 발화가 문제에서 응답해야 하는 대상이 된다.
- 대화는 2~3턴으로 구성하되, 마지막 발화는 반드시 여자의 대사로 끝난다.

### Question Format Requirements
- **Stem**: "대화를 듣고, 남자의 마지막 말에 대한 여자의 응답으로 가장 적절한 것을 고르시오. [3점]"
- **Options**: 5 English response options
- **Correct Answer**: Must be the most contextually appropriate and natural response
- **Distractors**: Contextually inappropriate, logically inconsistent, or socially awkward responses

### Content Generation Guidelines
- Create realistic everyday scenarios requiring immediate responses
- Ensure the final statement clearly sets up the need for a specific type of response
- Include contexts familiar to Korean students (daily life, services, social situations)
- Use natural conversational patterns and appropriate social registers

**Required JSON Output Format:**
{
  "question": "대화를 듣고, [화자]의 마지막 말에 대한 [상대방]의 응답으로 가장 적절한 것을 고르시오. [3점]",
  "transcript": "[60-80 word short dialogue with M:/W: indicators]",
  "options": ["Response 1", "Response 2", "Response 3", "Response 4", "Response 5"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of why the response is appropriate]"
}""",
    "spec": {
        "type": "standard",
        "components": ["question", "transcript", "options"],
        "processing_hints": {
            "transcript": "speaker_separation"
        },
        "special_features": ["response_inference"]
    }
},
"LC12": {
    "title": "듣기 12번 - 짧은 대화 응답",
    "content": """Create a CSAT Listening Item 12 (Short Response Inference) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Inferring appropriate responses to final statements in short dialogues
- **Cognitive Process**: Follow dialogue context → Analyze final statement → Select logical response
- **Difficulty Level**: Intermediate contextual inference with clear response patterns

### Discourse Type & Structure
- **Format**: Brief two-person dialogue (2-3 exchanges)
- **Structure Pattern**: Proposal → Concern expression → Reassurance → Response needed
- **Content Flexibility**: Any situation involving initial hesitation followed by reassurance
- **Interaction Type**: Invitation acceptance after concern resolution

### Language Specifications
- **Transcript Length**: 50-70 words (approximately 25-35 seconds)
- **Sentence Complexity**: Simple with clear reassurance patterns
- **Vocabulary Level**: Basic conversational vocabulary
- **Speech Rate**: Natural conversational pace
- **Vocabulary Profile**:
  "vocabulary_difficulty": "CSAT+O3000",
  "low_frequency_words": ["예: permit", "예: schedule"]

### Question Format Requirements
- **Stem**: "대화를 듣고, 여자의 마지막 말에 대한 남자의 응답으로 가장 적절한 것을 고르시오."
- **Options**: 5 English response options
- **Correct Answer**: Must show acceptance after reassurance, as the man's response to the final W: line
- **Distractors**: Continued hesitation, irrelevant responses, inappropriate reactions

 ### Transcript Formatting Instructions
- 대화문은 W: (여자 화자), M: (남자 화자) 표기를 사용한다.
- 여자가 먼저 말하고, 남자가 마지막에 말하며, 그 마지막 발화가 문제에서 응답해야 하는 대상이 된다.
- 대화는 2~3턴으로 구성하되, 마지막 발화는 반드시 남자의 대사로 끝난다.
- 대화문 표기는 W: (여자), M: (남자)를 사용한다.
- 여자가 먼저 말하고, 마지막 발화도 반드시 여자의 대사(W:)로 끝난다.
- 남자의 응답은 transcript에 포함하지 않으며, 보기가 남자의 응답 후보가 된다.
- (검증) transcript의 마지막 줄은 반드시 `W:`로 시작해야 한다.

### Content Generation Guidelines
- Create scenarios where initial concerns are addressed and resolved
- Ensure the final statement provides clear reassurance
- Include contexts involving activities, programs, or invitations
- Use clear concern-resolution patterns

**Required JSON Output Format:**
{
  "question": "대화를 듣고, [화자]의 마지막 말에 대한 [상대방]의 응답으로 가장 적절한 것을 고르시오.",
  "transcript": "[50-70 word dialogue with W:/M: indicators; ends with a W: line; the man's response is NOT included]",
  "options": ["Response 1", "Response 2", "Response 3", "Response 4", "Response 5"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of the response logic]"
}""",
    "spec": {
        "type": "standard",
        "components": ["question", "transcript", "options"],
        "processing_hints": {
            "transcript": "speaker_separation"
        },
        "special_features": ["response_inference"]
    }
},
"LC13": {
    "title": "듣기 13번 - 긴 대화 응답",
    "content": """Create a CSAT Listening Item 13 (Long Response Inference) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Inferring appropriate responses in extended dialogue contexts
- **Cognitive Process**: Track extended conversation → Understand contribution context → Select appreciative response
- **Difficulty Level**: Intermediate contextual inference with extended dialogue tracking

### Discourse Type & Structure
- **Format**: Extended two-person dialogue
- **Turn Pattern**: Exactly **9 turns total** → M: 5 times, W: 4 times
- **Structure Pattern**: Contact → Proposal → Interest → Contribution offer → Acceptance → Response needed
- **Content Flexibility**: Any collaborative or charitable activity scenario
- **Interaction Type**: Voluntary contribution and appreciation

### Language Specifications
- **Transcript Length**: 100-120 words (approximately 50-60 seconds)
- **Sentence Complexity**: Simple with clear contribution patterns
- **Vocabulary Level**: Basic conversational and activity-related vocabulary
- **Speech Rate**: Natural conversational pace
- **Vocabulary Profile**:
  "vocabulary_difficulty": "CSAT+O3000",
  "low_frequency_words": ["예: permit", "예: schedule"]

### Question Format Requirements
- **Stem**: "대화를 듣고, 남자의 마지막 말에 대한 여자의 응답으로 가장 적절한 것을 고르시오."
- **Options**: 5 English response options
- **Correct Answer**: Must express appreciation and encouragement for the contribution, as the woman's response to the final M: line
- **Distractors**: Inappropriate reactions, misunderstanding responses, irrelevant comments

### Transcript Formatting Instructions
- 대화문은 반드시 **M과 W의 발화가 교대로 교환**되어야 한다.
- 총 **9턴**: 남자(M) 5회, 여자(W) 4회.
- 마지막 발화는 반드시 **M:으로 끝나야** 하며, 여자의 최종 응답은 transcript에 포함하지 않는다.
- 전체 길이는 100~120 단어(약 50~60초)로 유지한다.

### Content Generation Guidelines
- Create scenarios involving voluntary contributions or collaborative efforts
- Ensure the final statement confirms positive contribution
- Include contexts involving community activities, charitable work, or group projects
- Use clear appreciation and encouragement patterns

**Required JSON Output Format:**
{
  "question": "대화를 듣고, 남자의 마지막 말에 대한 여자의 응답으로 가장 적절한 것을 고르시오.",
  "transcript": "[100-120 word extended dialogue with exactly 9 turns (M:5, W:4), ending with M:]",
  "options": ["(Woman's response) 1", "(Woman's response) 2", "(Woman's response) 3", "(Woman's response) 4", "(Woman's response) 5"],
  "correct_answer": [1-5],
  "explanation": "[남자의 마지막 발화에 대해 여자가 감사와 격려를 표현하는 응답이 왜 적절한지 한국어로 설명]"
}""",
    "spec": {
        "type": "standard",
        "components": ["question", "transcript", "options"],
        "processing_hints": {
            "transcript": "speaker_separation"
        },
        "special_features": ["response_inference"]
    }
},
"LC14": {
    "title": "듣기 14번 - 긴 대화 응답",
    "content": """Create a CSAT Listening Item 14 (Long Response Inference) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Inferring appropriate responses in complex extended dialogues
- **Cognitive Process**: Track complex conversation → Understand scheduling context → Select appropriate response
- **Difficulty Level**: Advanced contextual inference with complex dialogue tracking

### Discourse Type & Structure
- **Format**: Extended two-person dialogue
- **Scenario Type**: Professional **telephone conversation**
- **Turn Pattern**: Exactly **9 turns total** → W: 5 times, M: 4 times
- **Structure Pattern**: Request → Acceptance → Scheduling conflict → Coordination → Promise → Response needed
- **Interaction Type**: Professional scheduling and commitment

### Language Specifications
- **Transcript Length**: 120-140 words (approximately 60-70 seconds)
- **Sentence Complexity**: Moderate with professional language patterns
- **Vocabulary Level**: Professional and scheduling vocabulary
- **Speech Rate**: Natural professional conversation pace
- **Vocabulary Profile**:
  "vocabulary_difficulty": "CSAT+O3000",
  "low_frequency_words": ["예: permit", "예: schedule"]

### Question Format Requirements
- **Stem**: "대화를 듣고, 여자의 마지막 말에 대한 남자의 응답으로 가장 적절한 것을 고르시오. [3점]"
- **Options**: 5 English response options
- **Correct Answer**: Must express hope and positive expectation for the promised response, as the man's response to the final W: line
- **Distractors**: Impatient responses, misunderstanding, inappropriate timing, irrelevant comments

### Transcript Formatting Instructions
- 대화문은 반드시 **M과 W의 발화가 교대로 교환**되어야 한다.
- 총 **9턴**: 여자(W) 5회, 남자(M) 4회.
- 마지막 발화는 반드시 **W:**로 끝나야 하며, 그 발화는 후속 응답(콜백/이메일 약속 등)을 명확히 약속한다.
- 남자의 최종 응답은 transcript에 포함하지 않고, 선택지에 제시한다.
- 전체 길이는 120~140 단어(약 60~70초)로 유지한다.
- 상황은 반드시 **전화 통화**여야 하며, 첫 발화는 전화 인사 또는 자기소개로 시작한다.

### Content Generation Guidelines
- Create professional consultation or expert invitation scenarios
- Ensure the final statement makes a clear promise for future response
- Include contexts involving professional services, expert advice, or formal requests
- Use appropriate professional language and scheduling patterns

**Required JSON Output Format:**
{
  "question": "대화를 듣고, 여자의 마지막 말에 대한 남자의 응답으로 가장 적절한 것을 고르시오. [3점]",
  "transcript": "[120-140 word professional telephone dialogue with exactly 9 turns (W:5, M:4), ending with a W: line that promises a follow-up; the man's response is NOT included]",
  "options": ["(Man's response) 1", "(Man's response) 2", "(Man's response) 3", "(Man's response) 4", "(Man's response) 5"],
  "correct_answer": [1-5],
  "explanation": "[여자의 마지막 약속 발화에 대해 남자가 희망/긍정적 기대를 공손하게 표현하는 응답이 왜 적절한지 한국어로 설명]"
}""",
    "spec": {
        "type": "standard",
        "components": ["question", "transcript", "options"],
        "processing_hints": {
            "transcript": "speaker_separation"
        },
        "special_features": ["response_inference"]
    }
},
"LC15": {
    "title": "듣기 15번 - 상황에 맞는 말",
    "content": """Create a CSAT Listening Item 15 (Situational Response) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Selecting appropriate utterances for complex situational contexts
- **Cognitive Process**: Analyze complex situation → Understand speaker motivation → Select optimal expression
- **Difficulty Level**: Advanced situational inference requiring deep contextual understanding

### Discourse Type & Structure
- **Format**: Situational description monologue
- **Structure Pattern**: Background → Initial plan → Complication → Experience factor → Advice motivation → Utterance selection
- **Content Flexibility**: Any advice-giving situation based on experience and expertise
- **Speaker Role**: Experienced advisor offering guidance based on personal knowledge

### Language Specifications
- **Transcript Length**: 140-160 words (approximately 70-80 seconds)
- **Sentence Complexity**: Complex with sophisticated situational development
- **Vocabulary Level**: Sophisticated situational and advisory vocabulary
- **Speech Rate**: Measured pace appropriate for complex situation description
- **Vocabulary Profile**:
  "vocabulary_difficulty": "CSAT+O3000",
  "low_frequency_words": ["예: permit", "예: schedule"]

### Question Format Requirements
- **Stem**: "다음 상황 설명을 듣고, [화자]가 [상대방]에게 할 말로 가장 적절한 것을 고르시오. [3점]"
- **Options**: 5 English utterance options
- **Correct Answer**: Must be the most contextually appropriate and helpful utterance
- **Distractors**: Partially appropriate, contextually mismatched, or inappropriately toned utterances

### Transcript Formatting Instructions
- transcript의 마지막 문장은 반드시 다음 영어 문장으로 끝난다(철자·구두점·대괄호 그대로 사용):
   "In this situation, what would [화자] most likely to say to [상대방]?"
 - 위 마지막 문장도 Transcript Length(140–160 words)에 포함된다

### Content Generation Guidelines
- Create complex scenarios requiring experience-based advice
- Ensure the speaker has clear motivation and expertise to offer guidance
- Include realistic contexts where advice-giving is natural and helpful
- Use sophisticated language appropriate for complex situational analysis

**Required JSON Output Format:**
{
  "question": "다음 상황 설명을 듣고, [화자]가 [상대방]에게 할 말로 가장 적절한 것을 고르시오. [3점]",
  "transcript": "[140-160 word situational description in English; ends with the exact line: \"In this situation, what would [화자] most likely to say to [상대방]?\" ]",
  "options": ["Utterance 1", "Utterance 2", "Utterance 3", "Utterance 4", "Utterance 5"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of the situational appropriateness]"
}""",
    "spec": {
        "type": "standard",
        "components": ["question", "transcript", "options"],
        "processing_hints": {},
        "special_features": ["situational_response"]
    }
},
"LC16_17": {
    "title": "듣기 16-17번 - 장문 듣기 (세트형)",
    "content": """Create a CSAT Listening Item 16-17 (Long Listening Set) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Dual assessment - topic identification and detail tracking in extended monologue
- **Cognitive Process**: Process extended content → Extract main topic → Track specific details → Dual evaluation
- **Difficulty Level**: Advanced extended listening with dual assessment requirements

### Discourse Type & Structure
- **Format**: Extended informational monologue
- **Structure Pattern**: Introduction → Topic establishment → Systematic enumeration → Detail explanation → Conclusion
- **Content Flexibility**: Any academic or informational topic with categorizable elements
- **Speaker Role**: Educator, expert, or informational presenter

### Language Specifications
- **Transcript Length**: 180-220 words (approximately 90-110 seconds)
- **Sentence Complexity**: Moderate to complex with academic discourse features
- **Vocabulary Level**: Academic and informational vocabulary
- **Speech Rate**: Measured academic presentation pace
- **Vocabulary Profile**:
  "vocabulary_difficulty": "CSAT+O3000",
  "low_frequency_words": ["예: nutrients"]

### Question Format Requirements
- **Item 16 Stem**: "[화자]가 하는 말의 주제로 가장 적절한 것은?"
- **Item 17 Stem**: "언급된 [항목 유형]이 <u>아닌</u> 것은?"
- **Options**: 5 English options for each question
- **Assessment Focus**: Topic comprehension + detail identification

### Content Generation Guidelines
- Create academic presentations with clear topics and enumerated examples
- Ensure 4-5 specific items are mentioned with one omitted from options
- Include educational contexts appropriate for Korean high school level
- Use clear academic discourse markers and systematic organization

**Required JSON Output Format:**
{
  "set_instruction": "[16~17] 다음을 듣고, 물음에 답하시오.",
  "transcript": "[180-220 word academic monologue in English]",
  "questions": [
    {
      "question_number": 16,
      "question": "[화자]가 하는 말의 주제로 가장 적절한 것은?",
      "options": ["topic1", "topic2", "topic3", "topic4", "topic5"],
      "correct_answer": [1-5],
      "explanation": "[Korean explanation of the topic]"
    },
    {
      "question_number": 17,
      "question": "언급된 [항목 유형]이 <u>아닌</u> 것은?",
      "options": ["item1", "item2", "item3", "item4", "item5"],
      "correct_answer": [1-5],
      "explanation": "[Korean explanation of what was not mentioned]"
    }
  ]
}""",
    "spec": {
        "type": "set",
        "set_size": 2,
        "start_number": 16,
        "components": ["transcript", "questions"],
        "processing_hints": {}
    }
},

"RC18": {
  "title": "읽기 18번 - 목적 파악",
  "content": """Create a CSAT Reading Item 18 (Purpose Identification) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Identifying the primary communicative purpose of a formal notice or announcement
- **Cognitive Process**: Analyze background situation → Trace cause and anticipated outcomes → Infer the writer’s main intent → Match with the most accurate purpose option
- **Difficulty Target**: 중상 (예상 정답률 81–95%, 변별도 0.1–0.2)

### Abstractness & Complexity Controls
- **Abstractness Level (1–9)**: 3
- **Syntactic Complexity Targets (optional)**:
  - avg_words_per_sentence: 18.8
  - avg_clauses_per_sentence: 2.3
  - subordination_ratio: 0.5
- **Vocabulary Profile (optional)**: CSAT+O3000

### Text Type & Structure
- **Format**: Official notice, public letter, or announcement
- **Structure Pattern (mandatory 5-step logic)**:
  A. 상황 설명 (Context Setup) →  
  B. 원인 설명 (Cause/Reason) →  
  C. 기대 내용 (Expected outcome/anticipation) →  
  D. 결론 (Key decision/action) →  
  E. 정서적 마무리 (Closure: thanks/request/next steps)
- **Purpose Location Strategy**:
  - The **main communicative intent must become fully clear only in D–E** after A–C build-up.
  - **Do NOT** reveal the final action/purpose in the **first sentence**.
- **Content Source**: Local government, school, event organizer, or comparable institution
- **Special Placement Rules**:
  - Use contrastive and causal linkers to delay the decisive action until section D.
  - Maintain linear flow; avoid bullet lists inside the passage.

### Greeting & Closing (Hard Constraints)
- The passage MUST be a formal letter or notice that:
  1) **Begins with exactly one of**:
     - `Dear [Name],`
     - `To whom it may concern,`
  2) **Ends with a formal closing**, e.g.:
     - `Sincerely,` (or `Regards,`, `Best regards,`) **followed by a sender name or department**.
- If the generated passage is missing either the greeting or the closing, **regenerate internally** and return **only** the final JSON that satisfies these constraints.
- Do **not** use “Hello,” “Hi,” or other informal greetings.  

### Language Specifications
- **Passage Length**: 120–150 words (English only)
- **Register**: Formal, institutional tone
- **Sentence Style**: Compound–complex sentences preferred; adhere to the syntactic targets above
- **Vocabulary Profile**: CSAT+O3000 with limited AWL items where natural
- **Key Language Features**:
  - Causal markers: “due to”, “as a result”, “because of”
  - Anticipatory phrasing: “many looked forward to”, “we had planned to”
  - Intent verbs (appear late): “announce”, “inform”, “notify”, “postpone”, “cancel”
  - Closure tone: “we regret…”, “we appreciate your understanding”, “thank you for your cooperation”
  - **Vocabulary Profile**:
    "vocabulary_difficulty": "CSAT+O3000",
    "low_frequency_words": ["예: sponsor", "예: exhibit", "예: festival"]

### Question Format Requirements
- **Stem (Korean)**: "다음 글의 목적으로 가장 적절한 것은?"
- **Options (Korean, 5지)**:
  - Action-based 목적 표현, 모두 “~하려고”로 끝남
  - Include **1 correct** option reflecting the **D–E** purpose
  - Include **4 distractors**:
    1) **early-context**: A 또는 초반 정보에 근거한 오해 유도  
    2) **partial cause**: B의 원인 정보만 확대 해석  
    3) **misinference**: C의 기대를 목적과 혼동  
    4) **irrelevant**: 문맥과 무관한 공공 목적
- **Correct Answer**:
  - Must align with the **primary function** of the notice explicitly/implicitly stated in **D–E**.

### Explanation (Korean)
- Concise:
  - **정답 근거**: D–E 구간의 핵심 의도 문장 + 전체 인과 흐름
  - **오답 배제**: 각 선지가 A–C의 일부 정보만 반영하거나 잘못된 추론임을 1–2문장씩 제시

**Required JSON Output Format:**
{
  "question": "다음 글의 목적으로 가장 적절한 것은?",
  "passage": "[120–150 word formal communication in English]",
  "options": ["목적1하려고", "목적2하려고", "목적3하려고", "목적4하려고", "목적5하려고"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of the purpose]"
}""",

  "spec": {
    "type": "standard",
    "components": ["question", "passage", "options", "correct_answer", "explanation"],
    "processing_hints": {}
  }    
},  
"RC19": {
  "title": "읽기 19번 - 심경 변화",
  "content": """Create a CSAT Reading Item 19 (Emotional Change) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Tracking emotional progression in narrative texts
- **Cognitive Process**: Identify initial emotion → Track transition points → Determine final emotion
- **Difficulty Level**: Intermediate emotional analysis requiring inference skills

### Text Type & Structure
- **Format**: Personal narrative or story with clear emotional arc
- **Structure Pattern**: Initial situation → Expectation/hope → Complication → Emotional response
- **Content Flexibility**: Any personal experience involving emotional change
- **Narrative Type**: First-person or third-person emotional journey

### Language Specifications
- **Passage Length**: 100–130 words
- **Sentence Complexity**: Moderate with emotional expression features
- **Vocabulary Level**: Emotional and descriptive vocabulary
- **Reading Level**: Accessible narrative style

### Question Format Requirements
- **Stem**: "다음 글에 드러난 [인물]의 심경 변화로 가장 적절한 것은?"
- **Options**: 5 English emotional change patterns (emotion A → emotion B)
- **Correct Answer**: Must accurately reflect the emotional progression in the text
- **Distractors**: Partial emotions, reversed emotions, unrelated emotions, static emotions

### Enhanced Critical Anti-Leakage Rules
1. The passage MUST NOT contain:
   - Any of the option adjectives.
   - Any synonyms, antonyms, or morphological variants of the option adjectives (including nouns, verbs, adverbs).
   - Any generic emotion adjectives (happy, sad, nervous, confident, relieved, disappointed, frustrated, excited, satisfied, hopeful, etc.).
   - Any directly emotional actions (e.g., smile, frown, cry, cheer).
2. Emotions must be conveyed ONLY through:
   - Neutral physical behaviors (e.g., pausing hands, tapping table, shifting gaze).
   - Contextual actions (e.g., rewriting a draft, checking the clock repeatedly).
   - Subtle physiological cues (e.g., heartbeat quickening, shoulders tightening, breathing slowing).
   - Dialogues or inner thoughts that imply feelings without naming them or using synonyms.
3. The narrative must allow readers to INFER the emotions only by interpreting contextual cues.
4. **Self-check requirement**: Before producing the final output, review the passage and REMOVE any terms that overlap with option words, their synonyms, or direct emotion-related expressions.

### Example Transformation
- Instead of "She felt confident," → "Her keystrokes became faster, filling the page without pauses."
- Instead of "He was nervous," → "He checked the time again and again, his foot moving restlessly under the desk."

### Content Generation Guidelines
- Create relatable personal experience scenarios
- Ensure emotional progression is clear but only through indirect evidence
- Avoid all explicit or near-explicit emotion vocabulary
- Maintain a realistic narrative style suitable for inference

### Options Language Rule
- All option words MUST be **English adjectives** (e.g., "anxious → relieved").
- Do NOT use Korean words or translations for options.

### Vocabulary Profile
"vocabulary_difficulty": "CSAT+O3000",
"low_frequency_words": ["예: sponsor", "예: exhibit", "예: festival"]  // 예시 단어, 반드시 사용해야 하는 것은 아님

**Required JSON Output Format:**
{
  "question": "다음 글에 드러난 [character_name]의 심경 변화로 가장 적절한 것은?",
  "passage": "[100–130 word narrative with emotional progression, strictly without emotional adjectives, synonyms, or obvious emotion words]",
  "options": ["adjective1 → adjective2", "adjective3 → adjective4", "adjective5 → adjective6", "adjective7 → adjective8", "adjective9 → adjective10"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of the emotional change, focusing only on contextual cues such as actions or physical reactions]",
  "vocabulary_difficulty": "CSAT+O3000",
  "low_frequency_words": ["예: sponsor", "예: exhibit", "예: festival"]
}
""",

  "spec": {
    "type": "standard",
    "components": ["question", "passage", "options", "correct_answer", "explanation", "vocabulary_difficulty", "low_frequency_words"],
    "processing_hints": {},
    "special_features": ["emotional_change"]
  }
},  
"RC20": {
    "title": "읽기 20번 - 주장 파악",
    "content": """Create a CSAT Reading Item 20 (Argument Identification) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Identifying the main argument in persuasive texts
- **Cognitive Process**: Analyze argumentative structure → Extract central claim → Match with argument options
- **Difficulty Level**: Intermediate argumentative comprehension

### Text Type & Structure
- **Format**: Argumentative or persuasive text
- **Structure Pattern**: Problem presentation → Analysis → Proposed solution → Supporting reasoning
- **Content Flexibility**: Any topic suitable for argumentative treatment
- **Argument Type**: Constructive proposals or recommendations

### Language Specifications
- **Passage Length**: 130–160 words
- **Sentence Complexity**: Moderate to complex with argumentative features
- **Vocabulary Level**: Argumentative and analytical vocabulary
- **Reading Level**: Academic argumentative style

### Question Format Requirements
- **Stem**: "다음 글에서 필자가 주장하는 바로 가장 적절한 것은?"
- **Options**: 5 Korean argument statements ending with "~해야 한다"
- **Correct Answer**: Must capture the author's main argument or recommendation
- **Distractors**: Supporting points, opposite arguments, partial arguments, unrelated claims

### Content Generation Guidelines
- Create persuasive texts with clear argumentative structure
- Ensure the main argument is well-supported but requires synthesis to identify
- Include topics relevant to Korean high school students and society
- Use clear argumentative markers and logical progression

### Vocabulary Profile
"vocabulary_difficulty": "CSAT+O3000",
"low_frequency_words": ["예: sponsor", "예: exhibit", "예: festival"]  // 예시 단어, 반드시 사용해야 하는 것은 아님

**Required JSON Output Format:**
{
  "question": "다음 글에서 필자가 주장하는 바로 가장 적절한 것은?",
  "passage": "[130–160 word argumentative text in English]",
  "options": ["주장1해야 한다", "주장2해야 한다", "주장3해야 한다", "주장4해야 한다", "주장5해야 한다"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of the argument]"
}""",

    "spec": {
        "type": "standard",
        "components": ["question", "passage", "options", "correct_answer", "explanation"],
        "processing_hints": {}
    }    
},        

"RC21": {
  "title": "읽기 21번 - 함축 의미 추론",
  "content": """
Create a CSAT Reading Item 21 (Underlined Expression Inference) following these specifications.

## ITEM CHARACTERISTICS & METHODOLOGY
### Assessment Objective
- **Core Skill**: Inferring the contextual meaning of metaphorical or idiomatic expressions
- **Cognitive Process**: Analyze surrounding context → Interpret figurative expression → Select meaning consistent with passage
- **Difficulty Target**: 중상 수준 (예상 정답률 40–55%, 변별도 0.3–0.4)

### Text Type & Structure
- **Format**: Academic explanatory passage (history, science, philosophy, culture, society)
- **Structure Pattern**: Concept introduction → Analysis → Use of metaphorical expression → Explanation/contrast
- **Expression Placement**: The underlined metaphorical/idiomatic expression **must appear in the final 1–2 sentences**, summarizing or concluding the argument.

### Expression Selection Policy
- **Ban rule**: Do not use the expression **“the tip of the iceberg.”**
- Instead, freely select any classic idiom or metaphor that:
  1) is widely recognized in academic or literary contexts,
  2) is appropriate for CSAT-level learners,
  3) can naturally fit the passage’s conclusion.

### Language Specifications
- **Passage Length**: 150–180 words
- **Sentence Complexity**: Complex sentences with academic cohesion
- **Vocabulary Level**: CSAT-level academic vocabulary
- **Reading Level**: High academic text, comparable to actual CSAT passages
- **Underline exactly one** expression in the passage with HTML `<u> ... </u>`.


### Vocabulary Profile
"vocabulary_difficulty": "CSAT+O3000",
"low_frequency_words": ["예: sponsor", "예: exhibit", "예: festival"]  // 예시 단어, 반드시 사용해야 하는 것은 아님


### Question Format Requirements
- **Stem (Korean)**: "밑줄 친 <u>EXPRESSION</u>이 다음 글에서 의미하는 바로 가장 적절한 것은? [3점]"
  - Replace EXPRESSION with the exact underlined expression.
- **Options (Korean, 5지)**:
  - Include: (1) literal meaning, (2) partial/limited meaning, (3) opposite meaning, (4) unrelated meaning, (5) correct figurative meaning.
  - **Do NOT prefix options with any numbers or symbols** (예: `① ② ③ ④ ⑤`, `1.`, `(1)`, `1)` 등).  
    Each option must be **plain text only**.
- **Correct Answer**: Provide the correct option index **as an integer (1–5)**, not text.



### Explanation (Korean)
- 간명하게:
  - 정답 근거: 본문 맥락 + 표현의 비유적 의미 일치 근거
  - 오답 배제: 각 보기별 왜 틀렸는지 1–2문장씩

### Output JSON (Required)
{
  "question": "밑줄 친 <u>EXPRESSION</u>이 다음 글에서 의미하는 바로 가장 적절한 것은? [3점]",
  "passage": "[150–180 word academic passage with <u>EXPRESSION</u> in English]",
  "options": ["...", "...", "...", "...", "..."],   // 번호/기호 없이 순수 텍스트 5개
  "correct_answer": 5,   // 정답 번호를 반드시 정수로
  "explanation": "[한국어 해설: 정답 근거 및 오답 배제 이유]"
}

### Self-Check BEFORE finalizing (hard constraints)
1) The passage **must not contain** the string “the tip of the iceberg.”
2) Exactly **one** `<u> ... </u>` expression is present, and the **same string** appears in the stem.
3) Word count of the passage is **150–180**.
4) Options are in **Korean** and follow the distractor policy.
5) `correct_answer` is an **integer 1–5** that matches the correct option.
6) **Options MUST NOT start with any numbering or bullets**.
""",
  "spec": {
    "type": "standard",
    "components": ["question", "passage", "options", "correct_answer", "explanation"],
    "processing_hints": {
      "passage": "underline_marking"
    },
    "controls": {
      "ban_expressions": ["the tip of the iceberg"]
    }
  }
},   
"RC22": {
  "title": "읽기 22번 - 요지 파악",
  "content": """Create a CSAT Reading Item 22 (Main Point Identification) following these specifications.

### ITEM CHARACTERISTICS & METHODOLOGY

**Assessment Objective**
- **Core Skill:** The ability to identify the **central argument** of an explanatory text and **synthesize key information** to extract the main message.
- **Cognitive Process:** Analyze the logical flow of the entire passage and derive the main point by integrating all information, not just from a single section.
- **Difficulty Target:** **중상** (예상 정답률 70–80%, 변별도 0.2–0.3)

**Abstractness & Complexity Controls**
- **Abstractness Level (1–9):** 5
- **Syntactic Complexity Targets (optional):**
  - avg_words_per_sentence: 20.7
  - avg_clauses_per_sentence: 2.7
  - subordination_ratio: 0.5
- **Vocabulary Profile (optional):** Academic and explanatory vocabulary

**Text Type & Structure**
- **Format:** Explanatory or expository text
- **Structure Pattern:** Randomly select one of the three:
  1. **Common Belief–Rebuttal:** Introduce a common belief → Rebuttal → Author’s true argument (main point).
  2. **Problem–Solution:** Present a phenomenon or problem → Analyze causes → Offer and explain a solution (main point).
  3. **Argumentative Progression:** Pose a question/phenomenon → Provide evidence/examples → Synthesize into a conclusion (main point).
- **Type-Specific Policy:** The main point must not be identifiable from the first sentence alone; require integrated comprehension.

### Language Specifications
- **Passage Length:** 140–170 words (English only)
- **Sentence Style:** Academic cohesion; complexity aligned to the above targets
- **Question & Options:** Korean
- **Explanation:** Korean, concise

### Vocabulary Profile
"vocabulary_difficulty": "CSAT+O3000",
"low_frequency_words": ["예: sponsor", "예: exhibit", "예: festival"]  // 예시 단어, 반드시 사용해야 하는 것은 아님

### Question Format Requirements
- **Stem (Korean):** "다음 글의 요지로 가장 적절한 것은?"
- **Options (Korean, 5지):**
  - **Write 5 Korean statements WITHOUT any leading numbering or markers.**  
    - ❌ Do NOT prefix with “①”, “②”, “③”, “④”, “⑤”, “1.”, “-”, bullets, or parentheses.
  - Distractors must include:
    - The **common belief** (if present at the beginning)
    - **Partial/subordinate points** mentioned in the passage
    - **Related but non-central** statements
    - A statement **opposite** to the main point
- **Correct Answer:** Exactly one, matching the central message of the passage

### Explanation (Korean)
- Must include:
  - 정답 근거: 본문 전개 + 유형별 핵심 근거
  - 오답 배제: 각 선택지가 틀린 이유 간략히 (1–2문장씩)

### OUTPUT (validator-compatible; JSON only)
Return **ONLY** valid JSON. Use the exact keys below.  
`correct_answer`는 반드시 문자열 `"1"`~`"5"` 중 하나.  
**No extra keys** beyond the schema.

{
  "question": "다음 글의 요지로 가장 적절한 것은?",
  "passage": "[140–170 word academic passage in English]",
  "options": [
    "Option sentence 1",
    "Option sentence 2",
    "Option sentence 3",
    "Option sentence 4",
    "Option sentence 5"
  ],
  "correct_answer": "1",
  "explanation": "정답 근거 및 오답 배제 이유를 한국어로 간결히 작성"
}

### Hard Constraints (Self-Check)
- Passage word count 140–170 (English only).""",

  "spec": {
    "type": "standard",
    "components": ["question", "passage", "options", "correct_answer", "explanation"],
    "processing_hints": {
      "passage": "main_point_explanation"
    }
  }
},     
"RC23": {
  "title": "읽기 23번 - 주제 파악",
  "content": """Create a CSAT Reading Item 23 (Topic Identification) following these specifications.

### ITEM CHARACTERISTICS & METHODOLOGY

**Assessment Objective**
- **Core Skill:** The ability to **inductively infer the overall topic** of a text by synthesizing various arguments and pieces of information.
- **Cognitive Process:** Identify the common thread or pattern running through the passage's examples and arguments to deduce its ultimate message.
- **Difficulty Target:** **중상 수준** (예상 정답률 53%, 변별도 0.3–0.4)

**Abstractness & Complexity Controls**
- **Abstractness Level (1–9):** 5
- **Syntactic Complexity Targets (optional):**
  - avg_words_per_sentence: 17.9
  - avg_clauses_per_sentence: 2.3
  - subordination_ratio: 0.4
- **Vocabulary Profile (optional):** Academic and thematic vocabulary

**Text Type & Structure**
- **Format:** Expository text about social, cultural, or academic topics
- **Structure Pattern:** Randomly select one of the three when generating the passage:
  1. **Sequential Examples:** Present a phenomenon or a specific example first → List and explain two or more similar or related examples → Synthesize these examples to implicitly reveal the common theme or topic.
  2. **Comparison/Contrast:** Introduce two subjects (A and B) → Describe their features or effects by contrasting them repeatedly → Conclude by explaining the significance of their relationship or differences.
  3. **Historical Shift–Consequence:** Describe a situation from a specific era or before a key event → Introduce the catalyst for change (e.g., technological or social shift) → Detail the consequences and implications that arose from this change.
- **Type-Specific Policy:** The main topic must not be identifiable from the first sentence alone; require integrated understanding of the entire passage.

### Language Specifications
- **Passage Length:** 130–160 words (English only)
- **Sentence Style:** Academic cohesion; complexity aligned to the above targets
- **Question & Options:** Korean
- **Explanation:** Korean, concise

### Vocabulary Profile
"vocabulary_difficulty": "CSAT+O3000",
"low_frequency_words": ["예: sponsor", "예: exhibit", "예: festival"]  // 예시 단어, 반드시 사용해야 하는 것은 아님

### Question Format Requirements
- **Stem (Korean):** "다음 글의 주제로 가장 적절한 것은?"
- **Options (English, 5지):**
   - **Write 5 concise English topic statements WITHOUT any leading numbering or markers.**
   - ❌ Do NOT prefix with “①”, “②”, “③”, “④”, “⑤”, “1.”, “-”, bullets, or parentheses.
  - Distractors must include:
    - Present a **partial example or phenomenon** from the passage as if it were the main topic
    - Offer a topic that is **too broad or too narrow**
    - Use a statement that focuses on only one side/aspect of the contrast
    - Include a concept not discussed in the passage
- **Correct Answer:** Exactly one, comprehensively capturing the inferred topic

### Explanation (Korean)
- Must include:
  - 정답 근거: 본문 맥락 + 유형별 핵심 근거
  - 오답 배제: 각 선택지별 왜 틀렸는지 1–2문장


### OUTPUT (validator-compatible; JSON only)
Return **ONLY** valid JSON. Use the exact keys below.  

"correct_answer"는 반드시 문자열 "1", "2", "3", "4", "5" 중 하나여야 한다.  
❌ 절대로 옵션의 텍스트를 넣지 말라.  
✅ 예: `"correct_answer": "3"`  
❌ 예: `"correct_answer": "환경 보호의 필요성"` (금지)

{
  "question": "다음 글의 주제로 가장 적절한 것은?",
  "passage": "[130–160 word academic passage in English]",
  "options": [
    "Option sentence 1",
    "Option sentence 2",
    "Option sentence 3",
    "Option sentence 4",
    "Option sentence 5"
  ],
  "correct_answer": "1",
  "explanation": "정답 근거 및 오답 배제 이유를 한국어로 간결히 작성",
  "metadata": {
    "item_number": 23,
    "item_type": "Reading",
    "skill_focus": "Topic Identification",
    "difficulty": "중상",
    "abstractness_level": 5,
    "syntactic_complexity": {
      "avg_words_per_sentence": 17.9,
      "avg_clauses_per_sentence": 2.3,
      "subordination_ratio": 0.4
    },
    "vocabulary_difficulty": "Academic and thematic vocabulary",
    "passage_word_count": {PWC_EXAMPLE},
    "type_specific_metadata": {
      "passage_structure": "{STRUCTURE_PATTERN_EN}"
    },
    "low_frequency_words": []
  }
}

### Hard Constraints (Self-Check)
- Passage word count 130–160 (English only).
- Options are Korean, exactly 5, and follow the type-specific distractor policy.
- `correct_answer` is a string "1"–"5" that matches the correct option.
- Output is JSON only (no fences, no extra text).""",

  "spec": {
    "type": "standard",
    "components": ["question", "passage", "options", "correct_answer", "explanation"],
    "processing_hints": {
      "passage": "expository_theme"
    }
  }
},
"RC24": {
  "title": "읽기 24번 - 제목 추론",
  "content": """Create a CSAT Reading Item 24 (Title Inference) following these specifications.

### ITEM CHARACTERISTICS & METHODOLOGY

**Assessment Objective**
- **Core Skill:** Inferring appropriate titles for complex texts
- **Cognitive Process:** Analyze the entire text, synthesize main themes, and select the optimal title
- **Difficulty Target:** **중상** (예상 정답률·변별도는 시스템 프롬프트 가이드에 준함)

**Abstractness & Complexity Controls**
- **Abstractness Level (1–9):** 6
- **Syntactic Complexity Targets (optional):**
  - avg_words_per_sentence: 20.7
  - avg_clauses_per_sentence: 2.2
  - subordination_ratio: 0.38
- **Vocabulary Profile (optional):** Advanced academic vocabulary

**Text Type & Structure**
- **Format:** Complex expository or analytical text
- **Structure Pattern:** Randomly select one of the three when generating the passage:
  1. **Contrast–Synthesis:** Present two opposing concepts (A and B) → Contrast their features → Conclude by synthesizing how they interact or form a new meaning
  2. **Problem–Solution:** Analyze a problem in detail → Present a comprehensive solution in the latter half
  3. **Historical–Analytical:** Connect a current phenomenon to its historical origins/traditions → Show how it inherits legacies while creating new value
- **Type-Specific Policy:** The core argument must not be explicitly stated in the first sentence; the title must synthesize the entire logical development

### Language Specifications
- **Passage Length:** 150–180 words (English only)
- **Sentence Style:** Academic cohesion; complexity aligned to the above targets

### Vocabulary Profile
"vocabulary_difficulty": "CSAT+O3000",
"low_frequency_words": ["예: sponsor", "예: exhibit", "예: festival"]  // 예시 단어, 반드시 사용해야 하는 것은 아님

### Question Format Requirements
- **Stem (Korean):** "다음 글의 제목으로 가장 적절한 것은?"
- **Options (English, 5지):**
  - **Write 5 English title statements WITHOUT numbering or markers.**  
    - ❌ Do NOT prefix with “①”, “②”, “③”, “④”, “⑤”, “1.”, “-”, bullets, or parentheses.
- Distractors must include:
   - Present a **partial example or phenomenon** from the passage as if it were the main topic
   - Offer a topic that is **too broad or too narrow**
   - Use a statement that focuses on only one side/aspect of the contrast
   - Include a concept not discussed in the passage
- **Correct Answer:** Must capture the essence and scope of the entire text, reflecting the synthesized argument/conclusion

### Explanation (Korean)
- Must include:
  - 정답 근거: 본문 맥락 + 유형별 핵심 근거
  - 오답 배제: 각 선택지별 틀린 이유 간략히 (1–2문장)

### OUTPUT (validator-compatible; JSON only)
Return **ONLY** valid JSON. Use the exact keys below.  
`correct_answer`는 반드시 문자열 `"1"`~`"5"` 중 하나.

{
  "question": "다음 글의 제목으로 가장 적절한 것은?",
  "passage": "[150–180 word analytical passage in English]",
  "options": [
    "Option sentence 1",
    "Option sentence 2",
    "Option sentence 3",
    "Option sentence 4",
    "Option sentence 5"
  ],
  "correct_answer": "1",
  "explanation": "정답 근거 및 오답 배제 이유를 한국어로 간결히 작성",
  "metadata": {
    "item_number": 24,
    "item_type": "Reading",
    "skill_focus": "Title Inference",
    "difficulty": "중상",
    "abstractness_level": 6,
    "syntactic_complexity": {
      "avg_words_per_sentence": 20.7,
      "avg_clauses_per_sentence": 2.2,
      "subordination_ratio": 0.38
    },
    "vocabulary_difficulty": "Advanced academic vocabulary",
    "passage_word_count": {PWC_EXAMPLE},
    "type_specific_metadata": {
      "passage_structure": "{STRUCTURE_PATTERN_EN}"
    },
    "low_frequency_words": []
  }
}

### Hard Constraints (Self-Check)
- Passage word count 150–180 (English only).
- Options are English, exactly 5, and follow the type-specific distractor policy.
- `correct_answer` is a string "1"–"5" that matches the correct option.
- Output is JSON only (no fences, no extra text).""",

  "spec": {
    "type": "standard",
    "components": ["question", "passage", "options", "correct_answer", "explanation"],
    "processing_hints": {
      "passage": "complex_analysis"
    }
  }
},    
"RC25": {
  "title": "읽기 25번 - 도표 분석",
  "content": """Create a CSAT Reading Item 25 (Chart Analysis) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY
### Assessment Objective
- **Core Skill**: 도표 데이터와 텍스트 진술 간 일치성 판단 능력 측정
- **Processing Pattern**: 도표 정보 추출 → 각 선택지별 데이터 확인 → 불일치 요소 탐지
- **Evaluation Focus**: 시각적 데이터와 언어적 진술 간의 정확한 대조 분석 능력

### Discourse Structure
- **Pattern**: 상황 설명(그래프/도표 소개) → ①~⑤ 진술을 하나의 단락 안에서 자연스럽게 제시 → 각 진술이 도표와 비교 가능해야 함
- **Flow**: 그래프 개요 설명 → 연도/항목/지역 비교 → ①~⑤ 진술 → 그 중 정확히 하나는 도표와 모순
- **Natural Embedding Rule (CRITICAL)**:
- ①~⑤는 **각 진술의 문장 맨 앞에서 시작**해야 한다. 형식은 정확히 `①␠문장... ②␠문장... ③␠문장... ④␠문장... ⑤␠문장...`이며, 
- **숫자 뒤에 공백 1칸**을 둔다. **문장 끝에 `... ①.`처럼 달아붙이는 형식 금지**.

- **Number Placement (CRITICAL)**: Each numbered statement **must begin** with its circled numeral followed by a single space. 
- Pattern must match: `(^|[.!?]\s)①\s.+?[.!?]\s②\s.+?[.!?]\s③\s.+?[.!?]\s④\s.+?[.!?]\s⑤\s.+?$` (DOTALL).
- If any numeral appears **at the end of a sentence or clause** (e.g., `…, 20% ①.`), **REGENERATE**.
  - **목록·줄바꿈 금지**: ①~⑤ 앞뒤로 줄바꿈 없이, 문장 흐름 속에 쉼표·세미콜론·접속사(and, while, whereas 등)로 연결한다.
  - 각 번호 문장의 길이는 **18~25 words** 범위 안에서 균형 있게 작성한다.
  - 한 문장에서는 **최대 2개 집단(국가/지역/연도/범주)까지만** 언급한다 (인지부하 방지).
  - **Numbering Enforcement**: The passage MUST embed **all five circled numerals** exactly once and **in order** — `① ② ③ ④ ⑤` — **inline** within the same paragraph. **Do NOT** omit, reorder, repeat, or place them on separate lines. If this fails, **REGENERATE**.
  ✅ DO: “① In 2018, Country A … . ② By 2020, Country B … . ③ In 2022, … . ④ Across all … . ⑤ However, … .”
  ❌ DON’T: “… 20% ①. … unchanged ②.”  (문장 끝에 번호 금지)

### Language Specifications
- **Passage Length**: 115–135 words (영문 전용, 번호 포함)
- **Sentence Complexity**: Complex, with comparative/descriptive structures (~2.2 clauses/sentence)
- **Vocabulary Level**: Statistical, comparative, and data-related vocabulary.
- **Variety of Expression (MANDATORY)**:
  - 다섯 문장(①~⑤) 중 **최소 두 문장**은 **구체적 수치(%)**를 직접 포함.
  - **최소 한 문장**은 **배수/비율 관계**(e.g., "twice", "three times")를 포함(근사 금지, chart_data로 정확히 뒷받침).
  - **최소 한 문장**은 **변화 없음/유지** 유형.
  - **최소 한 문장**은 **순위/최고·최저** 언급.

### Vocabulary Profile
"vocabulary_difficulty": "CSAT+O3000",
"low_frequency_words": ["예: sponsor", "예: exhibit", "예: festival"]  // 예시 단어, 반드시 사용해야 하는 것은 아님

### Question Format Requirements
- **Stem**: "다음 도표의 내용과 일치하지 <u>않는</u> 것은?"
- **Passage**: 반드시 위 구조를 따를 것
- **Options**: ["①", "②", "③", "④", "⑤"] (번호만)
- **Correct Answer**: 정수 **1~5 중 하나** (number)
- **Explanation**: 한국어로, ①~⑤ 각각에 대해 도표 수치·추세 근거로 일치/불일치 판정. 정답(오답 진술)이 왜 틀렸는지 **구체 수치/증감 방향/배수 관계**를 인용하여 설명한다.

### Incorrect Statement Position (CRITICAL)
- **Position Balance Rule**: Do **not** default to ⑤. If a position hint is provided (e.g., `wrong_index_hint` in context), use it. Otherwise, **choose uniformly among ①–⑤** and **prefer ①–④ when uncertain** to avoid positional bias.
- The item must be valid for **any** wrong index; do not structure the passage to make ⑤ systematically easiest.

### Chart Data Schema (STRICT)
You MUST produce chart_data in one of the following STRICT schemas. 
Do NOT mix schemas. Do NOT add extra fields.

(1) GRAPH schema (bar | line | stacked_bar | pie)
- Structure:
  {
    "type": "bar" | "line" | "stacked_bar" | "pie",
    "title": string,
    "labels": string[],
    "datasets": [
      { "label": string, "data": number[] }
    ]
  }

### Graph Complexity Guardrails (CRITICAL)
- To ensure non-trivial comparisons, follow ALL of these:
  - **Type**: Use **bar** or **line** (pie 금지) **unless** the task is share-of-whole only. Prefer **grouped bar** or **multi-series line**.
  - **Labels**: **≥ 4** categories (e.g., age groups, activities, years).
  - **Datasets**: **≥ 2** series (e.g., regions/genders/years). Single-series charts **금지**.
  - **Comparative Structure**: Ensure **at least one rank inversion across series** (there exist labels A,B where Series1(A)>Series1(B) but Series2(A)<Series2(B)).
  - Include **both within-series rankings** (highest/lowest inside one group) **and cross-series comparisons** (Group X vs Group Y for the same label).
  - If time-series, include **≥ 3 points** per series and **non-identical trends** across series (e.g., one increases while another decreases or stagnates).

(2) TABLE schema (table)
- Use ONLY if necessary for clarity.
- Structure:
  {
    "type": "table",
    "title": string,
    "columns": string[],
    "rows": Array<[string, number, number]>
  }

### Output Schema Guardrails
- DO NOT output fields not listed in Output Format.
- "correct_answer" MUST be a **number** (1–5), not a string.
- "options" MUST be exactly ["①","②","③","④","⑤"].
- **Passage Compliance Check**: Before returning JSON, self-check that the passage **contains ①②③④⑤ in order in one paragraph**. If not, **regenerate**.

### Passage–Chart Consistency Rules
- The passage’s ①–⑤ statements MUST be evaluated strictly against chart_data.
- Exactly **4 statements match** chart_data and **1 contradicts**.
- Ratios/multiples (e.g., “twice”, “three times”) must be **exact** per chart_data (no rounding). If not exact, use comparative wording (“more than”, “less than”) instead.
- Check consistency before output.

### Variation Rules
- Vary the opener sentence.
- Mix relation types across ①–⑤ (increase/decrease, highest/lowest, unchanged, ratio/multiple, ranking, threshold like “all above 20%”).

### Output Format
Respond ONLY with a JSON object structured as:

{
  "question": "다음 도표의 내용과 일치하지 <u>않는</u> 것은?",
  "passage": "115–135-word English paragraph with overview + naturally embedded ①–⑤ statements (no line breaks, no bulleting).",
  "options": ["①", "②", "③", "④", "⑤"],
  "correct_answer": (number 1–5),
  "explanation": "한국어 해설: 각 번호 진술의 사실 여부를 수치·추세 근거로 판정, 정답은 왜 틀렸는지 명시.",
  "chart_data": {
    "type": "...",
    "title": "...",
    "labels": [...],
    "datasets": [...]
  }
}
""",
  "spec": {
    "type": "standard",
    "components": ["question", "passage", "options", "correct_answer", "explanation", "chart_data"],
    "processing_hints": { "chart_data": "structured_chart" },
    "special_features": ["chart_analysis"]
  }
},       
"RC26": {
  "title": "읽기 26번 - 인물 정보 불일치",
  "content": """Create a CSAT Reading Item 26 (Biographical Information Mismatch) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: 인물 소개 텍스트와 선택지 간 사실 일치성 판단 능력 측정
- **Processing Pattern**: 텍스트 정보 추출 → 각 선택지별 사실 확인 → 불일치 요소 탐지
- **Evaluation Focus**: 인물 관련 사실 정보와 선택지 간의 정확한 대조 분석 능력

### Discourse Structure
- **Pattern**: 인물 소개 → 출생 정보 → 초기 경력 → 주요 업적 → 경력 발전 → 말년 활동 → 사망 정보 → 추가 성취
- **Flow**: 기본 정보 → 배경 → 시작점 → 전환점 → 전성기 → 후기 → 종료 → 부가 정보

### Language Specifications
- **Passage Length**: 130-150 words
- **Sentence Complexity**: Moderate, featuring chronological and descriptive sentences
- **Vocabulary Level**: Biographical and descriptive vocabulary
- **Reading Level**: Accessible narrative and expository style

### Vocabulary Profile
"vocabulary_difficulty": "CSAT+O3000",
"low_frequency_words": ["예: sponsor", "예: exhibit", "예: festival"]  // 예시 단어, 반드시 사용해야 하는 것은 아님

### Question Format Requirements
- **Stem**: "{person_name_en}에 관한 다음 글의 내용과 일치하지 <u>않는</u> 것은?"
  - 인물명은 지문 표기의 영문 그대로 사용 (번역/음차 금지).
  - 여러 인명이 언급되면 본문 중심 인물(첫 문단 주어)을 사용.

- **Options**:
  - 5개 선택지 (모두 한국어).
  - 구체적 사실을 진술하는 문장.
  - 정확히 1개는 본문과 불일치.
  - **불일치 선택지는 부정형 문장이 아니라 세부 정보 오류(연도, 장소, 기관명, 업적, 수상명 등)로 구성.**
  - 나머지 4개는 본문과 정확히 일치하되 표현을 다소 변형하여 자연스럽게 제시.

### Content Generation Guidelines
- 인물은 잘 알려진 실제 인물이어야 함.
- 불일치는 본문과 유사해 보이지만 세부적으로 틀린 정보여야 함.
- **절대 “~하지 않았다, 관심이 없었다” 식의 부정형 문장 사용 금지.**
- Distractors는 직역 대신 자연스러운 한국어 표현으로 변형.

### Self-check Rules
- 최종 출력 전에 확인:
  1. 정답 선택지에 부정형 문장이 없는가?
  2. 정답 선택지가 본문과 크게 동떨어진 “엉뚱한 내용”이 아닌가?
  3. 불일치는 세부 정보 오류(연도/장소/기관명 등)로 구현되었는가?

**Required JSON Output Format:**
{
  "question": "{person_name_en}에 관한 다음 글의 내용과 일치하지 <u>않는</u> 것은?",
  "passage": "[Biographical text about a notable person in English]",
  "options": ["사실진술1", "사실진술2", "사실진술3", "사실진술4", "사실진술5"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of the factual contradiction]"
}""",

  "spec": {
    "type": "standard",
    "components": ["question", "passage", "options", "correct_answer", "explanation"],
    "processing_hints": {},
    "special_features": ["biographical_info"]
  }
}, 
"RC27": {
  "title": "읽기 27번 - 안내문 불일치",
  "content": """Create a CSAT Reading Item 27 (Notice Mismatch) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: 안내문 정보와 선택지 간 사실 일치성 판단 능력 측정
- **Processing Pattern**: 안내문 정보 추출 → 각 선택지별 사실 확인 → 불일치 요소 탐지
- **Evaluation Focus**: 공식 안내문과 선택지 간의 정확한 사실 대조 능력

### Discourse Structure
- **Pattern**: 제목/헤드라인 → 이벤트 소개 → 일정 정보 → 장소 정보 → 참가 조건 → 신청 방법 → 연락처 → 추가 안내
- **Flow**: 헤더 → 목적 → 시간 → 위치 → 자격 → 절차 → 문의 → 특별사항
- **Key Positioning**: 핵심 정보(시간, 장소, 조건)는 중앙부에 배치되고 절차 정보는 하단부에 위치

### Language Specifications
- **Passage Length**: 120–140 words (count words by spaces; strictly enforce)
- **Sentence Complexity**: Simple to moderate, clearly conveying rules, dates, and conditions.
- **Vocabulary Level**: Informational/procedural vocabulary for events and registration.
- **Reading Style**: Straightforward informational notice.

### Vocabulary Profile
"vocabulary_difficulty": "CSAT+O3000",
"low_frequency_words": ["예: sponsor", "예: exhibit", "예: festival"]  // 예시 단어, 반드시 사용해야 하는 것은 아님

### Question Format Requirements
- **Stem**: “[이벤트 제목(영문)]에 관한 다음 안내문의 내용과 일치하지 <u>않는</u> 것은?” 
  - The event title in the stem MUST be copied exactly from the passage’s Title line (no quotes).
  - **Do NOT use any HTML or Markdown tags** (e.g., no <u>, no **).
- **Options**: Exactly 5 Korean sentences, each stating a specific factual claim from the notice.
- **Correct Answer**: The ONLY option (1–5, integer) that contradicts the notice.
- **Distractors**: 4 options that exactly match facts stated in the notice.

### Content Generation Guidelines
- Use any official announcement with concrete conditions (event, competition, program, policy notice).
- Include specific, checkable facts (dates, deadlines, fees, locations, eligibility, procedures).

### Formatting Instructions (ASCII-styled layout)
- The notice MUST use the following **exact** structure and dividers:
  1) A top divider line of "=" repeated at least 40 times (e.g., "============================================").
  2) A single line with the EVENT TITLE in ALL CAPS (e.g., "2025 INTERNATIONAL STUDENT FORUM").
  3) An identical divider line of "=".
  4) The labeled sections, each on its own line in this exact order and spelling:
     Title:, Date:, Location:, Eligibility:, Registration:, Fee:, Contact:, Note:
     - Each label is followed by a space and its content on the same line.
  5) A **bottom** divider line identical to the top/between dividers.
- Do NOT use Markdown (#, ##, **, *, -) or HTML tags anywhere.
- Do NOT include double quotes inside string values.
- Ensure the passage total length is 120–140 words.

### OUTPUT (STRICT)
Return ONE JSON object ONLY with these exact keys and types—no extra keys:
- question (string; Korean; NO HTML/Markdown)
- passage (string; English; ASCII-styled layout as above)
- options (array of exactly 5 Korean strings)
- correct_answer (integer 1–5; NOT a string)
- explanation (string; Korean; concise: 정답 근거 + 오답 배제)

### HARD CONSTRAINTS CHECKLIST (the model MUST self-verify before finalizing)
- [ ] No code fences or backticks in output.
- [ ] No HTML/Markdown tags anywhere.
- [ ] passage has top divider, ALL-CAPS title line, identical divider, all 8 labeled lines in order, and a bottom divider identical to the others.
- [ ] passage length is 120–140 words (by spaces).
- [ ] options length is exactly 5; each is a Korean sentence.
- [ ] correct_answer is an integer 1–5 and matches the only contradictory option.
- [ ] Only the required keys are present; no extra fields (e.g., no rationale).""",

  "spec": {
    "type": "standard",
    "components": ["question", "passage", "options", "correct_answer", "explanation"],
    "processing_hints": { "passage": "structured_notice" },
    "special_features": ["notice_mismatch"]
  }
},
"RC28": {
  "title": "읽기 28번 - 안내문 일치",
  "content": """Create a CSAT Reading Item 28 (Notice Match) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: 이벤트 안내문 정보와 선택지 간 사실 일치성 판단 능력 측정
- **Processing Pattern**: 안내문 정보 추출 → 각 선택지별 사실 확인 → 일치 요소 식별
- **Evaluation Focus**: 이벤트 안내문과 선택지 간의 정확한 사실 일치 능력

### Discourse Structure
- **Pattern**: 이벤트 제목 → 목적/개요 → 일정 정보 → 장소 정보 → 프로그램 내용 → 참가 방법 → 혜택/특전 → 연락처
- **Flow**: 헤더 → 취지 → 시간 → 위치 → 활동 → 신청 → 보상 → 문의
- **Key Positioning**: 핵심 정보(일정, 장소, 내용)는 중앙부에 배치되고 참가 정보는 하단부에 위치

### Language Specifications
- **Passage Length**: 120–140 words
- **Register**: Neutral, factual
- **Style**: Informational notice with structured ASCII layout

### Vocabulary Profile
"vocabulary_difficulty": "CSAT+O3000",
"low_frequency_words": ["예: sponsor", "예: exhibit", "예: festival"]  // 예시 단어, 반드시 사용해야 하는 것은 아님

### Passage Formatting Rules (STRICT)
- The notice must be surrounded by ASCII divider lines made of "=" at the top and bottom.
- Layout order:
  1) Top divider line (at least 40 "=" signs)
  2) Event title in ALL CAPS (one line only)
  3) Identical divider line of "="
  4) Each labeled section, exactly one per line, using the following labels in English:
     Title:, Date:, Time:, Location:, Eligibility:, Registration:, Fee:, Program:, Benefits:, Contact:, Note:
     - Use at least 6 of these fields (Title, Date, Location, Registration, Contact are mandatory).
     - Each label must be followed by a space and the value on the same line.
  5) Bottom divider line identical to the top divider.
- No HTML, Markdown, or bullet points.
- No blank lines inside the notice.
- Passage length must be 120–140 words total.

### Question Format Requirements
- **Stem**: "[이벤트 제목(영문)]에 관한 다음 안내문의 내용과 일치하는 것은?"
  - The event title must be copied exactly from the ALL CAPS title line.
- **Options**:
  - Exactly 5 Korean sentences.
  - Each option is a single line (no `\\n`).
  - Exactly 1 option must state a fact that matches the passage.
  - The other 4 must contain incorrect, altered, or unrelated information.
  - Avoid simple negation (~않다, ~없다) to reveal the answer; use detail mismatches instead.
- **Correct Answer**: An integer (1–5) indicating the correct option.
- **Explanation**: Korean, must state why the correct option matches the passage and why the others are wrong.

### OUTPUT (STRICT)
Return exactly one JSON object with these keys:
- question (string, Korean, no HTML/Markdown)
- passage (string, English, ASCII notice layout as above)
- options (array of 5 Korean strings)
- correct_answer (integer 1–5)
- explanation (string, Korean)

### HARD CONSTRAINTS CHECKLIST
- [ ] No code fences or backticks in output.
- [ ] No HTML or Markdown tags anywhere.
- [ ] Passage has top divider, ALL-CAPS title, identical divider, labeled sections, and bottom divider.
- [ ] Passage word count 120–140.
- [ ] Options = exactly 5 Korean sentences.
- [ ] correct_answer = integer 1–5.
- [ ] Only required keys in JSON; no extras.""",

  "spec": {
    "type": "standard",
    "components": ["question", "passage", "options", "correct_answer", "explanation"],
    "processing_hints": { "passage": "structured_notice" },
    "special_features": ["notice_match"]
  }
},       
"RC29": {
  "title": "읽기 29번 - 어법 판단",
  "content": """Create a CSAT Reading Item 29 (Grammar Judgment) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: 문맥 속에서 문법 규칙의 올바른 적용 여부를 판단하는 능력 측정
- **Processing Pattern**: 문장 구조 분석 → 밑줄 친 부분의 문법적 역할 파악 → 관련 문법 규칙 적용 → 오류 식별
- **Evaluation Focus**: 동사의 수일치, 시제, 태, 준동사(부정사, 동명사, 분사), 관계사, 접속사 등 핵심 문법 사항의 정확한 판단 능력

### Discourse Structure
- **Pattern**: 설명문 또는 논설문 형식의 글
- **Flow**: 일관된 주제를 가진 글 안에서 문법적 판단이 필요한 5개의 요소를 배치
- **Key Positioning**: 5개의 밑줄 친 문법 요소가 텍스트 전반에 걸쳐 분산 배치되어, 각기 다른 문법 포인트를 평가함

### Language Specifications
- **Passage Length**: 반드시 110~130 words (절대 초과·미달 금지)
- **Sentence Complexity**: Complex, intentionally including a variety of grammatical structures to be tested. (Avg. 2.3~2.5 clauses per sentence)
- **Vocabulary Level**: Academic and topic-specific vocabulary to provide a challenging context.
- **Reading Level**: High academic complexity, focused on structural analysis over content comprehension.

### Vocabulary Profile
"vocabulary_difficulty": "CSAT+O3000",
"low_frequency_words": ["예: sponsor", "예: exhibit", "예: festival"]  // 예시 단어, 반드시 사용해야 하는 것은 아님

### Question Format Requirements
- **Stem**: "다음 글의 밑줄 친 부분 중, 어법상 <u>틀린</u> 것은?"
- **Options**: 5개 선택지 (①②③④⑤), 지문 내 번호가 선택지를 대신함
- **Correct Answer**: 문법적으로 오류가 있는 유일한 표현
- **Distractors**: 문법적으로 올바른 표현들 (4개)

### Content Generation Guidelines
- 주제: 과학·기술·사회·인문 등 학문적/이론적 주제
- 지문에는 반드시 5개의 distinct grammar points 포함:
  1. 관계대명사/관계부사
  2. 동사 시제 또는 수일치
  3. 조동사 + 동사 원형/부정사
  4. 수동태
  5. 분사 또는 분사구문
- 각 밑줄 포인트는 반드시 **단일 단어** 또는 **짧은 어휘 단위(최대 2~3어, 예: to be, have been)**만 사용해야 하며,
  절(clause)이나 완전한 구(phrase) 전체가 밑줄 처리되어서는 안 됨.
- 문법 포인트는 ①~⑤ 번호와 `<u>...</u>` 태그로 표시
Each grammar target MUST be written as "①<u>word_or_phrase</u>", 
"②<u>word_or_phrase</u>", … "⑤<u>word_or_phrase</u>".
Do NOT put the number outside <u>. Do NOT duplicate numbers.

### Length Control Method
- 지문은 6~8문장으로 구성
- 각 문장은 14~18 words를 목표로 작성
- Word count를 110~130 words 범위 내에서 반드시 마무리
- 필요 시 종속절·부사절을 간결하게 조정하여 길이 유지

### Formatting Instructions for Passage
- Grammar points embedded directly in the passage:
  ① <u>word_or_phrase</u>, ② <u>word_or_phrase</u>, ③ <u>word_or_phrase</u>, ④ <u>word_or_phrase</u>, ⑤ <u>word_or_phrase</u>
- `<u>` 태그 외의 다른 강조 기호는 사용 금지
- `<u>` 태그 안에는 **문법적으로 문제되는 최소 단위**만 들어가야 하며,
  반드시 핵심 문법 형태소/단어 수준으로 표시할 것.

**Required JSON Output Format:**
{
  "question": "다음 글의 밑줄 친 부분 중, 어법상 <u>틀린</u> 것은?",
  "passage": "[110~130 words academic text with ① <u>...</u> through ⑤ <u>...</u> embedded]",
  "options": ["①", "②", "③", "④", "⑤"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of the grammar error]"
}"""
,
  "spec": {
    "type": "standard",
    "components": ["question", "passage", "options"],
    "processing_hints": {
      "passage": "grammar_numbers_with_underlines"
    }
  }
},
"RC29_EDIT_ONE_FROM_CLEAN": {
  "title": "읽기 29번 - 어법 판단 (맞춤)",
  "content": "Create a CSAT Reading Item 29 (Grammar Judgment) from the given passage.\n\n## ITEM CHARACTERISTICS & RULES\n- Use the passage AS-IS for content: do NOT paraphrase, reorder, summarize, or expand sentences.\n- The passage is already clean (no numbers/underlines remain).\n- Insert exactly five labeled grammar targets into the passage.\n- Each grammar target MUST follow this exact format:\n  - ①<u>word_or_phrase</u>\n  - ②<u>word_or_phrase</u>\n  - ③<u>word_or_phrase</u>\n  - ④<u>word_or_phrase</u>\n  - ⑤<u>word_or_phrase</u>\n- **The circled number must always be OUTSIDE the <u>…</u> tags.**\n- Never duplicate or nest labels. Do NOT write \"⑤<u>①<u>…</u></u>\".\n- Each <u>…</u> must contain only one word or a very short unit (max 2–3 words). No full clauses.\n\n## GRAMMAR ERROR REQUIREMENT\n- Make EXACTLY ONE of the five underlined spans ungrammatical.\n- The error must be a clear violation of an English grammar rule (subject–verb agreement, tense, voice, pronoun, article, preposition, infinitive/gerund/participle, comparative/superlative, parallelism).\n- The other four spans must remain fully grammatical and natural.\n- Stylistic awkwardness, redundancy, or meaning shifts are NOT allowed as errors.\n\n## OUTPUT FORMAT\nReturn JSON only (no extra text):\n{\n  \"question\": \"다음 글의 밑줄 친 부분 중, 어법상 <u>틀린</u> 것은?\",\n  \"passage\": \"[original passage with ①<u>...</u> through ⑤<u>...</u>; exactly one span minimally altered to be ungrammatical]\",\n  \"options\": [\"①\", \"②\", \"③\", \"④\", \"⑤\"],\n  \"correct_answer\": [1-5],\n  \"explanation\": \"[한국어로 규칙명, 잘못된 형태 vs 올바른 형태를 명확히 제시하고, 왜 틀렸는지 설명]\"\n}\n",
  "spec": {
    "type": "standard",
    "components": ["question", "passage", "options"],
    "processing_hints": {
      "passage": "grammar_numbers_with_underlines"
    }
  }
},
    "RC30": {
    "title": "읽기 30번 - 어휘의 적절성 파악",
    "content": """Create a CSAT Reading Item 30 (Vocabulary Judgment) following these specifications:

    ## ITEM CHARACTERISTICS & METHODOLOGY

    ### Assessment Objective
    - **Core Skill**: 글의 전체적인 논리 흐름 속에서 어휘의 문맥적 적절성을 판단하는 능력 측정
    - **Processing Pattern**: 글의 주제와 문장 간 논리 관계 파악 → 밑줄 친 어휘의 의미와 문맥의 요구사항 비교 → 의미적으로 상충되는 어휘 식별
    - **Evaluation Focus**: 반의어 관계, 인과관계, 논리적 모순 등을 통해 문맥상 부적절한 어휘를 정확히 찾아내는 능력

    ### Discourse Structure
    - **Pattern**: 설명문 또는 논설문 형식의 글
    - **Flow**: 일관된 주제와 논리적 흐름을 가진 글 안에서, 문맥상 판단이 필요한 5개의 어휘를 배치
    - **Key Positioning**: 5개의 밑줄 친 어휘가 텍스트 전반에 걸쳐 분산 배치되며, 주로 논리적 전환점이나 핵심 개념어에 위치함

    ### Language Specifications
    - **Passage Length**: 130-150 words
    - **Sentence Complexity**: Complex, with dense logical relationships (e.g., cause-effect, contrast) to support inference. (Avg. 2.1-2.3 clauses per sentence)
    - **Vocabulary Level**: Advanced academic and abstract vocabulary.
    - **Reading Level**: High academic complexity, focused on logical inference.

    ### Vocabulary Profile
    "vocabulary_difficulty": "CSAT+O3000",
    "low_frequency_words": ["예: sponsor", "예: exhibit", "예: festival"]  // 예시 단어, 반드시 사용해야 하는 것은 아님


    ### Question Form at Requirements
    - **Stem**: "다음 글의 밑줄 친 부분 중, 문맥상 낱말의 쓰임이 적절하지 <u>않은</u> 것은? [3점]"
    - **Options**: 5개 선택지 (①②③④⑤), 지문 내 번호가 선택지를 대신함
    - **Correct Answer**: 글의 전체적인 논리 흐름과 상충되는 유일한 어휘
    - **Distractors**: 문맥상 의미가 적절하며 글의 논리를 지지하는 어휘들 (4개)

    ### Content Generation Guidelines
    - Any academic or explanatory topic with a clear logical flow and conceptual depth
    - Any phenomenon requiring analysis of causes, effects, and mechanisms where logical consistency is key
    - Any subject involving contrasting ideas or logical progressions
    - The error is often an antonym of the correct word (e.g., 'increase' instead of 'decrease', 'stronger' instead of 'weaker')
    - 각 번호에 해당하는 어휘는 반드시 HTML 밑줄 태그(`<u>...</u>`)를 사용해 표기하십시오.
    - 예: ①<u>increase</u>, ②<u>reduce</u>, ...
    - 지문 내 정확히 5개의 어휘가 ①~⑤ 번호와 함께 밑줄로 처리되어야 합니다.
    - 번호와 밑줄은 항상 붙여서 표기하며, 띄어쓰기 없이 사용하십시오.

    **Required JSON Output Format:**
    {
    "question": "다음 글의 밑줄 친 부분 중, 문맥상 낱말의 쓰임이 적절하지 <u>않은</u> 것은? [3점]",
    "passage": "[Academic text with ①<u>word1</u> ②<u>word2</u> ③<u>word3</u> ④<u>word4</u> ⑤<u>word5</u> placed throughout the text]",
    "options": ["①", "②", "③", "④", "⑤"],
    "correct_answer": [1-5],
    "explanation": "[Korean explanation of the vocabulary error]"
    }""",
            "spec": {
                "type": "standard",
                "components": ["question", "passage", "options"],
                "processing_hints": {
                    "passage": "vocabulary_underline"
                }
            }
        },

"RC31": {
  "title": "읽기 31번 - 빈칸 추론 (단어/구)",
  "content": """Create a CSAT Reading Item 31 (Blank Inference - Word/Phrase) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: 문맥을 통한 핵심 어휘/구 추론 능력 측정
- **Processing Pattern**: 문맥 분석 → 논리적 관계(인과, 대조 등) 파악 → 빈칸의 기능 확인 → 적절한 어휘/구 추론
- **Evaluation Focus**: 글의 논리적 흐름을 완성하는 핵심 개념어의 정확한 추론 능력

### Discourse Structure
- **Pattern**: 주제 제시 → 배경 설명 → 핵심 논점 → **빈칸 위치** → 구체적 사례/상술 → 결론
- **Flow**: 개념 도입 → 맥락 설정 → 중심 아이디어 → **추론 지점** → 예시/근거 → 종합
- **Key Positioning**: 빈칸은 텍스트의 핵심 개념을 요약하거나 논리적 연결을 담당하는 위치에 배치

### Language Specifications
- **Passage Length**: 130–150 words
- **Sentence Complexity**: Complex, with dense logical relationships (e.g., cause-effect, contrast) to support inference. (Avg. 2.1–2.3 clauses per sentence)
- **Vocabulary Level**: Advanced academic and abstract vocabulary.
- **Reading Level**: High academic complexity, focused on logical inference.


### Vocabulary Profile
"vocabulary_difficulty": "CSAT+O3000",
"low_frequency_words": ["예: statistic", "예: percentage"]  // 예시 단어, 반드시 사용해야 하는 것은 아님

### Question Format Requirements
- **Stem**: "다음 글의 빈칸에 들어갈 말로 가장 적절한 것은?"
- **Options**: 5개 선택지, 모두 빈칸에 들어갈 수 있는 영어 단어 또는 짧은 구
- **Correct Answer**: 문맥의 논리적 흐름에 완벽히 부합하는 핵심 어휘/구
- **Distractors**: 부분적으로 관련되거나, 반의어이거나, 논리적으로 부적절한 어휘/구들

### Content Generation Guidelines
- Any argumentative or explanatory topic requiring logical reasoning
- Any concept with cause-effect relationships or logical progressions
- Any subject requiring inference and logical connection
- **The blank must be indicated ONLY by `_____` (five underscores).**
- **Do NOT use any HTML underline tags `<u>...</u>` anywhere in the passage.**
- Ensure exactly one blank in the passage.

**Required JSON Output Format:**
{
  "question": "다음 글의 빈칸에 들어갈 말로 가장 적절한 것은?",
  "passage": "[Academic text with _____ blank in English]",
  "options": ["word/phrase 1", "word/phrase 2", "word/phrase 3", "word/phrase 4", "word/phrase 5"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of the logical completion]"
}""",

  "spec": {
    "type": "standard",
    "components": ["question", "passage", "options", "correct_answer", "explanation"],
    "processing_hints": {
      "passage": "blank_filling"
    }
  }
},
    "RC32": {
        "title": "읽기 32번 - 빈칸 추론 (구/절)",
        "content": """
Create a CSAT Reading Item 32 (Blank Inference - Phrase/Clause) following these specifications.

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Inference of a key phrase or clause within a complex context.
- **Cognitive Process**: Complex context analysis → multi-layered logic comprehension → identifying the blank's core function → inferring high-level content.
- **Difficulty Target**: 상 수준 (예상 정답률 15–20%, 변별도 0.3 이상)

### Abstractness & Complexity Controls
- **Abstractness Level (1–9)**: MUST be 8 (high abstractness, theoretical reasoning required)
- **Syntactic Complexity Targets**:
  - Each sentence MUST average around 19 words.
  - Each sentence MUST contain about 2.2 clauses.
  - Subordination ratio MUST be ~0.4.
  - If the passage is simpler, regenerate.
- **Vocabulary Profile**: MUST use CSAT+AWL vocabulary.

### Text Type & Structure
- **Format**: Academic or theoretical discourse
- **Structure Pattern**: Introduction of a concept → theoretical background → a point of logical consequence or conclusion that requires inference → specific explanation → example presentation → conclusion.
- **TYPE_SPECIFIC_PLACEMENT**: The blank should be positioned at a crucial point of logical transition, requiring a high-level inference.

### Type-Specific Policy
- The passage MUST have a clear, logical flow.
- The correct answer MUST be a phrase or clause that perfectly completes the argument.

### Language Specifications
- Passage Length: 130–150 words (MUST be enforced)
- Sentence Style: Academic cohesion with complex logical development.
- Use `_____` for the blank.

### Question Format Requirements
- Stem: "다음 글의 빈칸에 들어갈 말로 가장 적절한 것은?"
- Options: 5 choices, ALL verb phrases (verb + object/complement)
  - At least one MUST contain passive voice.
  - At least one MUST contain present perfect.
  - At least one MUST contain a to-infinitive construction.
- **Options (Korean, 5지)**:
  - **DISTRACTOR_POLICY_KR**: 겉으로 관련되어 보이나 논리적으로 부정확하거나 지엽적인 내용을 포함한 오답을 구성.
  - **TYPE_SPECIFIC_OPTIONS_KR**: 모든 선택지는 동사구(verb phrase) 형태로 만들어져야 함 (예: 동사 + 목적어, 동사 + 목적어 + 목적보어 등).
- Correct Answer: The option that logically and coherently completes the argument.
- Distractors: Seem relevant but logically inaccurate or too narrow.

**Required JSON Output Format:**
{
  "question": "다음 글의 빈칸에 들어갈 말로 가장 적절한 것은?",
  "passage": "[130–150 word academic passage in English with a single blank.]",
  "options": [
    "verb phrase option",
    "verb phrase option",
    "verb phrase option",
    "verb phrase option",
    "verb phrase option"
  ],
  "answer": 2,
  "explanation": "[한국어 해설: 정답 근거 및 오답 배제 이유]",
  "metadata": {
    "item_number": 32,
    "item_type": "Reading",
    "skill_focus": "Inference (Phrase/Clause)",
    "difficulty": "High",
    "abstractness_level": 8,
    "syntactic_complexity": {
      "avg_words_per_sentence": 19.0,
      "avg_clauses_per_sentence": 2.2,
      "subordination_ratio": 0.4
    },
    "vocabulary_difficulty": "CSAT+AWL",
    "passage_word_count": 140,
    "TYPE_SPECIFIC_METADATA": "focus: logical transition",
    "low_frequency_words": []
  }
}
""",
        "spec": {
            "type": "standard",
            "components": ["question", "passage", "options"],
            "processing_hints": {
                "passage": "blank_filling"
            }
        }
    },

"RC33": {
  "title": "읽기 33번 - 빈칸 추론 (구/절, 고난도)",
  "content": """Create a CSAT Reading Item 33 (Blank Inference - Phrase/Clause, High Difficulty) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: Inference of logical paradox or hidden truth from a complex narrative context.
- **Cognitive Process**: Analyzing cause-and-effect relationships and sequences of events; identifying a point of logical divergence; deducing the narrative's underlying principle.
- **Difficulty Target**: 중 수준 (예상 정답률 35.7%, 변별도 0.3)

### Abstractness & Complexity Controls
- **Abstractness Level (1–9)**: 9
- **Syntactic Complexity Targets (optional)**:
  - avg_words_per_sentence: 32.25
  - avg_clauses_per_sentence: 4.25
  - subordination_ratio: 0.5
- **Vocabulary Profile (optional)**: Very high abstractness vocabulary (highly conceptual, theoretical terms)

### Text Type & Structure
- **Format**: Academic or theoretical narrative
- **Structure Pattern**: Introduction of a concept → Development through clear, declarative sentences → A point of logical consequence or conclusion that requires inference
- **TYPE_SPECIFIC_PLACEMENT**: The blank should be positioned at a crucial point where the core argument culminates or a logical consequence is drawn from the preceding sentences.

### Type-Specific Policy
- Passage should avoid excessive nominalization, favoring clear subject-verb structures to convey logical relationships.
- The passage should explain abstract concepts through clear, sequential statements and avoid dense noun phrases.
- The correct answer must follow a clear logical cause-and-effect or narrative progression.

### Language Specifications
- **Passage Length**: 130–150 words
- **Sentence Style**: Academic cohesion, with clear prose; complexity is achieved through nuanced phrasing and logical links rather than nominalizations.
- **TYPE_SPECIFIC_MARKUP**: Use `_____` (five underscores) to indicate the blank.

### Question Format Requirements
- **Stem**: "다음 글의 빈칸에 들어갈 말로 가장 적절한 것은? [3점]"
- **Options**: 5개 선택지, 모두 고난도 논리적 구/절
- **Correct Answer**: The option that logically and coherently concludes the clear narrative progression.
- **Distractors Policy (KR)**: 정답과 반대되는 논리, 부분적으로 타당하나 전체 논리를 벗어난 내용, 지엽적 세부 정보에만 초점을 맞춘 내용을 포함하여 매력적인 오답을 구성.
 

    **Required JSON Output Format:**
    {
    "question": "다음 글의 빈칸에 들어갈 말로 가장 적절한 것은? [3점]",
    "passage": "[130–150 word academic passage in English with a single blank, composed of clear, narrative sentences with minimal nominalization.]",
    "options": ["sophisticated phrase/clause 1", "sophisticated phrase/clause 2", "sophisticated phrase/clause 3", "sophisticated phrase/clause 4", "sophisticated phrase/clause 5"],
    "correct_answer": [1-5],
    "explanation": "[한국어 해설: 정답 근거 및 오답 배제 이유]",
    "vocabulary_difficulty": "Very high abstractness vocabulary (highly conceptual, theoretical terms)",
    "passage_word_count": 140,
    "TYPE_SPECIFIC_METADATA": "focus: reduced nominalization, clear subject-verb structure",
    "low_frequency_words": []
    }""",
            "spec": {
                "type": "standard",
                "components": ["question", "passage", "options"],
                "processing_hints": {
                    "passage": "blank_filling"
                }
            }
        },  
"RC34": {
  "title": "읽기 34번 - 빈칸 추론 (주제문/술부)",
  "content": "Create a CSAT Reading Item 34 (Blank Inference - Topic Sentence Predicate) following these specifications:\n\n## ABSOLUTE RULES (DO NOT VIOLATE)\n1. The blank (_____) MUST appear **only in the very first sentence** of the passage.\n   - The first sentence MUST begin with a clear subject (e.g., \"Global cooperation,\" \"Technological innovations,\" \"Traditional practices\"), followed by `_____`.\n   - The blank must cover the **entire predicate** of the first sentence.\n   - DO NOT place the blank in the middle or at the end of the passage.\n   - If the blank is not in the first-sentence predicate, the output is INVALID.\n\n2. Passage length MUST be between **130 and 150 words**.\n   - If it is shorter or longer, the output is INVALID.\n\n3. Sentence complexity MUST match the following targets:\n   - Average ≈ 21.9 words per sentence\n   - Average ≈ 2.75 clauses per sentence\n   - Subordination ratio ≈ 0.5 or higher\n   - You MUST include complex sentences with relative clauses, subordinate clauses, or participial constructions.\n\n4. Vocabulary MUST include several words from the **Academic Word List (AWL)**, such as:\n   - integrate, facilitate, exemplify, commodify, resonate, sustain, embody, demonstrate, transformation, mechanism.\n   - At least **3 AWL words** must appear.\n   - If AWL words are missing, the output is INVALID.\n\n### Vocabulary Profile\n    \"vocabulary_difficulty\": \"AWL\"\n\n## ITEM CHARACTERISTICS & METHODOLOGY\n- **Assessment Objective**: Infer the correct predicate that generalizes multiple examples into a unifying principle.\n- **Cognitive Process**: 사례 분석 → 공통 원리 추상화 → 일반화된 술부 도출\n- **Difficulty Target**: 최상 수준 (예상 정답률 26.8%, 변별도 0.2–0.3)\n\n## Discourse Structure\n- First sentence: Subject + `_____` (general principle predicate)\n- Body: Example 1 → Example 2 → Example 3 (all supporting the general principle)\n- Final sentence: Reaffirmation of the principle, using AWL vocabulary.\n\n## Question Format Requirements\n- **Stem (Korean)**: \"다음 글의 빈칸에 들어갈 말로 가장 적절한 것은? [3점]\"\n- **Options (Korean, 5지)**:\n  - **DISTRACTOR_POLICY_KR**: 일부 사례에만 적용되거나, 주된 논리와 상반되는 내용을 담는 등 논리적으로 부정확한 오답을 구성.\n  - **TYPE_SPECIFIC_OPTIONS_KR**: 모든 선택지는 빈칸 앞부분에 제시된 주어 + (조동사)에 이어질 수 있는 완전한 술부(predicate)로 이루어져야 함.\n- **Correct Answer**: 글 전체의 귀납적 결론을 가장 정확하게 서술하는 선택지\n- **Explanation (Korean)**:\n  - 정답 근거: 본문 맥락 + 유형별 핵심 근거 명시\n  - 오답 배제: 각 보기별 왜 틀렸는지 1–2문장 설명\n\n## OUTPUT CONTRACT OVERRIDE (STRICT)\n- **This item overrides the BASE output keys.**\n- Use **exactly** the following top-level JSON keys and value types.\n- **Do NOT** use \"stimulus\" or \"question_stem\" keys.\n- The output must be a **single JSON object** with **no extra text**.\n\n{\n  \"question\": \"다음 글의 빈칸에 들어갈 말로 가장 적절한 것은? [3점]\",\n  \"passage\": \"[130–150 word academic passage in English beginning with a sentence that has a blank after the subject.]\",\n  \"options\": [\"...\", \"...\", \"...\", \"...\", \"...\"],\n  \"correct_answer\": 1,\n  \"explanation\": \"[한국어 해설: 정답 근거 및 오답 배제 이유]\",\n  \"vocabulary_difficulty\": \"AWL\",\n  \"low_frequency_words\": []\n}\n\n## SELF-CHECK BEFORE RETURNING\n- JSON parses with a standard parser.\n- Keys **exactly** match the contract above.\n- `correct_answer` is an integer in [1,5].\n- `passage` is 130–150 words; first sentence has **subject + `_____` as predicate**.\n- At least 3 AWL words appear.\n- Options are 5, mutually exclusive, and grammatically fit after the subject.\n- Explanation in Korean justifies the key and rules out distractors.\n",
  "spec": {
    "type": "standard",
    "components": ["question", "passage", "options", "correct_answer", "explanation", "vocabulary_difficulty", "low_frequency_words"],
    "processing_hints": {
      "passage": "blank_filling"
    }
  }
},    
"RC35": {
  "title": "읽기 35번 - 무관한 문장 찾기",
  "content": """Create a CSAT Reading Item 35 (Irrelevant Sentence) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: 글의 통일성을 해치는 문장 식별 능력 측정
- **Processing Pattern**: 주제 파악 → 각 문장의 관련성 평가 → 논리적 이탈 문장 식별
- **Evaluation Focus**: 글의 일관성과 논리적 전개 속에서 미묘하게 어긋나는 문장을 찾아내는 능력

### Discourse Structure
- **Introductory Paragraph**: 반드시 **2~3절 이상으로 연결된 Complex sentence**로 주제 제시 (조건절, 인과절, 대조절 포함).
- **Main Passage (①~⑤)**:
  - ① 주제 관련 구체적 설명 또는 사례  
  - ② 주제 확장/일반화  
  - ③ 또는 ④: **무관 문장** (겉보기에 관련 있어 보이지만 실제 주제에서 벗어남)  
  - 나머지 문장: 주제와 긴밀히 연결  
  - ⑤ 결론 또는 주제 강화  

### Language Specifications
- **Passage Length**: 120–140 words
- **Sentence Complexity**: 평균 2.2절 이상, 주제문은 반드시 복합문
- **Vocabulary Level**: Academic, expository style
- **Reading Style**: Argumentative or expository, high cohesion
- **Vocabulary Profile**:
  "vocabulary_difficulty": "AWL",
  "low_frequency_words": ["예: collaboration", "예: innovation", "예: comprehensive"]  // 예시 단어, 반드시 사용해야 하는 것은 아님

### Question Format Requirements
- **Stem**: "다음 글에서 전체 흐름과 관계 <u>없는</u> 문장은?"
- **Options**: ①~⑤
- **Correct Answer**: 반드시 ①~⑤ 중 정확히 하나
- **Distractors**: 나머지 4개 문장은 주제를 강화

### Content Generation Guidelines
- 무관 문장은 **①~⑤ 중 하나**에만 배치해야 함.  
- 무관 문장은 **겉보기에 주제와 관련 있어 보이지만**, 실제로는 논리적 초점을 흐리거나 다른 주제로 전환함.  
  - ❌ 주제와 완전히 무관한 분야(예: 독서 지문에 운동 이야기) → 피하기  
  - ✅ 주제와 부분적으로 연관 있으나, 중심 논리와 어긋나는 내용 (예: 독서의 가치 지문에 출판사의 마케팅 전략 언급)  
- **각 문장은 반드시 같은 단락 안에서 공백으로만 구분되며, 절대 줄바꿈(\\n) 없이 연속해서 이어져야 함.**
- 번호는 **①, ②, ③, ④, ⑤** 순서대로 문장 앞에만 붙인다.

**Required JSON Output Format:**
{
  "question": "다음 글에서 전체 흐름과 관계 <u>없는</u> 문장은?",
  "passage": "[Introductory complex sentence paragraph] ① ... ② ... ③ ... ④ ... ⑤ ...",
  "options": ["①", "②", "③", "④", "⑤"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of why the chosen sentence is irrelevant]",
  "vocabulary_difficulty": "AWL",
  "low_frequency_words": ["예: collaboration", "예: innovation", "예: comprehensive"]
}
""",
  "spec": {
    "type": "standard",
    "components": ["question", "passage", "options", "vocabulary_difficulty", "low_frequency_words"],
    "processing_hints": {
      "passage": "intro_complex_sentence + sentence_numbers_inline"
    }
  }
},
    "RC36": {
        "title": "읽기 36번 - 글의 순서 배열",
        "content": """Create a CSAT Reading Item 36 (Paragraph Ordering) following these specifications:

    ## ITEM CHARACTERISTICS & METHODOLOGY

    ### Assessment Objective
    - **Core Skill**: 논리적 글의 순서 파악 능력 측정
    - **Processing Pattern**: 주어진 문단 분석 → 각 단락의 기능 파악(예시, 부연, 결론 등) → 논리적 연결(대명사, 연결어) 추적 → 최적 배열 도출
    - **Evaluation Focus**: 담화 표지와 내용의 논리적 흐름을 통한 문단 순서의 정확한 배열 능력

    ### Discourse Structure
    - **Pattern**: 주어진 도입 문단(박스) → 순서가 섞인 (A), (B), (C) 단락
    - **Flow**: 고정된 시작(원칙/개념 제시) → 세 개의 단락을 논리적 순서(예: 일반→구체, 원인→결과)로 배열
    - **Key Positioning**: 도입 문단이 전체의 맥락을 설정하고, 나머지 세 단락은 대명사, 지시어, 연결어 등을 통해 논리적 순서를 추론해야 함

    ### Language Specifications
    - **Passage Length**: 130-150 words (total across all paragraphs)
    - **Sentence Complexity**: Moderate to complex, with explicit logical connectors (pronouns, discourse markers) to signal paragraph order. (Avg. 2.0-2.2 clauses per sentence)
    - **Vocabulary Level**: Academic and transitional vocabulary.
    - **Reading Level**: Academic expository or argumentative style.   

    ### Vocabulary Profile
    "vocabulary_difficulty": "AWL"

    ### Question Format Requirements
    - **Stem**: "주어진 글 다음에 이어질 글의 순서로 가장 적절한 것은?"
    - **Options**: 5개 선택지, 모두 (A)-(C)-(B) 형태의 순서 조합
    - **Correct Answer**: 논리적으로 가장 자연스러운 단락 순서
    - **Distractors**: 부분적으로는 논리적이나 전체적으로 부자연스러운 순서들

    ### Content Generation Guidelines
    - Any academic or explanatory topic with a clear logical progression
    - Any subject requiring sequential development or logical order
    - Any concept with problem-solution or cause-effect relationships
    - Each paragraph must be clearly labeled as (A), (B), and (C) and contain distinct content.

    **Required JSON Output Format:**
    {
    "question": "주어진 글 다음에 이어질 글의 순서로 가장 적절한 것은?",
    "intro_paragraph": "[Introductory paragraph in a box]",
    "passage_parts": {
        "(A)": "[Paragraph A content]",
        "(B)": "[Paragraph B content]",
        "(C)": "[Paragraph C content]"
    },
    "options": ["(A)-(C)-(B)", "(B)-(A)-(C)", "(B)-(C)-(A)", "(C)-(A)-(B)", "(C)-(B)-(A)"],
    "correct_answer": [1-5],
    "explanation": "[Korean explanation of the logical order]"
    }""",
        "spec": {
            "type": "ordering",
            "components": ["question", "intro_paragraph", "passage_parts", "options"],
            "processing_hints": {
                "passage_parts": "paragraph_labels"
            }
        }
    },
    "RC37": {
  "title": "읽기 37번 - 글의 순서 배열",
  "content": """Create a CSAT Reading Item 37 (Paragraph Ordering) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: 논리적 글의 순서 파악 능력 측정
- **Processing Pattern**: 주어진 문단 분석 → 각 단락의 기능 파악(예시, 부연, 결론 등) → 논리적 연결(대명사, 연결어) 추적 → 최적 배열 도출
- **Evaluation Focus**: 담화 표지와 내용의 논리적 흐름을 통한 문단 순서의 정확한 배열 능력

### Discourse Structure
- **Pattern**: 주어진 도입 문단(박스) → 순서가 섞인 (A), (B), (C) 단락
- **Flow**: 고정된 시작(현상 제시) → 세 개의 단락을 논리적 순서(예: 원인→실험→결과)로 배열
- **Key Positioning**: 도입 문단이 전체의 맥락을 설정하고, 나머지 세 단락은 대명사, 지시어, 연결어 등을 통해 논리적 순서를 추론해야 함

### Language Specifications
- **Passage Length**: 130-150 words (total across all paragraphs)
- **Sentence Complexity**: Moderate to complex, with explicit logical connectors (pronouns, discourse markers) to signal paragraph order. (Avg. 2.0-2.2 clauses per sentence)
- **Vocabulary Level**: Academic and transitional vocabulary.
- **Reading Level**: Academic expository or argumentative style.

### Vocabulary Profile
"vocabulary_difficulty": "AWL"


### Question Format Requirements
- **Stem**: "주어진 글 다음에 이어질 글의 순서로 가장 적절한 것은? [3점]"
- **Options**: 5개 선택지, 모두 (A)-(C)-(B) 형태의 순서 조합
- **Correct Answer**: 논리적으로 가장 자연스러운 단락 순서
- **Distractors**: 부분적으로는 논리적이나 전체적으로 부자연스러운 순서들

### Content Generation Guidelines
- Any scientific or experimental topic with a clear logical progression
- Any subject requiring sequential development (e.g., hypothesis, method, result)
- Any concept with cause-effect relationships demonstrated through research
- Each paragraph must be clearly labeled as (A), (B), and (C) and contain distinct content.

**Required JSON Output Format:**
{
  "question": "주어진 글 다음에 이어질 글의 순서로 가장 적절한 것은? [3점]",
  "intro_paragraph": "[Introductory paragraph in a box]",
  "passage_parts": {
    "(A)": "[Paragraph A content]",
    "(B)": "[Paragraph B content]",
    "(C)": "[Paragraph C content]"
  },
  "options": ["(A)-(C)-(B)", "(B)-(A)-(C)", "(B)-(C)-(A)", "(C)-(A)-(B)", "(C)-(B)-(A)"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of the logical order]"
}""",
  "spec": {
    "type": "ordering",
    "components": ["question", "intro_paragraph", "passage_parts", "options"],
    "processing_hints": {
      "passage_parts": "paragraph_labels"
    }
  }
},
"RC38": {
    "title": "읽기 38번 - 문장 위치 추론",
    "content": """Create a CSAT Reading Item 38 (Sentence Insertion) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: 주어진 문장의 적절한 삽입 위치 파악 능력 측정
- **Processing Pattern**: 주어진 문장 분석 → 글의 논리적 흐름 파악 → 각 삽입 위치별 적합성 검토 → 최적 위치 선택
- **Evaluation Focus**: 담화 표지와 내용의 논리적 연결을 통한 문장 삽입 위치의 정확한 파악 능력

### Discourse Structure
- **Pattern**: 주어진 문장(박스) → 5개의 삽입 위치가 표시된 본문
- **Flow**: 독립적 문장 → 삽입 위치 ① → 문단1 → 삽입 위치 ② → 문단2 → 삽입 위치 ③ → 문단3 → 삽입 위치 ④ → 문단4 → 삽입 위치 ⑤
- **Key Positioning**: 주어진 문장이 글의 논리적 흐름에 가장 자연스럽게 연결되는 위치를 찾아야 함

### Language Specifications
- **Passage Length**: 120-140 words
- **Sentence Complexity**: Moderate to complex, with strong logical cohesion that creates a single correct insertion point. (Avg. 2.0+ clauses per sentence)
- **Vocabulary Level**: Academic vocabulary with an emphasis on discourse markers and cohesive devices.
- **Reading Level**: Academic expository or argumentative style.

### Vocabulary Profile
"vocabulary_difficulty": "AWL"

### Question Format Requirements
- **Stem**: "글의 흐름으로 보아, 주어진 문장이 들어가기에 가장 적절한 곳은?"
- **Options**: 5개 선택지 (①②③④⑤), 각각 본문의 삽입 위치
- **Correct Answer**: 논리적으로 가장 자연스러운 삽입 위치
- **Distractors**: 부분적으로는 연결되나 전체적으로 부자연스러운 위치들

### Content Generation Guidelines
- Any topic with clear logical flow and development
- Any subject requiring sequential reasoning or cause-effect relationships
- Any concept with identifiable transition points
- The passage must include five insertion points marked exactly as **( ① )**, **( ② )**, **( ③ )**, **( ④ )**, **( ⑤ )**.
- The given sentence must fit naturally into only one of these points.
- Do not use alternative markers like (1) or [1].

**Required JSON Output Format:**
{
  "question": "글의 흐름으로 보아, 주어진 문장이 들어가기에 가장 적절한 곳은?",
  "given_sentence": "[Independent sentence to be inserted]",
  "passage": "[Text with ①②③④⑤ insertion points in English]",
  "options": ["①", "②", "③", "④", "⑤"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of the logical insertion point]"
}""",
    "spec": {
        "type": "insertion",
        "components": ["question", "given_sentence", "passage", "options"],
        "processing_hints": {
            "passage": "insertion_points",
            "given_sentence": "highlight"
        }
    }
},

"RC39": {
    "title": "읽기 39번 - 문장 위치 추론",
    "content": """Create a CSAT Reading Item 39 (Sentence Insertion) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: 주어진 문장의 적절한 삽입 위치 파악 능력 측정
- **Processing Pattern**: 주어진 문장 분석 → 글의 논리적 흐름 파악 → 각 삽입 위치별 적합성 검토 → 최적 위치 선택
- **Evaluation Focus**: 담화 표지와 내용의 논리적 연결을 통한 문장 삽입 위치의 정확한 파악 능력

### Discourse Structure
- **Pattern**: 주어진 문장(박스) → 5개의 삽입 위치가 표시된 본문
- **Flow**: 독립적 문장 → 삽입 위치 ① → 문단1 → 삽입 위치 ② → 문단2 → 삽입 위치 ③ → 문단3 → 삽입 위치 ④ → 문단4 → 삽입 위치 ⑤
- **Key Positioning**: 주어진 문장이 글의 논리적 흐름에 가장 자연스럽게 연결되는 위치를 찾아야 함

### Language Specifications
- **Passage Length**: 120-140 words
- **Sentence Complexity**: Moderate to complex, with strong logical cohesion that creates a single correct insertion point. (Avg. 2.0+ clauses per sentence)
- **Vocabulary Level**: Academic vocabulary with an emphasis on discourse markers and cohesive devices.
- **Reading Level**: Academic expository or argumentative style.

### Vocabulary Profile
"vocabulary_difficulty": "AWL"

### Question Format Requirements
- **Stem**: "글의 흐름으로 보아, 주어진 문장이 들어가기에 가장 적절한 곳은? [3점]"
- **Options**: 5개 선택지 (①②③④⑤), 각각 본문의 삽입 위치
- **Correct Answer**: 논리적으로 가장 자연스러운 삽입 위치
- **Distractors**: 부분적으로는 연결되나 전체적으로 부자연스러운 위치들

### Content Generation Guidelines
- Any complex topic with sophisticated logical flow and development
- Any subject requiring advanced sequential reasoning or abstract relationships
- Any concept with subtle transition points and complex argumentation
- The passage must include five insertion points marked exactly as **( ① )**, **( ② )**, **( ③ )**, **( ④ )**, **( ⑤ )** (with parentheses and spacing).
- Do not use any alternative markers such as (1), [1], {1}, or plain ① without parentheses.
- The given sentence must fit naturally into only one of these points.
- Do not use alternative markers like (1) or [1].

**Required JSON Output Format:**
{
  "question": "글의 흐름으로 보아, 주어진 문장이 들어가기에 가장 적절한 곳은? [3점]",
  "given_sentence": "[Independent sentence to be inserted]",
  "passage": "[Text with ①②③④⑤ insertion points in English]",
  "options": ["①", "②", "③", "④", "⑤"],
  "correct_answer": [1-5],
  "explanation": "[Korean explanation of the logical insertion point]"
}""",
    "spec": {
        "type": "insertion",
        "components": ["question", "given_sentence", "passage", "options"],
        "processing_hints": {
            "passage": "insertion_points",
            "given_sentence": "highlight"
        }
    }
},
"RC40": {
  "title": "읽기 40번 - 요약문 완성",
  "content": """Create a CSAT Reading Item 40 (Summary Completion) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: 글의 핵심 내용을 파악하여 영어 요약문의 두 빈칸을 완성하는 능력 측정
- **Processing Pattern**: 글 전체 내용 파악 → 핵심 개념과 그 관계 추출 → 요약문 구조 분석 → (A), (B) 빈칸에 적절한 영어 표현 추론
- **Evaluation Focus**: 글 전체를 조직하는 두 개념의 **논리적 관계(대비, 인과, 메커니즘–결과, 조건–결과 등)**를 정확히 요약하는 능력

### Discourse Structure
- **Pattern**: 복잡한 개념 설명 → 구체적 사례/메커니즘 → 결과/효과 → 종합적 의미
- **Flow**: 현상 소개 → 세부 설명 → 작동 원리 → 영향/결과 → 전체적 함의
- **Key Positioning**: (A), (B)는 반드시 글 전체의 **두 축**이어야 하며, 단순 속성 나열이나 단선적 인과만으로는 부족함

### Language Specifications
- **Passage Length**:  
  - The passage must consist of **9–11 sentences**.  
  - Each sentence should be **information-dense and 18–22 words long**.  
  - The overall passage length should therefore be approximately **150–170 words**.  
  - Avoid producing fewer than 9 sentences or more than 11 sentences.
- **Sentence Complexity**: 복잡하고 정보 밀도가 높을 것
- **Vocabulary Level**: 학술적이고 추상적인 어휘 포함
- **Reading Level**: 고난도 종합 추론 요구

### Vocabulary Profile
"vocabulary_difficulty": "AWL"

### Question Format Requirements
- **Stem**: "다음 글의 내용을 한 문장으로 요약하고자 한다. 빈칸 (A), (B)에 들어갈 말로 가장 적절한 것은? [3점]"
- **Summary**: 영어 한 문장, (A)와 (B) 두 빈칸 포함

### Summary Template Structure
- One complete English sentence summarizing the passage
- (A), (B)는 <u>    (A)    </u>, <u>    (B)    </u>로 표기
- 두 개념의 **관계나 대비**가 반드시 드러나야 함 (단순 열거 금지)
- (A) and (B) must represent the two core concepts that organize the entire passage.
- The blanks (A) and (B) must be placed in positions where they share the same grammatical category 
  (e.g., both nouns, both verbs, both adjectives).
- **Avoid noun-only templates whenever possible.**
- At least half of all generated items must use **verb-verb** or **adjective-adjective** structures.  

- **STRICT LENGTH & COMPLEXITY REQUIREMENTS**
  - The summary template must always contain **at least three clauses** (one main clause + two subordinate clauses).  
  - The template must include **at least two different subordinating connectors** (e.g., although, because, while, if, what, when, even though, unless).  
  - Templates using only a **relative clause (“which …”) + main clause** are invalid.  
  - Templates using only a **not only–but also** pattern are invalid.  
    - If “not only–but also” is used, it must be embedded within a longer multi-clause sentence that also contains an additional subordinate clause (e.g., conditional, concessive, or noun clause).  
  - Sentence length must be **25–35 words** and span **two or more lines** when written.  
  - Templates must rotate across **relative, conditional, concessive, and noun clauses**, and at least one **non-relative clause** must appear in every item.  

- Example acceptable structures (must vary):
  - **Conditional + Concessive + Result** → “If sustainable living <u>  (A)  </u> waste, although many resist the effort, it ultimately <u>  (B)  </u> responsibility across communities.”  
  - **Noun Clause + Main + Relative** → “What students <u>  (A)  </u> in their early years often <u>  (B)  </u> their success, which later determines opportunities.”  
  - **Mixed (3-Clause)** → “Although recycling <u>  (A)  </u> participation, what governments fail to do often <u>  (B)  </u> the programs’ effectiveness, because enforcement remains inconsistent.”  
  - **Embedded not only–but also + Subordinate** → “Although seasonal observation not only <u>  (A)  </u> understanding but also <u>  (B)  </u> responsibility, it becomes meaningful because ecosystems reveal both resilience and vulnerability.”  

### Option Format
- All options must follow the format **"(A): word - (B): word"**.
- Each option must be a **single English word only** (no multi-word phrases).
- (A) and (B) must share the same grammatical category, consistent with the Summary Template.
- Do NOT generate only nouns. Ensure that at least one item uses verb-verb options and another uses adjective-adjective options.
- Permitted categories: 
  - Verb - Verb (e.g., "reduces / preserves")  
  - Adjective - Adjective (e.g., "flexible / effective")  
  - Verb - Noun or Adjective - Noun (allowed only if the Template requires it)  
  - Noun - Noun (allowed, but should be the minority)  
- Distractors must be partially plausible but ultimately fail to capture the passage’s overall meaning.
- At least one distractor should have (A) correct but (B) incorrect, and another should have (B) correct but (A) incorrect.

**Required JSON Output Format:**
{
  "question": "...",
  "passage": "...",
  "summary_template": "...",
  "options": [
    "(A): ... - (B): ...",
    "(A): ... - (B): ...",
    "(A): ... - (B): ...",
    "(A): ... - (B): ...",
    "(A): ... - (B): ..."
  ],
  "correct_answer": 1,
  "explanation": "..."
}""",
  "spec": {
    "type": "summary_completion",
    "components": ["question", "passage", "summary_template", "options"],
    "processing_hints": {
      "summary_template": "dual_blanks_ab_with_contrast_or_relation",
      "passage_length": "9–11 sentences, 18–22 words each"
    }
  }
},
"RC41_42": {
  "title": "읽기 41-42번 - 장문 독해 (1지문 2문항)",
  "content": """Create a CSAT Reading Item 41-42 (Long Reading Set) following these specifications:

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- **Core Skill**: 단일 장문에서 제목 추론 + 어휘 적절성 판단 능력 동시 측정
- **Processing Pattern**: 장문 전체 흐름 파악 → 제목 추출 + 문맥상 부적절한 어휘 식별 → 이중 평가 수행
- **Evaluation Focus**: 단일 지문에서 거시적(제목) + 미시적(어휘) 평가 동시 수행

### Discourse Structure
- **Pattern**: 복잡한 주제 제시 → 이론적 배경 → 구체적 설명 → (a)~(e) 어휘 위치 → 사례 제시 → 결론
- **Flow**: 개념 도입 → 맥락 설정 → 세부 전개 → 핵심 어휘 판단 지점 → 예시 → 종합
- **Key Positioning**: 제목은 전체 내용을 포괄해야 하고, (a)~(e) 어휘는 문맥상 적절성을 판단할 수 있는 위치에 배치

### Language Specifications
- **Passage Length**: 280-320 words
- **Sentence Complexity**: Moderate to complex, maintaining a sustained argument or explanation across at least three paragraphs. (Avg. 2.1+ clauses per sentence)
- **Vocabulary Level**: Advanced academic vocabulary.
- **Reading Level**: Sustained academic reading requiring both macro (title) and micro (vocabulary) analysis.

### Question Format Requirements
- **Item 41 Stem**: "윗글의 제목으로 가장 적절한 것은?"
- **Item 42 Stem**: "밑줄 친 (a)~(e) 중에서 문맥상 낱말의 쓰임이 적절하지 <u>않은</u> 것은? [3점]"
- **Item 41 Options**: 5개 선택지, 모두 영어 제목 (숫자 라벨 절대 금지)
- **Item 42 Options**: ["(a)", "(b)", "(c)", "(d)", "(e)"]

### Vocabulary Profile
    "vocabulary_difficulty": "AWL"

### Content Generation Guidelines
- Any complex concept requiring both title inference and vocabulary appropriateness judgment
- Any subject with sophisticated theoretical content and logical development
- Any topic suitable for advanced academic analysis with contextual vocabulary challenges
- All vocabulary markers (a) to (e) **must be followed by an underlined word** using HTML underline tags: e.g., `(a) <u>word</u>`

### Vocabulary Placement Strategy (Enhanced)
- Spread the (a)~(e) markers across at least **three distinct paragraphs**.
- Avoid clustering: no more than two markers in the same paragraph.
- Assign each marker to a distinct discourse function:
  - (a) Core concept introduction
  - (b) Mechanism/process description
  - (c) Transition/cause-effect statement
  - (d) Example or evidence
  - (e) Conclusion/generalization
- Use advanced academic vocabulary. Exactly one term must be contextually inappropriate, producing a logical inconsistency.

**Required JSON Output Format:**
{
  "set_instruction": "[41~42] 다음 글을 읽고, 물음에 답하시오.",
  "passage": "[Extended academic text with clearly marked (a) <u>word</u> ... (e) <u>word</u> vocabulary items in English.]",
  "questions": [
    {
      "question_number": 41,
      "question": "윗글의 제목으로 가장 적절한 것은?",
      "options": ["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"],
      "correct_answer": "<1~5 중 하나의 문자열>",
      "explanation": "[Korean explanation of the title]"
    },
    {
      "question_number": 42,
      "question": "밑줄 친 (a)~(e) 중에서 문맥상 낱말의 쓰임이 적절하지 <u>않은</u> 것은? [3점]",
      "options": ["(a)", "(b)", "(c)", "(d)", "(e)"],
      "correct_answer": "<1~5 중 하나의 문자열>",
      "explanation": "[Korean explanation of why the selected vocabulary is inappropriate in context]"
    }
  ]
}""",
  "spec": {
    "type": "set",
    "set_size": 2,
    "start_number": 41,
    "components": ["passage", "questions"],
    "processing_hints": {
      "passage": "vocabulary_marking_with_underline"
    }
  }
},
"RC41_42_EDIT_ONE_FROM_CLEAN": {
  "title": "읽기 41-42번 - 장문 독해 (기존 지문 최소 수정·세트화)",
  "content": """You will receive an existing passage. MINIMALLY EDIT this passage so it conforms to CSAT Reading Item 41–42 (Long Reading Set), then produce the two questions (41: title, 42: vocabulary appropriateness).

ABSOLUTE CONTRACT (MUST DO)
- You MUST insert exactly five markers (a)(b)(c)(d)(e), each immediately followed by ONE underlined English word: (a) <u>word</u> … (e) <u>word</u>.
- You MUST split the final passage into at least **2 paragraphs** (preferred 3–4), separated by exactly one blank line (\\n\\n).
- Exactly ONE of the five underlined words MUST be contextually inappropriate; the other four MUST be appropriate.
- If any of the above is missing, REGENERATE INTERNALLY and return only the corrected JSON.

INPUT GUARD
- Use ONLY the provided passage as content basis.
- Preserve original claims, facts, and line of reasoning.
- Do NOT change topic, add new examples, or reorder ideas.
- Allowed edits (minimal):
  1) Insert paragraph breaks at natural boundaries (topic shift, method→example, example→implication, conclusion).
  2) Insert the five markers with underlines as specified.
  3) Replace at most ONE existing word (or add one) solely to create the single misfit required by Q42.
  4) At most two tiny function-word fixes if needed for grammar.
- Disallowed: deleting sentences, adding new claims/examples, or duplicating content.

PARAGRAPHING RULES (STRICT)
- Final passage: **≥2 paragraphs** (preferred 3–4).
- Paragraph separators: **one blank line** only (\\n\\n).
- Distribute markers across **≥2 paragraphs**; **no paragraph has ≥3 markers** (max 2 per paragraph).

MARKER & UNDERLINE RULES (STRICT)
- Pattern must match EXACTLY: \\([a-e]\\)\\s*<u>[A-Za-z\\-]+</u>
- Lowercase marker letters only: (a)(b)(c)(d)(e).
- Underlines are ONE English word (no spaces/punctuation inside).
- Suggested discourse roles:
  (a) concept introduction, (b) mechanism/process, (c) transition/cause–effect,
  (d) example/evidence, (e) conclusion/generalization.

### Vocabulary Profile
    "vocabulary_difficulty": "AWL"

QUESTION FORMAT
- Q41 (Title):
  - question: "윗글의 제목으로 가장 적절한 것은?"
  - options: 5 English titles (no numeric prefixes in option text)
  - correct_answer: one of "1","2","3","4","5" (string)
- Q42 (Vocabulary):
  - question: "밑줄 친 (a)~(e) 중에서 문맥상 낱말의 쓰임이 적절하지 <u>않은</u> 것은? [3점]"
  - options: exactly ["(a)", "(b)", "(c)", "(d)", "(e)"]
  - correct_answer: "1".."5" (string), pointing to the misfit marker
  - explanation (Korean): explicitly justify WHY the chosen underlined word is a misfit in context (mention sentence/discourse role mismatch)

LENGTH & LANGUAGE
- Passage: English only; keep overall length close to original (±10%).
- Questions & explanations: Korean.

OUTPUT FORMAT (JSON ONLY)
Return ONLY:
{
  "set_instruction": "[41~42] 다음 글을 읽고, 물음에 답하시오.",
  "passage": "[Edited passage with (a) <u>...</u> ... (e) <u>...</u>, split into ≥2 paragraphs with blank lines.]",
  "questions": [
    {
      "question_number": 41,
      "question": "윗글의 제목으로 가장 적절한 것은?",
      "options": ["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"],
      "correct_answer": "1|2|3|4|5",
      "explanation": "[한국어 해설: 제목 선택 근거]"
    },
    {
      "question_number": 42,
      "question": "밑줄 친 (a)~(e) 중에서 문맥상 낱말의 쓰임이 적절하지 <u>않은</u> 것은? [3점]",
      "options": ["(a)", "(b)", "(c)", "(d)", "(e)"],
      "correct_answer": "1|2|3|4|5",
      "explanation": "[한국어 해설: 선택한 밑줄 어휘가 왜 부적절한지, 해당 문장/담화 기능과의 불일치 근거]"
    }
  ]
}

FINAL SELF-CHECK (REJECT INTERNALLY IF ANY FAILS)
- Exactly 5 occurrences of "(a) <u", "(b) <u", "(c) <u", "(d) <u", "(e) <u" in the passage.
- Each underline is ONE word only; no phrases.
- Markers spread across ≥2 paragraphs; no paragraph contains 3 or more markers.
- Exactly ONE underlined word is a misfit; four are appropriate.
- Q41 options=5 English titles; Q42 options fixed; both correct_answer fields are strings in {"1","2","3","4","5"}.
- Output is valid JSON; no extra keys or commentary.

---
Use this passage ONLY:
```passage
<PASSAGE>
```""",
  "spec": {
    "type": "set",
    "set_size": 2,
    "start_number": 41,
    "components": ["passage", "questions"],
    "processing_hints": {
      "passage": "vocabulary_marking_with_underline",
      "paragraphing": "at_least_two_paragraphs"
    }
  }
},
"RC43_45": {
  "title": "읽기 43-45번 - 장문 독해 (지칭 추론 - 복합 유형)",
  "content": """Create a CSAT Reading Item 43–45 (Long Reading Set) in perfect JSON format.

## ITEM CHARACTERISTICS & METHODOLOGY

### Assessment Objective
- Core Skill: Identify paragraph order, referent resolution, and content correctness from a 4-paragraph long reading passage.
- Processing: Understand narrative arc → resolve referents (pronouns & noun phrases) → identify correct order → check specific facts.
- Evaluation: Assess comprehension of narrative structure, referent clarity for characters, and detailed content in one set.
- Special Note for Item 44: Exactly one pronoun among (a)–(e) must refer to a different character (Person B), while the other four pronouns refer to Person A. Person A and Person B MUST be the same gender.

### Character Guidelines
- Use only these names:
  - Female set: Sarah, Chloe, Emma, Mia
  - Male set: Alex, Ben, Jack, Leo
- Choose one gender set only (all-female or all-male).
- Person A and Person B must come from the same chosen set.
- Do not use names outside these sets.

### Story Theme Guidelines
- Randomly select one theme: 'artistic struggle', 'scientific discovery', 'sports rivalry', 'a community project', 'a family secret'.

### Language Specifications
- Passage Length: 400–450 words total (each paragraph 95–115 words).
- Sentence Complexity: Moderate (~2 clauses per sentence).
- Vocabulary Level: CEFR B2 with 2–3 C1 words.

### FORMATTING RULES FOR Q44 UNDERLINES (STRICT)
- Insert exactly five underlined pronouns, labeled (a)~(e) in this format:
  - `(a) <u>she</u>` or `(a) <u>he</u>`
  - The label MUST come **before** the underlined pronoun, never after.
  - Do NOT output `<u>she</u> (a)` or `<u>he</u> (b)` — this is incorrect.
- Placement:
  - (A): include exactly one `(a) <u>pronoun</u>`
  - (B): include exactly one `(b) <u>pronoun</u>`
  - (C): include exactly one `(c) <u>pronoun</u>`
  - (D): include exactly two `(d) <u>pronoun</u>` and `(e) <u>pronoun</u>`
- Allowed forms: strictly lowercase, one-word → `he`, `him`, `she`, `her`.
- Case Variety Rule: At least one objective case (him/her) among the five.
- Absolute Gender Consistency: All five pronouns must be either `he/him` OR `she/her`, never mixed.
### Vocabulary Profile
    "vocabulary_difficulty": "AWL"

### Reference Resolution Design (Q44)
- Person A introduced by name in Paragraph A.
- Person B introduced elsewhere in the passage, same gender set.
- Exactly 4 pronouns → Person A; exactly 1 → Person B.
- The “different” pronoun can be at any of (a)~(e). **Do not always assign it to (e).**
- Randomization Emphasis: Vary which of (a)~(e) is Person B across different generations.
- One-Name Window: In each sentence with (a)~(e), mention only one of {Person A, Person B}.
- Nearest Name Wins: Pronoun must clearly refer to the nearest named person.
- Local Subject Default: Prefer subject pronoun (`he`/`she`), but include at least one objective (`him`/`her`).

### Question Format
- Q43: Paragraph order.
- Q44: Reference resolution.
- Q45: Content accuracy.

### Explanation Output Rules
- Q44 explanation MUST explicitly map each label to its referent in double quotes:
  - Example: `(a) → "Sarah", (b) → "Sarah", (c) → "Sarah", (d) → "Sarah", (e) → "Chloe"`
- Also explain why the different one is not the same.
- Q45 explanation MUST check each option and show why the false option is wrong.

### Distractor Design (Q45)
- One option must be false but plausible (role swap, cause-effect twist, or fact distortion).

### OUTPUT FORMAT
Respond ONLY with:

{
  "item_type": "RC_SET",
  "set_instruction": "[43~45] 다음 글을 읽고, 물음에 답하시오.",
  "passage_parts": {
    "A": "... include (a) <u>pronoun</u> ...",
    "B": "... include (b) <u>pronoun</u> ...",
    "C": "... include (c) <u>pronoun</u> ...",
    "D": "... include (d) <u>pronoun</u> and (e) <u>pronoun</u> ..."
  },
  "questions": [
    {
      "question_number": 43,
      "question": "주어진 글 (A)에 이어질 내용을 순서에 맞게 배열한 것으로 가장 적절한 것은?",
      "options": ["B-D-C", "C-B-D", "C-D-B", "D-B-C", "D-C-B"],
      "correct_answer": 1,
      "explanation": "한국어 설명: 단락 전개 순서가 시간적/인과적 흐름에 따라 B-D-C임을 설명."
    },
    {
      "question_number": 44,
      "question": "밑줄 친 (a)~(e) 중에서 가리키는 대상이 나머지 넷과 다른 것은?",
      "options": ["(a)", "(b)", "(c)", "(d)", "(e)"],
      "correct_answer": "A single integer 1–5 for the label that refers to Person B.",
      "explanation": "Must explicitly map (a)~(e) to character names in double quotes, and state why the chosen one is different."
    },
    {
      "question_number": 45,
      "question": "윗글에 관한 내용으로 적절하지 않은 것은?",
      "options": [
        "True statement 1",
        "True statement 2",
        "True statement 3",
        "True statement 4",
        "False/distorted statement"
      ],
      "correct_answer": 5,
      "explanation": "각 보기의 사실 여부를 단락의 단서로 확인하여 5번이 잘못된 진술임을 설명."
    }
  ]
}

### FINAL SELF-CHECK
- Exactly 5 pronouns labeled (a)–(e), label before pronoun.
- At least one objective case.
- 4 map to Person A, 1 to Person B (randomized label).
- Each antecedent clear and local.
- Paragraphs 95–115 words each.
- JSON valid.
"""
},
    # ===== (NEW) Overlay namespace =====
    "_OVERLAYS": {

        # 1) 특정 키 전용(가장 우선): RC25 전용 오버레이
        "RC25": {
            "content": """# RC25 Overlay (Azure-optimized, Minimal Validation)

## Hard Constraints (Critical)
- Single paragraph (115–135 words), English only.
- Exactly five statements inline and ordered: ① ② ③ ④ ⑤.
- Each begins with a numeral + one space (e.g., "① Text ...").
- Never put a numeral at sentence end (e.g., "... 20% ①.").

## Truth Structure (Critical)
- Exactly one statement contradicts chart_data; four are correct.
- 18–25 words per statement; ≤ 2 groups per sentence.

## Variety (Soft Hints)
- Include at least: one percentage, one exact multiple/ratio supported by data, 
  one highest/lowest, and one unchanged/remained.
- Prefer grouped bar or multi-series line with ≥4 labels and ≥2 datasets.

## Output
- Return only JSON: question, passage, options, correct_answer (1–5), explanation (Korean), chart_data.
- No extra fields/markdown. Do not retry unless a critical rule fails.
"""
        },

        # 2) (선택) 동일 키에 _OVERLAY 접미사로도 등록 가능
        "RC25_OVERLAY": {
            "content": """# RC25 Overlay (alt slot)
- If both 'RC25' and 'RC25_OVERLAY' exist, 'RC25' takes precedence.
"""
        },

        # 3) 캐논키 레벨 공유 오버레이(여러 RC 유형 공통으로 사용)
        "OVERLAY_RC_BLANK": {
            "content": """# RC Overlay (MCQ Reading Common)
- Follow item template's schema strictly; return JSON only.
- If numbered claims are required (①–⑤), ensure they start sentences, are inline and ordered.
- If the spec requires exactly one false claim, ensure it; otherwise, all must be consistent.
- Keep CSAT-appropriate vocabulary and avoid under/over-specified sentences.
"""
        },

        # 4) 글로벌 폴백
        "OVERLAY_DEFAULT": {
            "content": """# Overlay Default
- Use JSON only; no markdown or extra commentary.
- When in doubt, prefer minimal validation and avoid unnecessary regeneration.
"""
        },
    },




}
