
def execute_recommendation(review_result: dict) -> dict:
    """Build the final response from the reviewer's decision."""

    if not isinstance(review_result, dict):
        return {
            "status": "error",
            "message": "The review agent returned an invalid response.",
            "recommendations": [],
            "total": 0,
        }

    recommendations = review_result.get("recommendations", [])

    if not isinstance(recommendations, list):
        recommendations = []

    if not review_result.get("approved") or not recommendations:
        return {
            "status": "pending",
            "message": (
                "No recommendations passed review. "
                "Please try another interest or check the Qloo response."
            ),
            "recommendations": [],
            "total": 0,
            "review_status": review_result.get(
                "review_status", "pending_data"
            ),
        }

    # Keep only dictionary items with a usable title.
    final_recommendations = [
        item
        for item in recommendations
        if isinstance(item, dict)
        and str(item.get("title") or "").strip()
    ]

    if not final_recommendations:
        return {
            "status": "pending",
            "message": "No displayable recommendations remain after validation.",
            "recommendations": [],
            "total": 0,
        }

    return {
        "status": "success",
        "message": (
            f"Ready! Qloo-powered discovery returned "
            f"{len(final_recommendations)} recommendations."
        ),
        "recommendations": final_recommendations,
        "total": len(final_recommendations),
        "source": "Qloo",
        "review_status": review_result.get(
            "review_status", "approved"
        ),
    }

