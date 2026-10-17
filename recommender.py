import re

MIN_MATCH_SCORE = 60
RESULT_LIMIT = 10

INTEREST_ALIASES = {
    "sci-fi": [
        "science fiction", "futuristic",
        "space exploration", "alien",
        "artificial intelligence",
    ],
    "science fiction": [
        "sci-fi", "futuristic",
        "space exploration", "alien",
        "artificial intelligence",
    ],
    "space exploration": [
        "spacecraft", "astronaut", "galaxy",
        "spaceflight", "space mission",
        "planetary exploration",
    ],
    "intelligent aliens": [
        "extraterrestrial intelligence",
        "alien intelligence", "alien civilization",
        "first contact", "extraterrestrial",
    ],
    "time travel": [
        "time-travel", "time machine", "time loop",
        "travels through time", "back in time",
        "temporal journey", "timeline",
    ],
    "artificial intelligence": [
        "machine intelligence", "intelligent machine",
        "android", "sentient robot",
        "artificial life", "robotics",
    ],
    "adventure": [
        "expedition", "exploration",
        "adventurous journey",
    ],
    "comedy": [
        "comedic", "humorous",
        "black comedy", "satire",
    ],
    "horror": [
        "horror film", "supernatural horror",
        "creature horror",
    ],
    "indie pop": ["independent pop"],
    "indie rock": ["indie music", "independent rock"],
    "jazz": ["jazz music"],
    "indian street food": [
        "street food", "indian cuisine",
    ],
    "mountain destinations": [
        "mountain travel", "mountains",
    ],
}


def normalize(text):
    if isinstance(text, (list, tuple, set)):
        text = " ".join(str(value) for value in text)
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        str(text or "").casefold(),
    ).strip()


def contains_phrase(text, phrase):
    text = f" {normalize(text)} "
    phrase = normalize(phrase)
    return bool(phrase) and f" {phrase} " in text


def split_interests(interests):
    return [
        item.strip().casefold()
        for item in (interests or "").split(",")
        if item.strip()
    ]


def get_interest_signals(interest):
    normalized = normalize(interest)
    signals = {normalized}

    for key, aliases in INTEREST_ALIASES.items():
        if normalized == normalize(key):
            signals.update(normalize(alias) for alias in aliases)

    return {signal for signal in signals if signal}


def get_properties(item):
    properties = item.get("properties")
    return properties if isinstance(properties, dict) else {}


def get_text(value):
    """Convert common Qloo metadata values to searchable text."""
    if isinstance(value, str):
        return value

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, list):
        return " ".join(
            get_text(part) for part in value if part is not None
        )

    if isinstance(value, dict):
        # Common named metadata objects
        for key in ("name", "value", "label", "title", "description"):
            if value.get(key):
                return get_text(value[key])

        return " ".join(get_text(v) for v in value.values())

    return ""


def get_field(item, keys):
    properties = get_properties(item)

    for key in keys:
        value = item.get(key)
        if value:
            return value

    for key in keys:
        value = properties.get(key)
        if value:
            return value

    return None


def get_image_url(item):
    image = get_field(item, ["image", "images", "image_url"])

    if isinstance(image, list):
        image = image[0] if image else None

    if isinstance(image, dict):
        image = image.get("url") or image.get("src")

    if isinstance(image, str) and image.startswith(("https://", "http://")):
        return image

    return None


def get_genres(item):
    value = get_field(item, ["genres", "genre"])
    if not value:
        return []
    if not isinstance(value, list):
        value = [value]
    return [get_text(v) for v in value if get_text(v)]


def get_keywords(item):
    value = get_field(
        item,
        ["keywords", "tags", "interests", "themes", "subgenres"],
    )
    if not value:
        return []
    if not isinstance(value, list):
        value = [value]
    return [get_text(v) for v in value if get_text(v)]


def score_recommendation(item, interests):
    properties = get_properties(item)

    title = (
        item.get("name")
        or item.get("title")
        or properties.get("name")
        or properties.get("title")
        or "Untitled recommendation"
    )

    description = get_field(
        item,
        [
            "short_description",
            "description",
            "overview",
            "disambiguation",
        ],
    )

    description_text = get_text(description)
    genres = get_genres(item)
    keywords = get_keywords(item)

    # Include only useful, text-based metadata.
    metadata_text = " ".join([
        get_text(properties.get("akas")),
        get_text(properties.get("short_description")),
        get_text(properties.get("description")),
        get_text(properties.get("genres")),
        get_text(properties.get("keywords")),
        get_text(properties.get("tags")),
        get_text(properties.get("themes")),
    ])

    title_matches = []
    genre_matches = []
    keyword_matches = []
    description_matches = []
    metadata_matches = []

    for interest in interests:
        signals = get_interest_signals(interest)

        def matches_any(text):
            return any(contains_phrase(text, signal) for signal in signals)

        if matches_any(title):
            title_matches.append(interest)

        if matches_any(genres):
            genre_matches.append(interest)

        if matches_any(keywords):
            keyword_matches.append(interest)

        if matches_any(description_text):
            description_matches.append(interest)

        if matches_any(metadata_text):
            metadata_matches.append(interest)

    matched_interests = list(dict.fromkeys(
        title_matches
        + genre_matches
        + keyword_matches
        + description_matches
        + metadata_matches
    ))

    # Score the strongest evidence, not duplicate mentions.
    score = 0
    evidence = []

    if title_matches:
        score = max(score, 95)
        evidence.append("title")

    if genre_matches:
        score = max(score, 90)
        evidence.append("genre")

    if keyword_matches:
        score = max(score, 80)
        evidence.append("keywords")

    if description_matches:
        score = max(score, 70)
        evidence.append("description")

    if metadata_matches:
        score = max(score, 70)
        evidence.append("metadata")

    if not matched_interests:
        score = 10
        reason = (
            "No matching interest was found in the available metadata."
        )
    else:
        reason = (
            "Matched interests: "
            + ", ".join(matched_interests)
            + ". Evidence: "
            + ", ".join(dict.fromkeys(evidence))
            + "."
        )

    return {
        "title": str(title),
        "category": None,
        "description": (
            description_text
            if description_text
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

        recommendation = score_recommendation(item, interest_list)
        recommendation["category"] = category
        scored_recommendations.append(recommendation)

    recommendations = [
        item for item in scored_recommendations
        if item["match_score"] >= MIN_MATCH_SCORE
    ]

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
            "Try another interest or a more specific query."
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






