from fastapi import APIRouter, HTTPException

from models import AgentRequest, AgentResponse
from agent import generate_response

router = APIRouter()


@router.post("/fair-prep", response_model=AgentResponse)
async def fair_prep(request: AgentRequest):
    try:
        content = await generate_response(
            mode="fair",
            message=request.message,
            recipient=request.recipient,
            sender=request.sender,
            language=request.language,
        )
        return AgentResponse(
            content=content,
            mode="fair",
            metadata={"fair_mode": "prep"},
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
