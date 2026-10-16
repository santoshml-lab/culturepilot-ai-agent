
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
    description="Qloo-powered cultural discovery agent.",
    version="1.1.0",
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
    category: str | None = Field(default=None, max_length=30)


def normalise_category(category):
    if not category:
        return None

    value = category.strip().casefold()

    categories = {
        "movies": "Movies",
        "movie": "Movies",
        "film": "Movies",
        "films": "Movies",
        "music": "Music",
        "artist": "Music",
        "artists": "Music",
        "food": "Food",
        "restaurant": "Food",
        "restaurants": "Food",
        "travel": "Travel",
        "destination": "Travel",
        "destinations": "Travel",
    }

    return categories.get(value)


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
        "workflow": (
            "planner_researcher_recommender_reviewer_executor"
        ),
        "generic_input": True,
        "supported_qloo_categories": [
            "Movies",
            "Music",
            "Food",
            "Travel",
        ],
    }


@app.post("/agent/plan")
def generate_plan(request: PlanRequest):
    category = normalise_category(request.category)

    if not category:
        return {
            "interests": request.interests.strip(),
            "category": request.category,
            "status": "needs_category",
            "message": (
                "Choose a supported cultural category: "
                "Movies, Music, Food, or Travel."
            ),
            "qloo_required": True,
            "qloo_connected": False,
        }

    try:
        return create_plan(
            interests=request.interests.strip(),
            category=category,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/agent/recommend")
def generate_recommendation(request: PlanRequest):
    interests = request.interests.strip()
    category = normalise_category(request.category)

    # Accept any query, but do not invent a Qloo entity type.
    if not category:
        return {
            "plan": {
                "interests": interests,
                "category": request.category,
                "status": "needs_category",
                "qloo_connected": False,
            },
            "research": {
                "agent": "researcher",
                "status": "unsupported_or_unspecified_category",
                "interests": interests,
                "results": [],
                "source": "Qloo",
                "message": (
                    "Your query was received, but this version "
                    "needs a supported cultural category to search "
                    "Qloo. Try Movies, Music, Food, or Travel. "
                    "Other topics may require a different data source."
                ),
            },
            "recommendation": {
                "recommendation_status": "pending_data",
                "recommendations": [],
                "message": "No recommendations were generated.",
            },
            "review": {
                "approved": False,
                "review_status": "pending_data",
                "reason": "No research results were available.",
                "recommendations": [],
            },
            "final_result": {
                "status": "pending",
                "message": (
                    "No recommendations available. "
                    "Please choose a supported category."
                ),
                "recommendations": [],
            },
            "status": "workflow_completed",
        }

    try:
        # Agent 1: Planner
        plan_result = create_plan(
            interests=interests,
            category=category,
        )

        # Agent 2: Researcher
        research_result = research_cultural_data(
            interests=interests,
            category=category,
        )

        # Agent 3: Recommender
        recommendation_result = create_recommendation_request(
            interests=interests,
            category=category,
            plan=plan_result["plan"],
            cultural_data=research_result.get("results", []),
        )

        recommendation_result["research_status"] = (
            research_result.get("status", "unknown")
        )

        # Agent 4: Reviewer
        review_result = review_recommendations(
            recommendation_result
        )

        # Agent 5: Executor
        final_result = execute_recommendation(review_result)

        plan_result["qloo_connected"] = (
            research_result.get("status") == "success"
            and research_result.get("source") == "Qloo"
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
        raise HTTPException(status_code=400, detail=str(error))
















    
    


