
def create_recommendation_request(
    interests: str,
    category: str,
    plan: list | None = None,
    cultural_data: list | None = None,
) -> dict:
    interests = interests.strip()
    category = category.strip().title()

    if not interests:
        raise ValueError("Interests are required.")

    results = cultural_data or []

    recommendations = []
    for item in results[:10]:
        properties = item.get("properties") or {}
        title = item.get("name") or properties.get("name")

        if title:
            recommendations.append({
                "title": title,
                "category": category,
                "description": (
                    properties.get("short_description")
                    or properties.get("description")
                    or f"Recommended for your interest in {interests}."
                ),
                "entity_id": item.get("entity_id"),
                "source": "Qloo",
            })

    return {
        "interests": interests,
        "category": category,
        "plan_received": bool(plan),
        "recommendation_status": (
            "success" if recommendations else "no_results"
        ),
        "recommendations": recommendations,
        "message": (
            f"Retrieved {len(recommendations)} recommendations from Qloo."
            if recommendations
            else "No usable recommendations were returned by Qloo."
        ),
    }

