import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from routers import email, whatsapp, marketing, document, translate, fair

DATA_DIR = Path(__file__).parent / "data"
CONTEXT_PATH = Path(__file__).parent.parent / "context" / "sun_gallery_agent_context_v3.md"

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


@app.get("/api/data/collectors")
async def get_collectors():
    return json.loads((DATA_DIR / "collectors.json").read_text())


@app.get("/api/data/fairs")
async def get_fairs():
    return json.loads((DATA_DIR / "fair_schedule.json").read_text())


@app.get("/api/data/artists")
async def get_artists():
    return json.loads((DATA_DIR / "artists.json").read_text())


@app.get("/api/data/inventory")
async def get_inventory():
    return json.loads((DATA_DIR / "inventory.json").read_text())


@app.get("/api/data/context")
async def get_context():
    content = CONTEXT_PATH.read_text(encoding="utf-8") if CONTEXT_PATH.exists() else ""
    return PlainTextResponse(content)
