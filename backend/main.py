from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import email, whatsapp, marketing, document, translate, fair

app = FastAPI(
    title="Sun Gallery AI Assistant",
    description="선화랑 에이전틱 AI 어시스턴트 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(email.router, prefix="/api", tags=["Email"])
app.include_router(whatsapp.router, prefix="/api", tags=["WhatsApp"])
app.include_router(marketing.router, prefix="/api", tags=["Marketing"])
app.include_router(document.router, prefix="/api", tags=["Document"])
app.include_router(translate.router, prefix="/api", tags=["Translate"])
app.include_router(fair.router, prefix="/api", tags=["Fair"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Sun Gallery AI Assistant"}
