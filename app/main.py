from fastapi import FastAPI
from app.routers import summarize as summarize_router
from app.logging_config import logger
from fastapi.middleware.cors import CORSMiddleware

from app.services.groq_client import aclose_httpx_client

app = FastAPI(title="Rekapin Summarizer", version="1.0")

# minimal CORS example (adjust origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # CHANGE to specific origins in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(summarize_router.router)

@app.get("/health")
def health():
    return {"status": "ok"}

# Adjustment from refactoring app/services/groq_client.py
@app.on_event("startup")
async def on_startup():
    logger.info("Starting Rekapin Summarizer API")

@app.on_event("shutdown")
async def on_shutdown():
    await aclose_httpx_client()
    logger.info("Closed HTTPX client and shutting down.")