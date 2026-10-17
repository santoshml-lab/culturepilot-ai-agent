
import re

RESULT_LIMIT = 10

SUPPORTED_CATEGORIES = {
    "Movies", "Music", "Food", "Travel"
}

# These are category signals, not claims about any particular entity.
CATEGORY_TERMS = {
    "Movies": {
        "movie", "film", "cinema", "science fiction", "sci fi",
        "sci-fi", "thriller", "comedy", "horror", "drama",
        "animation", "documentary", "fantasy", "action",
    },
    "Music": {
        "music", "song", "singer", "artist", "jazz", "indie",
        "indie rock", "indie pop", "rock", "pop", "classical",
        "hip hop", "electronic", "folk", "metal",
    },
    "Food": {
        "food", "cuisine", "restaurant", "street food",
        "indian food", "indian cuisine", "indian street food",
        "pizza", "pasta", "sushi", "vegan", "dessert",
        "bakery", "cafe", "coffee", "seafood",
    },
    "Travel": {
        "travel", "destination", "tourism", "mountain",
        "beach", "historical place", "nature", "adventure",
        "city break", "national park", "museum",
    },
}

STOP_WORDS = {
    "i", "love", "like", "enjoy", "prefer", "want", "recommend",
    "recommendation", "recommendations", "suggest", "me", "some",
    "please", "find", "show", "my", "next", "favorite", "favourite",
    "thing", "things", "for", "the", "and", "or", "with", "based",
    "on", "into", "interested", "in",
}


def normalize(value):
    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(item) for item in value)

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        str(value or "").casefold(),
    ).strip()


def get_properties(item):
    value = item.get("properties")
    return value if isinstance(value, dict) else {}


