
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from planner import create_plan
from recommender import create_recommendation_request
from reviewer import review_recommendations
from executor import execute_recommendation
from researcher import research_cultural_data


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


class PlanRequest(BaseModel):
    interests: str = Field(min_length=1, max_length=250)
    category: str = Field(min_length=1, max_length=30)


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
"planner": "implemented",
"researcher": "implemented",
"recommender": "implemented_scaffold",
"reviewer": "implemented",
"executor": "implemented",
"qloo_connected": "check_via_recommend_endpoint",
"workflow": "planner_researcher_recommender_reviewer_executor"
}




    








@app.post("/agent/plan")
def generate_plan(request: PlanRequest):
    try:
        return create_plan(
            interests=request.interests,
            category=request.category,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@app.post("/agent/recommend")
def generate_recommendation(request: PlanRequest):
    try:
        # Agent 1: Planner
        plan_result = create_plan(
            interests=request.interests,
            category=request.category,
        )

        # Agent 2: Researcher
        research_result = research_cultural_data(
            interests=request.interests,
            category=request.category,
        )

        # Agent 3: Recommender
        recommendation_result = create_recommendation_request(
            interests=request.interests,
            category=request.category,
            plan=plan_result["plan"],
        )

        # Attach the research status for transparency
        recommendation_result["research_status"] = (
            research_result["status"]
        )

        # Agent 4: Reviewer
        review_result = review_recommendations(
            recommendation_result
        )

        # Agent 5: Executor
        final_result = execute_recommendation(
            review_result
        )

        return {
            "plan": plan_result,
            "research": research_result,
            "recommendation": recommendation_result,
            "review": review_result,
            "final_result": final_result,
            "status": "workflow_completed",
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )















    
    


