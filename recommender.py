import re
from typing import Any


RESULT_LIMIT = 10

SUPPORTED_CATEGORIES = {
    "movies": "Movies",
    "music": "Music",
    "food": "Food",
    "travel": "Travel",
}

CATEGORY_TERMS = {
    "Movies": [
        "movie", "film", "cinema", "actor", "actress",
        "director", "screenplay", "motion picture",
    ],
    "Music": [
        "music", "musical", "singer", "artist", "album",
        "song", "band", "musician", "composer", "genre",
    ],
    "Food": [
        "food", "cuisine", "restaurant", "street food",
        "dish", "dishes", "recipe", "cooking", "culinary",
        "snack", "snacks", "dessert", "bakery", "cafe",
        "coffee", "seafood", "pizza", "pasta", "sushi",
        "vegan", "vegetarian", "indian cuisine",
        "indian food", "indian street food",
        "specialty dishes", "speciality dishes",
    ],
    "Travel": [
        "travel", "destination", "tourism", "tourist",
        "vacation", "holiday", "landmark", "attraction",
        "island", "city", "country", "national park",
        "travel destination",
    ],
}

# Common words are excluded from individual-word matching.
STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this",
    "into", "about", "best", "good", "great", "some",
    "want", "like", "love", "recommend", "recommendations",
    "suggest", "suggestions", "please", "find", "show",
    "give", "tell", "explore", "discover", "popular",
    "famous", "type", "types", "things", "something",
    "near", "very", "more", "most", "which", "what",
}

# Specific phrase alternatives help with common cuisine queries.

INTEREST_SYNONYMS = {
    "indian street food": [
        "indian street food",
        "street food",
        "indian cuisine",
        "indian food",
        "street snacks",
    ],
    "indian food": [
        "indian food",
        "indian cuisine",
        "indian restaurant",
        "indian dishes",
    ],
    "street food": [
        "street food",
        "street snacks",
        "local snacks",
    ],
    "science fiction": [
        "science fiction",
        "sci-fi",
        "science-fiction",
    ],
    "sci-fi": [
        "sci-fi",
        "science fiction",
        "science-fiction",
    ],
    "indian classical": [
        "indian classical",
        "indian classical music",
        "hindustani classical",
        "carnatic music",
        "indian raga",
        "raga",
    ],
    "relaxing music": [
        "relaxing music",
        "relaxation music",
        "calm music",
        "soothing music",
        "ambient music",
        "meditative music",
        "instrumental music",
    ],
}


 


def normalize(value: Any) -> str:
    """Convert a value to normalized lowercase text."""
    if value is None:
        return ""

    if isinstance(value, (dict, list, tuple, set)):
        return ""

    text = str(value).lower().strip()
    text = text.replace("&", " and ")
    text = re.sub(r"[_/|-]+", " ", text)
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_properties(entity: dict) -> dict:
    """Safely retrieve Qloo entity properties."""
    if not isinstance(entity, dict):
        return {}

    properties = entity.get("properties", {})

    return properties if isinstance(properties, dict) else {}


def text_from_value(value: Any) -> str:
    """Extract searchable text from strings, lists, or Qloo tag objects."""
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, dict):
        parts = []

        for key in (
            "name",
            "value",
            "label",
            "description",
            "title",
            "id",
        ):
            item = value.get(key)

            if isinstance(item, (str, int, float)):
                parts.append(str(item))

        return " ".join(parts)

    if isinstance(value, (list, tuple, set)):
        return " ".join(
            text_from_value(item)
            for item in value
            if item is not None
        )

    return ""


def get_text(entity: dict, *keys: str) -> str:
    """Collect text from the entity and its properties."""
    if not isinstance(entity, dict):
        return ""

    properties = get_properties(entity)
    parts = []

    for key in keys:
        value = entity.get(key)

        if value is None:
            value = properties.get(key)

        extracted = text_from_value(value)

        if extracted:
            parts.append(extracted)

    return " ".join(parts)


def get_field(entity: dict, *keys: str) -> str:
    """Return the first available field as text."""
    if not isinstance(entity, dict):
        return ""

    properties = get_properties(entity)

    for key in keys:
        value = entity.get(key)

        if value is None:
            value = properties.get(key)

        extracted = text_from_value(value).strip()

        if extracted:
            return extracted

    return ""


