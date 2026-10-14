
def review_recommendations(recommendation_result: dict) -> dict:
    """
    Review recommendation results before they reach the user.
    """

    recommendations = recommendation_result.get(
        "recommendations", []
    )

    if not isinstance(recommendations, list):
        return {
            "approved": False,
            "review_status": "rejected",
            "reason": "Recommendations must be a list.",
            "recommendations": [],
        }

    if not recommendations:
        return {
            "approved": False,
            "review_status": "pending_data",
            "reason": (
                "No recommendations available yet. "
                "Connect Qloo to retrieve cultural data."
            ),
            "recommendations": [],
        }

    return {
        "approved": True,
        "review_status": "approved",
        "reason": "Recommendation data passed the basic review.",
        "recommendations": recommendations,
    }
