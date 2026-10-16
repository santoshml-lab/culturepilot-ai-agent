
import re


MIN_MATCH_SCORE = 60
RESULT_LIMIT = 10

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
    "indie pop": [
        "indie pop",
        "independent pop",
    ],
    "indian street food": [
        "indian street food",
        "street food",
        "indian cuisine",
    ],
    "mountain destinations": [
        "mountain destinations",
        "mountain travel",
        "mountains",
    ],
}


def normalize(text):
    """Normalize text while preserving word boundaries."""
    text = str(text or "").casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def contains_phrase(text, phrase):
    """Match a normalized complete phrase."""
    normalized_text = f" {normalize(text)} "
    normalized_phrase = normalize(phrase)

    if not normalized_phrase:
        return False

    return f" {normalized_phrase} " in normalized_text


def split_interests(interests):
    return [
        item.strip().casefold()
        for item in (interests or "").split(",")
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
    """Extract an ordinary HTTP/HTTPS image URL."""
    properties = item.get("properties") or {}
    image = item.get("image") or properties.get("image")

    if isinstance(image, dict):
        url = image.get("url")
    elif isinstance(image, str):
        url = image
    else:
        url = None

    if isinstance(url, str) and url.startswith(("https://", "http://")):
        return url

    return None


def get_genres(item):
    """Read genre metadata from common response locations."""
    properties = item.get("properties") or {}
    genres = item.get("genres") or properties.get("genres") or []

    if isinstance(genres, str):
        return [genres]

    if isinstance(genres, list):
        return [
            str(genre)
            for genre in genres
            if isinstance(genre, (str, int, float))
        ]

    return []


def get_keywords(item):
    """Read keyword metadata safely."""
    properties = item.get("properties") or {}
    keywords = item.get("keywords") or properties.get("keywords") or []

    if isinstance(keywords, str):
        return [keywords]

    if isinstance(keywords, list):
        return [
            str(value)
            for value in keywords
            if isinstance(value, (str, int, float))
        ]

    return []


def score_recommendation(item, interests):
    properties = item.get("properties") or {}

    title = (
        item.get("name")
        or properties.get("name")
        or item.get("title")
        or properties.get("title")
        or "Untitled recommendation"
    )

    description = (
        properties.get("short_description")
        or properties.get("description")
        or item.get("short_description")
        or item.get("description")
        or ""
    )

    genres = get_genres(item)
    keywords = get_keywords(item)

    normalized_title = normalize(title)
    normalized_description = normalize(description)
    normalized_genres = normalize(" ".join(genres))
    normalized_keywords = normalize(" ".join(keywords))

    matched_interests = []
    title_matches = []
    genre_matches = []
    keyword_matches = []
    description_matches = []

    for interest in interests:
        signals = get_interest_signals(interest)

        def matches_any(text):
            return any(
                contains_phrase(text, signal)
                for signal in signals
            )

        title_match = matches_any(normalized_title)
        genre_match = matches_any(normalized_genres)
        keyword_match = matches_any(normalized_keywords)
        description_match = matches_any(normalized_description)

        if any([
            title_match,
            genre_match,
            keyword_match,
            description_match,
        ]):
            matched_interests.append(interest)

        if title_match:
            title_matches.append(interest)

        if genre_match:
            genre_matches.append(interest)

        if keyword_match:
            keyword_matches.append(interest)

        if description_match:
            description_matches.append(interest)

    # Score the strongest evidence rather than rewarding repeated
    # mentions of the same interest across every field.
    score = 0

    if title_matches:
        score = max(score, 95)

    if genre_matches:
        score = max(score, 90)

    if keyword_matches:
        score = max(score, 80)

    if description_matches:
        score = max(score, 70)

    # No matching evidence means this item is not recommended.
    if not matched_interests:
        score = 10
        reason = (
            "No strong match was found for your interests. "
            "This result has been excluded from recommendations."
        )
    else:
        evidence = []

        if title_matches:
            evidence.append("title")

        if genre_matches:
            evidence.append("genre")

        if keyword_matches:
            evidence.append("keywords")

        if description_matches:
            evidence.append("description")

        reason = (
            "Matched interests: "
            + ", ".join(matched_interests)
            + ". Evidence: "
            + ", ".join(evidence)
            + "."
        )

    return {
        "title": str(title),
        "category": None,
        "description": (
            str(description)
            if description
            else "No additional description available."
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
    scored_recommendations = []

    for item in results:
        if not isinstance(item, dict):
            continue

        recommendation = score_recommendation(
            item,
            interest_list,
        )

        recommendation["category"] = category
        scored_recommendations.append(recommendation)

    # Exclude weak matches before ranking.
    recommendations = [
        item
        for item in scored_recommendations
        if item["match_score"] >= MIN_MATCH_SCORE
    ]

    # Highest score first; input order is preserved for ties.
    recommendations.sort(
        key=lambda item: item["match_score"],
        reverse=True,
    )

    recommendations = recommendations[:RESULT_LIMIT]

    if recommendations:
        message = (
            f"Selected {len(recommendations)} recommendations "
            f"with scores of at least {MIN_MATCH_SCORE}/100."
        )
        status = "success"
    else:
        message = (
            "No recommendations met the minimum relevance score. "
            "Try a different interest or a more specific query."
        )
        status = "no_results"

    return {
        "interests": interests,
        "category": category,
        "plan_received": bool(plan),
        "recommendation_status": status,
        "recommendations": recommendations,
        "message": message,
    }