def get_image_url(entity: dict) -> str | None:
    """Find an image URL if Qloo supplies one."""
    if not isinstance(entity, dict):
        return None

    properties = get_properties(entity)

    candidates = [
        entity.get("image"),
        entity.get("image_url"),
        entity.get("photo"),
        properties.get("image"),
        properties.get("image_url"),
        properties.get("photo"),
    ]

    for candidate in candidates:
        if isinstance(candidate, str):
            url = candidate.strip()

            if url.startswith(("https://", "http://")):
                return url

        if isinstance(candidate, dict):
            url = (
                candidate.get("url")
                or candidate.get("image_url")
                or candidate.get("src")
            )

            if isinstance(url, str) and url.startswith(
                ("https://", "http://")
            ):
                return url

    return None


def get_genres(entity: dict) -> list[str]:
    """Extract genre names from Qloo entity data."""
    if not isinstance(entity, dict):
        return []

    properties = get_properties(entity)
    raw_values = []

    for source in (entity, properties):
        for key in ("genres", "genre", "primary_genre"):
            value = source.get(key)

            if value is not None:
                raw_values.append(value)

    genres = []

    for value in raw_values:
        if isinstance(value, (list, tuple, set)):
            items = value
        else:
            items = [value]

        for item in items:
            genre = normalize(text_from_value(item))

            if genre and genre not in genres:
                genres.append(genre)

    return genres


def split_interests(interests: Any) -> list[str]:
    """Split a comma- or semicolon-separated interest string."""
    if isinstance(interests, (list, tuple, set)):
        raw_items = list(interests)
    else:
        raw_items = re.split(
            r"[,;\n]+",
            str(interests or ""),
        )

    result = []

    for item in raw_items:
        value = normalize(item)

        if value and value not in result:
            result.append(value)

    return result


def get_interest_terms(interests: Any) -> list[str]:
    """Return useful interest phrases and meaningful words."""
    phrases = split_interests(interests)
    terms = []

    for phrase in phrases:
        if phrase not in terms:
            terms.append(phrase)

        # Include explicit synonyms for known multiword interests.
        for original, alternatives in INTEREST_SYNONYMS.items():
            if phrase == original:
                for alternative in alternatives:
                    alternative = normalize(alternative)

                    if alternative and alternative not in terms:
                        terms.append(alternative)

        # Keep individual terms available for secondary matching.
        words = [
            word
            for word in phrase.split()
            if len(word) >= 4 and word not in STOP_WORDS
        ]

        for word in words:
            if word not in terms:
                terms.append(word)

    return terms


def phrase_in_text(phrase: str, text: str) -> bool:
    """Check a normalized phrase against normalized text."""
    phrase = normalize(phrase)
    text = normalize(text)

    if not phrase or not text:
        return False

    return f" {phrase} " in f" {text} "


def get_entity_metadata(entity: dict) -> dict:
    """
    Collect metadata useful for recommendation matching.

    Qloo may store important information in properties rather
    than at the top level, particularly for food entities.
    """
    if not isinstance(entity, dict):
        entity = {}

    properties = get_properties(entity)

    title = get_field(
        entity,
        "name",
        "title",
        "entity_name",
        "display_name",
    )

    description = get_field(
        entity,
        "description",
        "short_description",
        "overall_description",
        "overview",
        "summary",
    )

    # These fields are especially important for food relevance.
    metadata_keys = [
        "akas",
        "genres",
        "genre",
        "primary_genre",
        "tags",
        "keywords",
        "themes",
        "categories",
        "cuisine_description",
        "specialty_dishes",
        "speciality_dishes",
        "overall_description",
        "good_for",
        "menu_url",
        "food_type",
        "cuisine",
        "dish",
        "dishes",
        "location",
        "address",
        "known_for",
        "interests",
    ]

    metadata_parts = []

    for key in metadata_keys:
        value = entity.get(key)

        if value is None:
            value = properties.get(key)

        extracted = text_from_value(value)

        if extracted:
            metadata_parts.append(extracted)

    metadata_text = " ".join(metadata_parts)

    # Include the entity type when available.
    entity_type = get_field(
        entity,
        "entity_type",
        "type",
    )

    return {
        "title": title,
        "description": description,
        "genres": get_genres(entity),
        "metadata": metadata_text,
        "entity_type": normalize(entity_type),
        "all_text": normalize(
            " ".join(
                [
                    title,
                    description,
                    metadata_text,
                    entity_type,
                ]
            )
        ),
    }


