from fastapi import APIRouter, HTTPException

from models import AgentRequest, AgentResponse
from agent import generate_response

router = APIRouter()


@router.post("/gallery-document", response_model=AgentResponse)
async def gallery_document(request: AgentRequest):
    try:
        content = await generate_response(
            mode="document",
            message=request.message,
            recipient=request.recipient,
            sender=request.sender,
            language=request.language,
        )
        return AgentResponse(
            content=content,
            mode="document",
            metadata={"document_type": "gallery_document"},
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
