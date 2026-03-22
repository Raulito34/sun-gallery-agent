from fastapi import APIRouter, HTTPException

from models import AgentRequest, AgentResponse
from agent import generate_response

router = APIRouter()


@router.post("/marketing-content", response_model=AgentResponse)
async def marketing_content(request: AgentRequest):
    try:
        content = await generate_response(
            mode="marketing",
            message=request.message,
            recipient=request.recipient,
            sender=request.sender,
            language=request.language,
        )
        return AgentResponse(
            content=content,
            mode="marketing",
            metadata={"language": request.language},
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
