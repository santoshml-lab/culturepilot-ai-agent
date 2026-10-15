
import re


INTEREST_ALIASES = {
    "sci-fi": [
        "science fiction", "science-fiction", "futuristic",
        "space", "alien", "technology", "artificial intelligence"
    ],
    "science fiction": [
        "sci-fi", "science-fiction", "futuristic",
        "space", "alien", "technology"
    ],
    "space": [
        "spacecraft", "astronaut", "galaxy", "planet",
        "cosmic", "orbital", "spaceflight"
    ],
    "exploration": [
        "explore", "discovery", "expedition", "mission", "journey"
    ],
    "alien": [
        "aliens", "extraterrestrial", "non-human", "lifeform"
    ],
    "intelligent aliens": [
        "alien", "aliens", "extraterrestrial",
        "artificial intelligence", "intelligence"
    ],
    "time travel": [
        "time-travel", "time loop", "timeline",
        "temporal", "back in time", "time machine"
    ],
    "artificial intelligence": [
        "ai", "intelligent machines", "robot", "android",
        "artificial life", "machine intelligence"
    ],
    "robot": ["robots", "robotic", "android", "artificial intelligence"],
    "adventure": ["adventurous", "expedition", "journey", "exploration"],
    "comedy": ["comedic", "humor", "humour", "funny", "satire"],
    "horror": ["terrifying", "fear", "supernatural", "creature"],
    "travel": ["destination", "tourism", "journey", "traveler"],
    "food": ["cuisine", "restaurant", "dish", "culinary", "dining"],
}


def normalize(text):
    text = str(text or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def split_interests(interests):
    return [
        item.strip().lower()
        for item in interests.split(",")
        if item.strip()
    ]


def get_interest_signals(interest):
    signals = {normalize(interest)}

    for key, aliases in INTEREST_ALIASES.items():
        if key in interest:
            signals.update(normalize(alias) for alias in aliases)

    return {signal for signal in signals if signal}


def score_recommendation(item, interests):
    properties = item.get("properties") or {}

    title = (
        item.get("name")
        or properties.get("name")
        or "Untitled recommendation"
    )

    description = (
        properties.get("short_description")
        or properties.get("description")
        or item.get("description")
        or ""
    )

    searchable_text = normalize(f"{title} {description}")

    matched_interests = []
    direct_matches = 0

    for interest in interests:
        normalized_interest = normalize(interest)
        signals = get_interest_signals(interest)

        # Exact phrase match is a stronger relevance signal.
        if normalized_interest and normalized_interest in searchable_text:
            matched_interests.append(interest)
            direct_matches += 1
            continue

        # Otherwise, check known related terms.
        if any(signal in searchable_text for signal in signals):
            matched_interests.append(interest)

    total_interests = max(len(interests), 1)

    # This is a heuristic relevance score, not an AI probability.
    score = 15 + (
        75 * len(matched_interests) / total_interests
    )

    score += 10 * direct_matches / total_interests
    score = round(min(100, score))

    if matched_interests:
        reason = (
            "Related to your interests: "
            + ", ".join(matched_interests)
            + "."
        )
    else:
        reason = (
            "Suggested by Qloo, but no strong keyword match "
            "was found for your stated interests."
        )

    return {
        "title": title,
        "category": item.get("category") or properties.get("type"),
        "description": description or (
            f"A recommendation in {title} related to {interests[0]}."
        ),
        "entity_id": item.get("entity_id") or item.get("id"),
        "source": "Qloo",
        "match_score": score,
        "match_reason": reason,
    }


def create_recommendation_request(
    interests,
    category,
    plan=None,
    cultural_data=None
):
    interests = interests.strip()
    category = category.strip().title()

    if not interests:
        raise ValueError("Please provide at least one interest.")

    interest_list = split_interests(interests)
    results = cultural_data or []
    recommendations = []

    for item in results:
        if not isinstance(item, dict):
            continue

        recommendation = score_recommendation(item, interest_list)
        recommendation["category"] = category
        recommendations.append(recommendation)

    # Highest relevance score first.
    recommendations.sort(
        key=lambda item: item["match_score"],
        reverse=True
    )

    recommendations = recommendations[:10]

    return {
        "interests": interests,
        "category": category,
        "plan_received": bool(plan),
        "recommendation_status": (
            "success" if recommendations else "no_results"
        ),
        "recommendations": recommendations,
        "message": (
            f"Ranked {len(recommendations)} recommendations using "
            "interest-based relevance scoring."
            if recommendations
            else "No usable recommendations were returned by Qloo."
        ),
    }


