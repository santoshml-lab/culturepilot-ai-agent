
def review_recommendations(recommendation_result: dict) -> dict:
    """Validate and review Qloo-powered recommendations."""

    if not isinstance(recommendation_result, dict):
        return {
            "approved": False,
            "review_status": "rejected",
            "reason": "Recommendation response must be an object.",
            "recommendations": [],
        }

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
                "No usable recommendations were returned. "
                "Check the Qloo research response."
            ),
            "recommendations": [],
        }

    approved_items = []
    rejected_count = 0

    for item in recommendations:
        if not isinstance(item, dict):
            rejected_count += 1
            continue

        title = str(item.get("title") or "").strip()
        entity_id = str(item.get("entity_id") or "").strip()
        source = str(item.get("source") or "").strip()
        method = str(
            item.get("recommendation_method") or ""
        ).strip()
        score = item.get("match_score")

        if not title or not entity_id:
            rejected_count += 1
            continue

        if source.casefold() != "qloo":
            rejected_count += 1
            continue

        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not 0 <= score <= 100
        ):
            rejected_count += 1
            continue

        # Permit direct metadata matches and results returned
        # by Qloo's cultural insight endpoint.
        if method not in {
            "metadata_match",
            "qloo_cultural_insight",
        }:
            rejected_count += 1
            continue

        approved_items.append(item)

    if not approved_items:
        return {
            "approved": False,
            "review_status": "rejected",
            "reason": (
                "No recommendations passed validation. "
                "Check entity IDs, source and scoring fields."
            ),
            "recommendations": [],
            "rejected_count": rejected_count,
        }

    return {
        "approved": True,
        "review_status": "approved",
        "reason": (
            f"{len(approved_items)} recommendations passed review."
            + (
                f" {rejected_count} invalid items were excluded."
                if rejected_count else ""
            )
        ),
        "recommendations": approved_items,
        "rejected_count": rejected_count,
    }

