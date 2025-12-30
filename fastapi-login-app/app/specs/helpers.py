# app/specs/helpers.py
from __future__ import annotations
from typing import Any, Dict, Protocol
import re

PASSAGE_TOKEN = "<PASSAGE>"

class _HasSystemPrompt(Protocol):
    def system_prompt(self) -> str: ...

def has_system_prompt(spec: Any) -> bool:
    return hasattr(spec, "system_prompt") and callable(getattr(spec, "system_prompt"))

def make_prompt_with_passage(user_template: str, passage: str) -> str:
    """템플릿 내 토큰을 치환하고, 없으면 안전하게 passage 블록을 덧붙입니다."""
    if PASSAGE_TOKEN in user_template:
        return user_template.replace(PASSAGE_TOKEN, passage)
    if passage.strip() and ("```passage" not in user_template):
        return f"{user_template}\n\n---\nUse this passage ONLY:\n```passage\n{passage}\n```"
    return user_template

def default_system_prompt() -> str:
    return (
        "You MUST use ONLY the provided passage to create the question.\n"
        "Never invent or substitute a new passage. If information is missing, say so.\n"
        "Output MUST be valid JSON matching the requested schema. Do not include any extra text.\n"
    )

_BAD_SIGNS = [
    r"\bHere is a passage\b",
    r"\bNew passage\b",
    r"\bConsider the following text\b",
    r"^Passage:\s*$",
]
_BAD_RE = re.compile("|".join(_BAD_SIGNS), re.IGNORECASE | re.MULTILINE)

def looks_like_new_passage(text: str) -> bool:
    """새 지문을 만들어냈을 법한 전형적인 문구/패턴 휴리스틱."""
    return bool(_BAD_RE.search(text))

def default_repair_instruction(passage: str) -> str:
    return (
        "Your previous output appears to ignore the provided passage or invents text.\n"
        "Regenerate STRICTLY using ONLY the passage below. Do NOT create or rewrite a passage.\n"
        "Return VALID JSON only.\n\n"
        "Passage:\n```passage\n" + passage + "\n```"
    )