def get_text(value):
    if isinstance(value, str):
        return value

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, (list, tuple, set)):
        return " ".join(
            get_text(part) for part in value if part is not None
        )

    if isinstance(value, dict):
        preferred = (
            "name", "value", "label", "title",
            "description", "url",
        )
        parts = [
            get_text(value[key])
            for key in preferred
            if value.get(key) is not None
        ]

        return " ".join(parts) if parts else " ".join(
            get_text(part) for part in value.values()
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
    value = get_field(item, ["image", "images", "image_url"])

    if isinstance(value, list):
        value = value[0] if value else None

    if isinstance(value, dict):
        value = value.get("url") or value.get("src")

    if isinstance(value, str) and value.startswith("https://"):
        return value

    return None


def get_genres(item):
    value = get_field(item, ["genres", "genre", "tags", "categories"])

    if not value:
        return []

    if not isinstance(value, list):
        value = [value]

    return [
        get_text(part)
        for part in value
        if get_text(part)
    ]


def split_interests(interests):
    """Extract meaningful interest phrases without inventing interests."""
    text = str(interests or "").strip()

    text = re.sub(
        r"^\s*(i\s+)?(love|like|enjoy|prefer)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )

    parts = re.split(
        r"\s*(?:,|;|\band\b|\bor\b)\s*",
        text,
        flags=re.IGNORECASE,
    )

    cleaned = []

    for part in parts:
        phrase = part.strip(" .!?")
        phrase = re.sub(
            r"^(some|music|songs|movies|films)\s+",
            "",
            phrase,
            flags=re.IGNORECASE,
        )

        if phrase and normalize(phrase) not in {
            normalize(existing) for existing in cleaned
        }:
            cleaned.append(phrase)

    return cleaned or [text]


def get_interest_terms(interests):
    terms = []

    for phrase in interests:
        normalized = normalize(phrase)

        if not normalized:
            continue

        # Preserve the full phrase and its meaningful individual words.
        candidates = [normalized]
        candidates.extend(normalized.split())

        for candidate in candidates:
            if candidate in STOP_WORDS or len(candidate) < 3:
                continue
            if candidate not in terms:
                terms.append(candidate)

    return terms


def phrase_in_text(phrase, text):
    phrase = normalize(phrase)
    text = normalize(text)

    if not phrase or not text:
        return False

    # Word-boundary matching avoids accidental substring matches.
    return f" {phrase} " in f" {text} "


def get_entity_metadata(item):
    properties = get_properties(item)

    fields = {
        "title": get_field(item, ["name", "title"]),
        "description": get_field(
            item,
            [
                "short_description",
                "description",
                "overview",
                "disambiguation",
            ],
        ),
        "genres": get_field(item, ["genres", "genre"]),
        "tags": get_field(item, ["tags", "keywords", "themes"]),
        "categories": get_field(item, ["categories", "category"]),
        "properties_metadata": {
            key: properties.get(key)
            for key in (
                "akas", "genres", "tags", "keywords",
                "themes", "categories",
            )
            if properties.get(key) is not None
        },
    }

    return {
        key: get_text(value)
        for key, value in fields.items()
        if value is not None
    }


def score_recommendation(item, interests, category):
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
    metadata = get_entity_metadata(item)

    title_text = normalize(title)
    description_text = normalize(description)
    genre_text = normalize(genres)
    other_metadata_text = normalize({
        key: value
        for key, value in metadata.items()
        if key != "title"
    })

    matched_interests = []
    evidence_fields = []

    for interest in interests:
        interest_norm = normalize(interest)

        if not interest_norm:
            continue

        if phrase_in_text(interest_norm, title_text):
            matched_interests.append(interest)
            evidence_fields.append("title")
        elif phrase_in_text(interest_norm, genre_text):
            matched_interests.append(interest)
            evidence_fields.append("genres")
        elif phrase_in_text(interest_norm, description_text):
            matched_interests.append(interest)
            evidence_fields.append("description")
        elif phrase_in_text(interest_norm, other_metadata_text):
            matched_interests.append(interest)
            evidence_fields.append("metadata")

    # Category relevance is assessed separately from interest relevance.
    category_terms = CATEGORY_TERMS.get(category, set())
    all_metadata_text = normalize({
        "title": title_text,
        "description": description_text,
        "genres": genre_text,
        "metadata": other_metadata_text,
    })

    category_evidence = [
        term for term in category_terms
        if phrase_in_text(term, all_metadata_text)
    ]

    unique_evidence = list(dict.fromkeys(evidence_fields))
    unique_matches = list(dict.fromkeys(matched_interests))

    if not unique_evidence:
        score = 0
    elif "title" in unique_evidence:
        score = 95
    elif "genres" in unique_evidence:
        score = 90
    elif "description" in unique_evidence:
        score = 75
    else:
        score = 70

    # A match to the interest alone cannot compensate for a missing
    # category signal when metadata provides no evidence of the category.
    category_confirmed = bool(category_evidence)

    if score and not category_confirmed:
        score = min(score, 50)

    entity_id = item.get("entity_id") or item.get("id")

    if unique_matches:
        reason = (
            "Metadata matched: "
            + ", ".join(unique_matches)
            + ". Evidence fields: "
            + ", ".join(unique_evidence)
            + "."
        )
        method = "metadata_match"
    else:
        reason = (
            "No direct interest match was found in the available metadata. "
            "Qloo returned this entity, but its relevance is unconfirmed."
        )
        method = "qloo_cultural_insight"

    if not category_confirmed:
        reason += " Category relevance could not be confirmed from metadata."

    return {
        "title": str(title),
        "description": description or (
            "Description not supplied in the available Qloo response."
        ),
        "image_url": get_image_url(item),
        "genres": genres,
        "entity_id": entity_id,
        "source": "Qloo",
        "match_score": score,
        "match_reason": reason,
        "matched_interests": unique_matches,
        "category": category,
        "category_confirmed": category_confirmed,
        "recommendation_method": method,
    }


def create_recommendation_request(
    interests,
    category,
    plan=None,
    cultural_data=None,
):
    interests = str(interests or "").strip()
    category = (category or "").strip().title()

    if not interests:
        raise ValueError("Please provide at least one interest.")

    if category not in SUPPORTED_CATEGORIES:
        raise ValueError(
            "Category must be Movies, Music, Food, or Travel."
        )

    results = cultural_data or []
    recommendations = []

    for item in results:
        if not isinstance(item, dict):
            continue

        entity_id = item.get("entity_id") or item.get("id")
        if not entity_id:
            continue

        recommendation = score_recommendation(
            item,
            split_interests(interests),
            category,
        )

        # Do not assign an artificial fallback score to unsupported matches.
        # Keep only results with evidence for both the interest and category.
        if (
            recommendation["match_score"] < 60
            or not recommendation["matched_interests"]
            or not recommendation["category_confirmed"]
        ):
            continue

        recommendations.append(recommendation)

    recommendations.sort(
        key=lambda item: (
            item["match_score"],
            len(item["matched_interests"]),
        ),
        reverse=True,
    )

    recommendations = recommendations[:RESULT_LIMIT]

    if recommendations:
        status = "success"
        message = (
            f"{len(recommendations)} recommendations passed metadata "
            "relevance checks. Scores are app-calculated evidence scores, "
            "not official Qloo confidence scores."
        )
    else:
        status = "no_results"
        message = (
            "Qloo returned entities, but none passed the available "
            "interest and category metadata checks. Try a more specific "
            "interest. No unverified matches were promoted."
        )

    return {
        "interests": interests,
        "category": category,
        "plan_received": bool(plan),
        "recommendation_status": status,
        "recommendations": recommendations,
        "message": message,
    }








