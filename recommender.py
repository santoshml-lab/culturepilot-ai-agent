
def create_recommendation_request(
    interests: str,
    category: str,
    plan: list | None = None,
) -> dict:
    """
    Prepare a structured recommendation request.
    Real recommendations will come from Qloo after API integration.
    """

    interests = interests.strip()
    category = category.strip().title()

    if not interests:
        raise ValueError("Interests are required.")

    return {
        "interests": interests,
        "category": category,
        "plan_received": bool(plan),
        "recommendation_status": "awaiting_qloo_data",
        "recommendations": [],
        "message": (
            "The request is ready. Connect Qloo to retrieve "
            "personalized cultural recommendations."
        ),
    }
