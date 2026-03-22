from fastapi import APIRouter, HTTPException

from models import AgentRequest, AgentResponse
from agent import generate_response

router = APIRouter()


@router.post("/email-draft", response_model=AgentResponse)
async def email_draft(request: AgentRequest):
    try:
        content = await generate_response(
            mode="email",
            message=request.message,
            recipient=request.recipient,
            sender=request.sender,
            language=request.language,
        )
        return AgentResponse(
            content=content,
            mode="email",
            metadata={"recipient": request.recipient, "sender": request.sender},
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
