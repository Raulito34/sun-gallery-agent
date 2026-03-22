from pydantic import BaseModel
from typing import Optional


class AgentRequest(BaseModel):
    mode: str
    message: str
    recipient: Optional[str] = None
    sender: str = "Joonwha Lee"
    language: str = "en"


class AgentResponse(BaseModel):
    content: str
    mode: str
    metadata: dict = {}
