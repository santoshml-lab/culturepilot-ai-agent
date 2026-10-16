from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from planner import create_plan, detect_category
from recommender import create_recommendation_request
from reviewer import review_recommendations
from executor import execute_recommendation
from researcher import research_cultural_data


app = FastAPI(
    title="CulturePilot AI Agent",
    description="Qloo-powered cultural discovery agent.",
    version="1.2.0",
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

    aliases = {
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
        "auto": None,
        "automatic": None,
        "all": None,
        "all experiences": None,
    }

    return aliases.get(category.strip().casefold())


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
        "generic_input": True,
        "automatic_category_detection": True,
        "supported_qloo_categories": [
            "Movies",
            "Music",
            "Food",
            "Travel",
        ],
        "workflow": (
            "planner_researcher_recommender_reviewer_executor"
        ),
    }


@app.post("/agent/plan")
def generate_plan(request: PlanRequest):
    interests = request.interests.strip()
    category = normalise_category(request.category)

    if not category:
        category = detect_category(interests)

    if not category:
        return {
            "interests": interests,
            "category": None,
            "status": "unsupported_or_unclear_category",
            "message": (
                "We couldn't identify a supported cultural category. "
                "Try Movies, Music, Food, or Travel."
            ),
            "plan": [],
        }

    try:
        return create_plan(
            interests=interests,
            category=category,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/agent/recommend")
def generate_recommendation(request: PlanRequest):
    interests = request.interests.strip()
    category = normalise_category(request.category)

    # Automatically detect the category if it wasn't selected.
    if not category:
        category = detect_category(interests)

    # Do not send unsupported topics to Qloo or invent results.
    if not category:
        message = (
            "We couldn't identify a supported cultural category for "
            "this query. Try Movies, Music, Food, or Travel."
        )

        return {
            "plan": {
                "interests": interests,
                "category": None,
                "status": "unsupported_or_unclear_category",
                "qloo_connected": False,
            },
            "research": {
                "agent": "researcher",
                "status": "unsupported_category",
                "interests": interests,
                "category": None,
                "source": "Qloo",
                "results": [],
                "message": message,
            },
            "recommendation": {
                "interests": interests,
                "category": None,
                "recommendation_status": "no_results",
                "recommendations": [],
                "message": message,
            },
            "review": {
                "approved": False,
                "review_status": "pending_data",
                "reason": message,
                "recommendations": [],
            },
            "final_result": {
                "status": "pending",
                "message": message,
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