def expand_interest(interest: str) -> list[str]:
    """Expand known phrases into useful alternatives."""
    normalized = normalize(interest)

    if not normalized:
        return []

    alternatives = [normalized]

    for original, synonyms in INTEREST_SYNONYMS.items():
        if normalized == normalize(original):
            alternatives.extend(synonyms)

    result = []

    for alternative in alternatives:
        value = normalize(alternative)

        if value and value not in result:
            result.append(value)

    return result


def match_interests(
    interests: Any,
    metadata: dict,
) -> tuple[list[str], int, list[str]]:
    """
    Match interests against entity information.

    Full phrases receive priority. Individual words are used
    only as secondary evidence, not as automatic confirmation
    of every multiword interest.
    """
    title = normalize(metadata.get("title", ""))
    description = normalize(metadata.get("description", ""))
    genres = normalize(" ".join(metadata.get("genres", [])))
    other_metadata = normalize(metadata.get("metadata", ""))
    all_text = normalize(metadata.get("all_text", ""))

    matched_interests = []
    matched_phrases = []
    score = 0

    for interest in split_interests(interests):
        alternatives = expand_interest(interest)

        title_match = any(
            phrase_in_text(phrase, title)
            for phrase in alternatives
        )

        genre_match = any(
            phrase_in_text(phrase, genres)
            for phrase in alternatives
        )

        description_match = any(
            phrase_in_text(phrase, description)
            for phrase in alternatives
        )

        metadata_match = any(
            phrase_in_text(phrase, other_metadata)
            for phrase in alternatives
        )

        if title_match:
            score += 95
            matched_interests.append(interest)
            matched_phrases.append(interest)
            continue

        if genre_match:
            score += 90
            matched_interests.append(interest)
            matched_phrases.append(interest)
            continue

        if description_match:
            score += 75
            matched_interests.append(interest)
            matched_phrases.append(interest)
            continue

        if metadata_match:
            score += 70
            matched_interests.append(interest)
            matched_phrases.append(interest)
            continue

        # Secondary matching: avoid treating one common word
        # as proof of relevance for a longer query.
        meaningful_words = [
            word
            for word in interest.split()
            if len(word) >= 4 and word not in STOP_WORDS
        ]

        if not meaningful_words:
            continue

        matched_words = [
            word
            for word in meaningful_words
            if phrase_in_text(word, all_text)
        ]

        # A multiword interest needs at least two matching
        # meaningful words, unless only one meaningful word
        # exists in the original query.
        required_matches = (
            1 if len(meaningful_words) == 1 else 2
        )

        if len(matched_words) >= required_matches:
            score += 55
            matched_interests.append(interest)
            matched_phrases.extend(matched_words)

    return (
        list(dict.fromkeys(matched_interests)),
        score,
        list(dict.fromkeys(matched_phrases)),
    )


def category_confirmed(
    category: str,
    metadata: dict,
) -> bool:
    """Check that the result contains evidence for its category."""
    normalized_category = normalize(category)

    category_name = next(
        (
            value
            for key, value in SUPPORTED_CATEGORIES.items()
            if key == normalized_category
        ),
        category,
    )

    all_text = normalize(metadata.get("all_text", ""))
    entity_type = normalize(metadata.get("entity_type", ""))

    if category_name not in CATEGORY_TERMS:
        return False

    # Music and movie entities often have reliable entity types.
    if category_name == "Movies":
        if "movie" in entity_type or "film" in entity_type:
            return True

    if category_name == "Music":
        if "artist" in entity_type or "music" in entity_type:
            return True

    if category_name == "Travel":
        if "destination" in entity_type:
            return True

    # A generic place entity is not enough to establish food
    # relevance: look for actual cuisine or food-related evidence.
    if category_name == "Food":
        food_evidence = [
            "cuisine_description",
            "specialty_dishes",
            "speciality_dishes",
            "food_type",
            "cuisine",
            "dish",
            "dishes",
            "menu_url",
            "restaurant",
            "street food",
            "indian food",
            "indian cuisine",
            "food",
            "culinary",
            "bakery",
            "seafood",
        ]

        food_text = normalize(
            " ".join(
                [
                    metadata.get("description", ""),
                    metadata.get("metadata", ""),
                    metadata.get("title", ""),
                ]
            )
        )

        return any(
            phrase_in_text(term, food_text)
            for term in food_evidence
        )

    return any(
        phrase_in_text(term, all_text)
        for term in CATEGORY_TERMS[category_name]
    )


