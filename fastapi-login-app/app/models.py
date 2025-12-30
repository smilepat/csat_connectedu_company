from pydantic import BaseModel

class LoginRequest(BaseModel):
    user_id: str
    passwd: str
    institute_seq: int

class LoginResponse(BaseModel):
    userId: int
    role: str
    status: str

