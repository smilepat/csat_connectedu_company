# schemas/generate.py

from pydantic import BaseModel

class GenerateRequest(BaseModel):
    difficulty: str
    topic: str
    interest: str = "기본"
