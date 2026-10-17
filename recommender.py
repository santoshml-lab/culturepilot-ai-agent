
import re

RESULT_LIMIT = 10
MIN_MATCH_SCORE = 60


def normalize(value):
    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(item) for item in value)

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        str(value or "").casefold(),
    ).strip()


def split_interests(interests):
    return [
        item.strip()
        for item in (interests or "").split(",")
        if item.strip()
    ]


def get_properties(item):
    value = item.get("properties")
    return value if isinstance(value, dict) else {}


def get_text(value):
    if isinstance(value, str):
        return value

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, list):
        return " ".join(get_text(item) for item in value)

    if isinstance(value, dict):
        preferred = (
            "name", "value", "label",
            "title", "description", "url",
        )
        parts = [
            get_text(value[key])
            for key in preferred
            if value.get(key) is not None
        ]

        return " ".join(parts) if parts else " ".join(
            get_text(item) for item in value.values()
        )

    return ""


def get_field(item, keys):
    properties = get_properties(item)

    for source in (item, properties):
        for key in keys:
            value = source.get(key)
            if value:
                return value

    return None


def get_image_url(item):
    value = get_field(
        item,
        ["image", "images", "image_url"],
    )

    if isinstance(value, list):
        value = value[0] if value else None

    if isinstance(value, dict):
        value = value.get("url") or value.get("src")

    if isinstance(value, str) and value.startswith("https://"):
        return value

    return None


def get_genres(item):
    value = get_field(item, ["genres", "genre"])

    if not value:
        return []

    if not isinstance(value, list):
        value = [value]

    return [
        get_text(part)
        for part in value
        if get_text(part)
    ]


def score_recommendation(item, interests):
    properties = get_properties(item)

    title = (
        item.get("name")
        or item.get("title")
        or properties.get("name")
        or properties.get("title")
        or "Untitled recommendation"
    )

    description = get_text(
        get_field(
            item,
            [
                "short_description",
                "description",
                "overview",
                "disambiguation",
            ],
        )
    )

    genres = get_genres(item)

    metadata = get_text({
        "akas": properties.get("akas", []),
        "genres": properties.get("genres", []),
        "tags": properties.get("tags", []),
        "keywords": properties.get("keywords", []),
        "themes": properties.get("themes", []),
    })

    searchable_fields = {
        "title": normalize(title),
        "description": normalize(description),
        "genres": normalize(genres),
        "metadata": normalize(metadata),
    }

    matched = []
    evidence = []

    for interest in interests:
        term = normalize(interest)

        if not term:
            continue

        for field, content in searchable_fields.items():
            if term in content:
                matched.append(interest)
                evidence.append(field)
                break

    matched = list(dict.fromkeys(matched))
    evidence = list(dict.fromkeys(evidence))

    if "title" in evidence:
        score = 95
    elif "genres" in evidence:
        score = 90
    elif "description" in evidence:
        score = 75
    elif "metadata" in evidence:
        score = 70
    else:
        score = 0

    return {
        "title": str(title),
        "description": description or (
            "Qloo returned this entity as part of its "
            "cultural discovery results."
        ),
        "image_url": get_image_url(item),
        "genres": genres,
        "entity_id": item.get("entity_id") or item.get("id"),
        "source": "Qloo",
        "match_score": score,
        "match_reason": (
            "Direct metadata match: "
            + ", ".join(evidence)
            + "."
            if evidence
            else (
                "No direct metadata match was found. "
                "This entity was returned by Qloo's "
                "cultural insight results."
            )
        ),
        "matched_interests": matched,
        "recommendation_method": (
            "metadata_match" if evidence
            else "qloo_cultural_insight"
        ),
    }


def create_recommendation_request(
    interests,
    category,
    plan=None,
    cultural_data=None,
):
    interests = (interests or "").strip()
    category = (category or "").strip().title()

    if not interests:
        raise ValueError("Please provide at least one interest.")

    if category not in {"Movies", "Music", "Food", "Travel"}:
        raise ValueError(
            "Category must be Movies, Music, Food, or Travel."
        )

    results = cultural_data or []
    recommendations = []

    for item in results:
        if not isinstance(item, dict):
            continue

        entity_id = item.get("entity_id") or item.get("id")

        # Ignore malformed entities without a usable identity.
        if not entity_id:
            continue

        recommendation = score_recommendation(
            item,
            split_interests(interests),
        )
        recommendation["category"] = category

        # Qloo's insight endpoint has already selected these
        # entities using the supplied cultural interest signal.
        # Preserve these results even when metadata is incomplete.
        if recommendation["match_score"] < MIN_MATCH_SCORE:
            recommendation["match_score"] = 60
            recommendation["match_reason"] = (
                "Returned by Qloo's cultural insight endpoint "
                "for the supplied interest. Direct metadata "
                "evidence was insufficient to score a stronger match."
            )
            recommendation["matched_interests"] = []
            recommendation["recommendation_method"] = (
                "qloo_cultural_insight"
            )

        recommendations.append(recommendation)

    recommendations.sort(
        key=lambda item: (
            item["recommendation_method"] == "metadata_match",
            item["match_score"],
        ),
        reverse=True,
    )

    recommendations = recommendations[:RESULT_LIMIT]

    if recommendations:
        status = "success"
        message = (
            f"Qloo returned {len(recommendations)} cultural "
            "recommendations. Scores distinguish direct metadata "
            "evidence from Qloo insight results with limited metadata."
        )
    else:
        status = "no_results"
        message = (
            "Qloo did not return usable entities for this query. "
            "Try a specific title, artist, cuisine, or destination."
        )

    return {
        "interests": interests,
        "category": category,
        "plan_received": bool(plan),
        "recommendation_status": status,
        "recommendations": recommendations,
        "message": message,
    }







