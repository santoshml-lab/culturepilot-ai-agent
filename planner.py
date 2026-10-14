
def create_plan(interests: str, category: str) -> dict:
    """
    Create a structured plan for a cultural discovery request.
    This starter planner uses rules; AI reasoning can be added later.
    """

    interests = interests.strip()
    category = category.strip().title()

    supported_categories = {
        "Movies",
        "Music",
        "Food",
        "Travel",
        "All experiences",
    }

    if not interests:
        raise ValueError("Please provide your interests.")

    if category not in supported_categories:
        raise ValueError(
            "Choose Movies, Music, Food, Travel, or All experiences."
        )

    steps = [
        {
            "step": 1,
            "agent": "planner",
            "task": "Understand the user's interests and category.",
        },
        {
            "step": 2,
            "agent": "researcher",
            "task": "Retrieve relevant cultural data when Qloo API is available.",
        },
        {
            "step": 3,
            "agent": "recommender",
            "task": "Select recommendations that match the user's interests.",
        },
        {
            "step": 4,
            "agent": "reviewer",
            "task": "Check relevance and verify available recommendation data.",
        },
        {
            "step": 5,
            "agent": "executor",
            "task": "Return the reviewed results to the user.",
        },
    ]

    return {
        "interests": interests,
        "category": category,
        "plan": steps,
        "status": "plan_created",
        "qloo_required": True,
        "qloo_connected": False,
    }
