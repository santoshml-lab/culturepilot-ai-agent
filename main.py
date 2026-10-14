
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="CulturePilot AI Agent",
    description="Agentic AI for personalized cultural discovery.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://culturepilot-ai.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/")
def home():
    return {
        "project": "CulturePilot AI",
        "status": "online",
        "message": "CulturePilot AI Agent backend is ready.",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/agent/status")
def agent_status():
    return {
        "planner": "planned",
        "researcher": "awaiting_qloo_api",
        "recommender": "planned",
        "reviewer": "planned",
        "executor": "planned",
        "qloo_connected": False,
    }
