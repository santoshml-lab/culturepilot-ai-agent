
def review_recommendations(recommendation_result: dict) -> dict:
    """Validate and review Qloo-powered recommendations."""

    if not isinstance(recommendation_result, dict):
        return {
            "approved": False,
            "review_status": "rejected",
            "reason": "Recommendation response must be an object.",
            "recommendations": [],
            "rejected_count": 0,
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
            "rejected_count": 0,
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
            "rejected_count": 0,
        }

    approved_items = []
    rejected_count = 0

    for item in recommendations:
        if not isinstance(item, dict):
            rejected_count += 1
            continue

        title = str(item.get("title") or "").strip()

        entity_id = str(
            item.get("entity_id") or item.get("id") or ""
        ).strip()

        source = str(item.get("source") or "").strip()

        # Support both the current and older score field names.
        score = item.get("score")

        if score is None:
            score = item.get("match_score")

        matched_interests = item.get("matched_interests", [])

        # 1. Essential identity fields
        if not title or not entity_id:
            rejected_count += 1
            continue

        # 2. Verify recommendation source
        if source.casefold() != "qloo":
            rejected_count += 1
            continue

        # 3. Verify numerical score
        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not 0 <= score <= 100
        ):
            rejected_count += 1
            continue

        # 4. Require evidence that interests were matched
        if (
            not isinstance(matched_interests, list)
            or not matched_interests
            or not any(
                isinstance(interest, str) and interest.strip()
                for interest in matched_interests
            )
        ):
            rejected_count += 1
            continue

        # Keep the original recommendation fields intact.
        approved_item = dict(item)

        # Normalize identity and score fields for downstream use.
        approved_item["entity_id"] = entity_id
        approved_item["score"] = score

        approved_items.append(approved_item)

    if not approved_items:
        return {
            "approved": False,
            "review_status": "rejected",
            "reason": (
                "No recommendations passed validation. "
                "Check title, entity ID, Qloo source, score "
                "and matched interests."
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
                if rejected_count
                else ""
            )
        ),
        "recommendations": approved_items,
        "rejected_count": rejected_count,
    }


