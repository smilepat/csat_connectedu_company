from pydantic import BaseModel

class ErrorResponse(BaseModel):
    code: str
    message: str
    trace_id: str | None = None
