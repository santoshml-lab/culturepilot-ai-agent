
import re


INTEREST_ALIASES = {
    "sci-fi": [
        "science fiction", "futuristic", "space exploration",
        "alien", "artificial intelligence"
    ],
    "science fiction": [
        "sci-fi", "futuristic", "space exploration",
        "alien", "artificial intelligence"
    ],
    "space exploration": [
        "spacecraft", "astronaut", "galaxy", "spaceflight",
        "space mission", "planetary exploration"
    ],
    "intelligent aliens": [
        "extraterrestrial intelligence", "alien intelligence",
        "intelligent extraterrestrial", "alien civilization",
        "first contact"
    ],
    "time travel": [
        "time-travel", "time machine", "time loop",
        "travels through time", "travel through time",
        "back in time", "temporal journey", "timeline"
    ],
    "artificial intelligence": [
        "machine intelligence", "intelligent machine",
        "android", "sentient robot", "artificial life"
    ],
    "adventure": [
        "expedition", "exploration", "adventurous journey"
    ],
    "comedy": [
        "comedic", "humorous", "black comedy", "satire"
    ],
    "horror": [
        "horror film", "supernatural horror", "creature horror"
    ],
}


def normalize(text):
    """Normalize text while preserving word boundaries."""
    text = str(text or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def contains_phrase(text, phrase):
    """Match a complete phrase, not a substring inside another word."""
    normalized_text = f" {normalize(text)} "
    normalized_phrase = f" {normalize(phrase)} "

    if normalized_phrase.strip() == "":
        return False

    return normalized_phrase in normalized_text


def split_interests(interests):
    return [
        item.strip().lower()
        for item in interests.split(",")
        if item.strip()
    ]


def get_interest_signals(interest):
    normalized_interest = normalize(interest)
    signals = {normalized_interest}

    # Only expand aliases when the user actually entered
    # the corresponding interest phrase.
    for key, aliases in INTEREST_ALIASES.items():
        if normalized_interest == normalize(key):
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

    # Use title and description separately so title-only matches
    # cannot outweigh the actual recommendation details.
    matched_interests = []
    title_matches = []
    direct_matches = 0

    for interest in interests:
        signals = get_interest_signals(interest)

        direct_match = any(
            contains_phrase(title, signal)
            or contains_phrase(description, signal)
            for signal in signals
        )

        if direct_match:
            matched_interests.append(interest)

            if contains_phrase(title, normalize(interest)):
                title_matches.append(interest)

            if (
                contains_phrase(title, normalize(interest))
                or contains_phrase(description, normalize(interest))
            ):
                direct_matches += 1

    total_interests = max(len(interests), 1)
    match_count = len(matched_interests)

    # Conservative heuristic: no matching interest means a low score.
    if match_count == 0:
        score = 10
        reason = (
            "No strong keyword match was found for your stated interests. "
            "This item was returned by Qloo but may be less relevant."
        )
    else:
        coverage = match_count / total_interests
        score = round(20 + (60 * coverage) + (
            10 * direct_matches / total_interests
        ))

        if title_matches:
            score = min(100, score + 5)

        reason = (
            "Related to your interests: "
            + ", ".join(matched_interests)
            + "."
        )

    return {
        "title": title,
        "category": None,
        "description": description or "No additional description available.",
        "entity_id": item.get("entity_id") or item.get("id"),
        "source": "Qloo",
        "match_score": score,
        "match_reason": reason,
        "matched_interests": matched_interests,
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

    # Rank stronger matches first; preserve input order for ties.
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
            f"Ranked {len(recommendations)} recommendations "
            "using conservative keyword relevance scoring."
            if recommendations
            else "No usable recommendations were returned by Qloo."
        ),
    }