def score_recommendation(
    entity: dict,
    interests: Any,
    category: str,
) -> dict | None:
    """
    Score one Qloo entity.

    Returns None if the result does not have sufficient evidence
    of both category relevance and interest relevance.
    """
    if not isinstance(entity, dict):
        return None

    metadata = get_entity_metadata(entity)

    entity_id = (
        entity.get("entity_id")
        or entity.get("id")
        or entity.get("entityId")
    )

    if not entity_id:
        return None

    is_category_confirmed = category_confirmed(
        category,
        metadata,
    )

    if not is_category_confirmed:
        return None

    matched_interests, raw_score, matched_phrases = (
        match_interests(interests, metadata)
    )

    if not matched_interests:
        return None

    # Avoid presenting a weak word-level match as a high-confidence
    # recommendation. Full phrase matches retain their higher scores.
    final_score = min(raw_score, 100)

    if final_score < 60:
        return None

    title = metadata.get("title") or "Untitled recommendation"
    description = metadata.get("description") or (
        "No description was provided by Qloo."
    )

    return {
        "id": str(entity_id),
        "entity_id": str(entity_id),
        "title": title,
        "name": title,
        "description": description,
        "category": category,
        "score": final_score,
        "matched_interests": matched_interests,
        "matched_terms": matched_phrases,
        "genres": metadata.get("genres", []),
        "image_url": get_image_url(entity),
        "source": "Qloo",
        "reason": (
            "Matched your interests using the entity's available "
            "description, genre, or metadata."
        ),
    }


def create_recommendation_request(
    interests: Any,
    category: str,
    plan: Any = None,
    cultural_data: Any = None,
) -> dict:
    """
    Create ranked recommendations from the researcher's Qloo results.

    This function keeps the signature expected by main.py:
    create_recommendation_request(
        interests, category, plan, cultural_data
    )
    """
    normalized_category = normalize(category)

    category_name = next(
        (
            value
            for key, value in SUPPORTED_CATEGORIES.items()
            if key == normalized_category
        ),
        str(category or "").strip(),
    )

    if category_name not in CATEGORY_TERMS:
        return {
            "status": "error",
            "recommendation_status": "no_results",
            "category": category_name,
            "interests": interests,
            "recommendations": [],
            "results": [],
            "count": 0,
            "message": (
                f"Unsupported category: {category_name}. "
                "Use Movies, Music, Food, or Travel."
            ),
        }

    if isinstance(cultural_data, dict):
        # Support callers that pass the entire research response.
        entities = cultural_data.get("results", [])
    elif isinstance(cultural_data, list):
        entities = cultural_data
    else:
        entities = []

    if not isinstance(entities, list):
        entities = []

    recommendations = []
    seen_ids = set()

    for entity in entities:
        if not isinstance(entity, dict):
            continue

        entity_id = (
            entity.get("entity_id")
            or entity.get("id")
            or entity.get("entityId")
        )

        if not entity_id:
            continue

        entity_key = str(entity_id)

        if entity_key in seen_ids:
            continue

        
        metadata = get_entity_metadata(entity)
        category_ok = category_confirmed(category_name, metadata)
        matched, match_score, matched_terms = match_interests(
    interests, metadata
)

print(
    "[MUSIC DEBUG]",
    {
        "title": metadata.get("title"),
        "entity_type": metadata.get("entity_type"),
        "category_ok": category_ok,
        "matched_interests": matched,
        "match_score": match_score,
        "genres": metadata.get("genres"),
    }
)


        recommendation = score_recommendation(
            entity=entity,
            interests=interests,
            category=category_name,
        )

        if recommendation is None:
            continue

        seen_ids.add(entity_key)
        recommendations.append(recommendation)

    recommendations.sort(
        key=lambda item: item.get("score", 0),
        reverse=True,
    )

    recommendations = recommendations[:RESULT_LIMIT]

    if recommendations:
        return {
            "status": "success",
            "recommendation_status": "success",
            "category": category_name,
            "interests": interests,
            "plan": plan,
            "recommendations": recommendations,
            "results": recommendations,
            "count": len(recommendations),
            "message": (
                f"Found {len(recommendations)} relevant "
                f"{category_name.lower()} recommendations."
            ),
            "source": "Qloo",
        }

    return {
        "status": "success",
        "recommendation_status": "no_results",
        "category": category_name,
        "interests": interests,
        "plan": plan,
        "recommendations": [],
        "results": [],
        "count": 0,
        "message": (
            "Qloo research returned no results that met the "
            "current category and interest relevance checks. "
            "Try a more specific or alternative search phrase."
        ),
        "source": "Qloo",
    }








