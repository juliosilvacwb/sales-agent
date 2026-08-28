from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(
    title="Sales Data Analysis API",
    description="API for the Sales Data Analysis Agent Web Chat Interface",
    version="1.0.0"
)

from src.adapter.inbound.web.chat_controller import router as chat_router
app.include_router(chat_router)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/health")
def health_check():
    return {"status": "ok"}
