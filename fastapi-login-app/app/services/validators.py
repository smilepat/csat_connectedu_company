# app/services/validators.py
from __future__ import annotations
from pydantic import ValidationError

def validate_with_model(model_cls, data):
    try:
        model_cls.model_validate(data)  # pydantic v2
        return True, None
    except ValidationError as e:
        return False, e.errors()
