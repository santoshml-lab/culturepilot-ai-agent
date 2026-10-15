
import re


INTEREST_ALIASES = {
    "sci-fi": [
        "science fiction",
        "futuristic",
        "space exploration",
        "alien",
        "artificial intelligence",
    ],
    "science fiction": [
        "sci-fi",
        "futuristic",
        "space exploration",
        "alien",
        "artificial intelligence",
    ],
    "space exploration": [
        "spacecraft",
        "astronaut",
        "galaxy",
        "spaceflight",
        "space mission",
        "planetary exploration",
    ],
    "intelligent aliens": [
        "extraterrestrial intelligence",
        "alien intelligence",
        "intelligent extraterrestrial",
        "alien civilization",
        "first contact",
        "intelligent alien",
        "extraterrestrial",
    ],
    "time travel": [
        "time-travel",
        "time machine",
        "time loop",
        "travels through time",
        "travel through time",
        "back in time",
        "temporal journey",
        "timeline",
    ],
    "artificial intelligence": [
        "machine intelligence",
        "intelligent machine",
        "android",
        "sentient robot",
        "artificial life",
        "robotics",
    ],
    "adventure": [
        "expedition",
        "exploration",
        "adventurous journey",
    ],
    "comedy": [
        "comedic",
        "humorous",
        "black comedy",
        "satire",
    ],
    "horror": [
        "horror film",
        "supernatural horror",
        "creature horror",
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

    if not normalized_phrase.strip():
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

    for key, aliases in INTEREST_ALIASES.items():
        if normalized_interest == normalize(key):
            signals.update(normalize(alias) for alias in aliases)

    return {signal for signal in signals if signal}


def get_image_url(item):
    """Extract the image URL from the Qloo entity response."""
    properties = item.get("properties") or {}

    image = (
        item.get("image")
        or properties.get("image")
    )

    if isinstance(image, dict):
        url = image.get("url")
    elif isinstance(image, str):
        url = image
    else:
        url = None

    # Only retain ordinary HTTP/HTTPS image URLs.
    if isinstance(url, str) and url.startswith(("https://", "http://")):
        return url

    return None


def get_genres(item):
    """Read genre information from common Qloo response locations."""
    properties = item.get("properties") or {}

    genres = (
        item.get("genres")
        or properties.get("genres")
        or []
    )

    if isinstance(genres, str):
        return [genres]

    if isinstance(genres, list):
        return [
            str(genre)
            for genre in genres
            if isinstance(genre, (str, int, float))
        ]

    return []


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

    genres = get_genres(item)
    keywords = (
        item.get("keywords")
        or properties.get("keywords")
        or []
    )

    if not isinstance(keywords, list):
        keywords = []

    # Include genres and keywords in relevance matching.
    metadata_text = " ".join(
        [str(value) for value in genres + keywords]
    )

    matched_interests = []
    title_matches = []
    direct_matches = 0

    for interest in interests:
        signals = get_interest_signals(interest)

        # Match the user's interest or its aliases against Qloo data.
        matched = any(
            contains_phrase(text, signal)
            for text in (title, description, metadata_text)
            for signal in signals
        )

        if matched:
            matched_interests.append(interest)

            if contains_phrase(title, normalize(interest)):
                title_matches.append(interest)

            # Direct match means the exact entered interest appears
            # in the title or description.
            if (
                contains_phrase(title, normalize(interest))
                or contains_phrase(description, normalize(interest))
            ):
                direct_matches += 1

    total_interests = max(len(interests), 1)
    match_count = len(matched_interests)

    if match_count == 0:
        score = 10
        reason = (
            "No strong keyword match was found for your stated interests. "
            "This item was returned by Qloo but may be less relevant."
        )
    else:
        coverage = match_count / total_interests

        score = round(
            20
            + (60 * coverage)
            + (10 * direct_matches / total_interests)
        )

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
        "description": (
            description or "No additional description available."
        ),
        "image_url": get_image_url(item),
        "genres": genres,
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
    cultural_data=None,
):
    interests = (interests or "").strip()
    category = (category or "").strip().title()

    if not interests:
        raise ValueError("Please provide at least one interest.")

    interest_list = split_interests(interests)
    results = cultural_data or []
    recommendations = []

    for item in results:
        if not isinstance(item, dict):
            continue

        recommendation = score_recommendation(
            item,
            interest_list,
        )
        recommendation["category"] = category
        recommendations.append(recommendation)

    # Rank stronger matches first; preserve input order for ties.
    recommendations.sort(
        key=lambda item: item["match_score"],
        reverse=True,
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
            "using keyword relevance scoring and Qloo metadata."
            if recommendations
            else "No usable recommendations were returned by Qloo."
        ),
    }




