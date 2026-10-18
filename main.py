
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from recommender import create_recommendation_request
from reviewer import review_recommendations
from executor import execute_recommendation
from researcher import research_cultural_data
from planner import create_plan, detect_category

from lighting_advisor import (
    is_lighting_query,
    extract_taste_seed,
    create_lighting_recommendation,
)


app = FastAPI(
    title="CulturePilot AI Agent",
    description=(
        "Qloo-powered cultural discovery and "
        "personalized room lighting advisor."
    ),
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
    allow_methods=["*"],
    allow_headers=["*"],
    
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
        "lighting_advisor": "implemented",
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
        "additional_advisor": "Lighting",
    }


@app.post("/agent/plan")
def generate_plan(request: PlanRequest):
    interests = request.interests.strip()

    if not interests:
        raise HTTPException(
            status_code=400,
            detail="Please provide your interests.",
        )

    # Lighting is an advisor use case, not a Qloo entity category.
    if is_lighting_query(interests):
        return {
            "interests": interests,
            "category": "Lighting",
            "status": "plan_created",
            "qloo_required": False,
            "plan": [
                {
                    "step": 1,
                    "agent": "planner",
                    "task": "Identify room, activity, mood and style.",
                },
                {
                    "step": 2,
                    "agent": "researcher",
                    "task": (
                        "Look up an explicit supported cultural "
                        "taste in Qloo when available."
                    ),
                },
                {
                    "step": 3,
                    "agent": "recommender",
                    "task": "Create room lighting suggestions.",
                },
                {
                    "step": 4,
                    "agent": "reviewer",
                    "task": "Validate the suggestion list.",
                },
                {
                    "step": 5,
                    "agent": "executor",
                    "task": "Return the final suggestions.",
                },
            ],
        }

    category = normalise_category(request.category)

    if not category:
        category = detect_category(interests)

    if not category:
        return {
            "interests": interests,
            "category": None,
            "status": "unsupported_or_unclear_category",
            "message": (
                "Try Movies, Music, Food, Travel, "
                "or describe a room lighting requirement."
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

    if not interests:
        raise HTTPException(
            status_code=400,
            detail="Please provide your interests.",
        )

    # --------------------------------------------------
    # Lighting Advisor workflow
    # --------------------------------------------------
    if is_lighting_query(interests):
        taste_seed = extract_taste_seed(interests)

        research_result = {
            "agent": "researcher",
            "status": "not_requested",
            "source": "Qloo",
            "results": [],
            "message": (
                "No supported cultural taste was identified "
                "for a Qloo lookup."
            ),
        }

        # Query Qloo only for a recognised, supported category.
        if taste_seed:
            try:
                research_result = research_cultural_data(
                    interests=taste_seed["query"],
                    category=taste_seed["category"],
                )
            except (ValueError, TypeError) as error:
                research_result = {
                    "agent": "researcher",
                    "status": "research_error",
                    "source": "Qloo",
                    "results": [],
                    "message": str(error),
                }

        qloo_context = []

        for item in research_result.get("results", []):
            if not isinstance(item, dict):
                continue

            name = (
                item.get("name")
                or item.get("title")
            )

            if name:
                qloo_context.append(str(name))

        recommendation_result = create_lighting_recommendation(
            interests=interests,
            qloo_context=qloo_context,
            taste_seed=taste_seed,
        )

        recommendation_result["research_status"] = (
            research_result.get("status", "unknown")
        )

        recommendation_result["qloo_personalization_verified"] = (
            research_result.get("status") == "success"
            and bool(qloo_context)
        )

        # Reviewer and executor use the existing interfaces.
        review_result = review_recommendations(
            recommendation_result
        )

        final_result = execute_recommendation(review_result)

        plan_result = {
            "interests": interests,
            "category": "Lighting",
            "status": "plan_created",
            "qloo_connected": (
                research_result.get("status") == "success"
                and bool(qloo_context)
            ),
            "plan": [
                {
                    "step": 1,
                    "agent": "planner",
                    "task": "Identify room, activity and mood.",
                },
                {
                    "step": 2,
                    "agent": "researcher",
                    "task": "Retrieve cultural taste context if available.",
                },
                {
                    "step": 3,
                    "agent": "recommender",
                    "task": "Generate room lighting suggestions.",
                },
                {
                    "step": 4,
                    "agent": "reviewer",
                    "task": "Review suggestions.",
                },
                {
                    "step": 5,
                    "agent": "executor",
                    "task": "Return final results.",
                },
            ],
        }

        return {
            "plan": plan_result,
            "research": research_result,
            "recommendation": recommendation_result,
            "review": review_result,
            "final_result": final_result,
            "status": "workflow_completed",
        }

    # --------------------------------------------------
    # Existing Movies, Music, Food and Travel workflow
    # --------------------------------------------------
    category = normalise_category(request.category)

    if not category:
        category = detect_category(interests)

    if not category:
        return {
            "plan": {
                "interests": interests,
                "category": None,
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
                    "Try Movies, Music, Food, or Travel. "
                    "For room lighting, describe the room and "
                    "the mood or activity you want."
                ),
            },
            "recommendation": {
                "recommendation_status": "pending_data",
                "recommendations": [],
                "message": "No cultural recommendations were generated.",
            },
            "review": {
                "approved": False,
                "review_status": "pending_data",
                "reason": "No supported cultural category was identified.",
                "recommendations": [],
            },
            "final_result": {
                "status": "pending",
                "message": (
                    "Please provide a supported cultural category "
                    "or a room lighting request."
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

















    
    


