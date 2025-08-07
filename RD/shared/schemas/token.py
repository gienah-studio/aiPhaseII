from typing import Optional
from pydantic import BaseModel

class TokenPayload(BaseModel):
    user_id: Optional[int] = None
    account: Optional[str] = None
    role: Optional[str] = None
    enterprise_id: Optional[int] = None
    exp: int

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer" 