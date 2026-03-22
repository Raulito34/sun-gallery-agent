from fastapi import APIRouter, HTTPException

from models import AgentRequest, AgentResponse
from agent import generate_response

router = APIRouter()


@router.post("/whatsapp-reply", response_model=AgentResponse)
async def whatsapp_reply(request: AgentRequest):
    try:
        content = await generate_response(
            mode="whatsapp",
            message=request.message,
            recipient=request.recipient,
            sender=request.sender,
            language=request.language,
        )
        return AgentResponse(
            content=content,
            mode="whatsapp",
            metadata={"recipient": request.recipient},
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
