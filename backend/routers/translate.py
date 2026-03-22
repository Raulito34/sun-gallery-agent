from fastapi import APIRouter, HTTPException

from models import AgentRequest, AgentResponse
from agent import generate_response

router = APIRouter()


@router.post("/translate", response_model=AgentResponse)
async def translate(request: AgentRequest):
    try:
        content = await generate_response(
            mode="translate",
            message=request.message,
            recipient=request.recipient,
            sender=request.sender,
            language=request.language,
        )
        return AgentResponse(
            content=content,
            mode="translate",
            metadata={"target_language": request.language},
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
