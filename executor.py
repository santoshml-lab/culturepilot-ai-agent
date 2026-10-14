
def execute_recommendation(review_result: dict) -> dict:
    """
    Prepare the final user-facing response
    from the reviewer's result.
    """

    recommendations = review_result.get(
        "recommendations", []
    )

    if review_result.get("approved") and recommendations:
        return {
            "status": "success",
            "message": "Your cultural recommendations are ready.",
            "recommendations": recommendations,
        }

    return {
        "status": "pending",
        "message": (
            "Your request has been processed, but personalized "
            "recommendations are not available yet. "
            "Connect Qloo to retrieve cultural data."
        ),
        "recommendations": [],
    }
