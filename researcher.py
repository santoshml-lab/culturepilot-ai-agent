
import re
from difflib import SequenceMatcher
from typing import Any

RESULT_LIMIT = 10

SUPPORTED_CATEGORIES = ("Movies", "Music", "Food", "Travel")

CATEGORY_ALIASES = {
    "movie": "Movies",
    "movies": "Movies",
    "film": "Movies",
    "films": "Movies",
    "cinema": "Movies",
    "music": "Music",
    "song": "Music",
    "songs": "Music",
    "artist": "Music",
    "food": "Food",
    "foods": "Food",
    "restaurant": "Food",
    "restaurants": "Food",
    "travel": "Travel",
    "destination": "Travel",
    "destinations": "Travel",
    "places": "Travel",
}

CATEGORY_TERMS = {
    "Movies": (
        "movie", "film", "cinema", "actor", "actress",
        "director", "filmmaker", "screenplay", "box office",
    ),
    "Music": (
        "music", "musician", "artist", "singer", "song",
        "album", "band", "composer", "recording artist",
    ),
    "Food": (
        "food", "restaurant", "cuisine", "dish", "cafe",
        "coffee", "pizza", "sushi", "biryani", "bakery",
        "dessert", "street food", "culinary",
    ),
    "Travel": (
        "destination", "tourism", "tourist attraction",
        "national park", "landmark", "city", "country",
        "island", "mountain", "historic site",
        "travel destination",
    ),
}

STOP_WORDS = {
    "a", "an", "and", "are", "at", "for", "from",
    "i", "in", "is", "it", "me", "my", "of", "on",
    "or", "the", "to", "with", "want", "like",
    "love", "enjoy", "interested", "interest",
}

INTEREST_SYNONYMS = {
    "sci fi": ("science fiction", "sci fi", "science-fiction"),
    "science fiction": ("science fiction", "sci fi"),
    "movies": ("movies", "films", "cinema"),
    "music": ("music", "songs", "artists"),
    "japan": ("japan", "japanese", "tokyo", "kyoto", "osaka"),
    "italy": ("italy", "italian", "rome", "venice", "florence"),
    "india": ("india", "indian", "delhi", "mumbai", "jaipur"),
    "france": ("france", "french", "paris", "lyon"),
    "food": ("food", "cuisine", "restaurants", "dishes"),
}

COUNTRY_ALIASES = {
    "japan": ("japan",),
    "italy": ("italy",),
    "india": ("india",),
    "france": ("france",),
    "spain": ("spain",),
    "germany": ("germany",),
    "united kingdom": (
        "united kingdom", "uk", "great britain",
    ),
    "united states": (
        "united states", "united states of america", "usa",
    ),
    "south korea": ("south korea", "republic of korea"),
    "thailand": ("thailand",),
    "china": ("china",),
    "indonesia": ("indonesia",),
    "australia": ("australia",),
    "canada": ("canada",),
    "brazil": ("brazil",),
    "mexico": ("mexico",),
    "singapore": ("singapore",),
    "nepal": ("nepal",),
    "switzerland": ("switzerland",),
    "greece": ("greece",),
    "portugal": ("portugal",),
    "turkey": ("turkey", "türkiye"),
    "vietnam": ("vietnam",),
    "malaysia": ("malaysia",),
    "new zealand": ("new zealand",),
}

MOVIE_FRANCHISES = {
    "star wars": ("star wars",),
    "harry potter": ("harry potter", "wizarding world"),
    "marvel": ("marvel", "mcu"),
    "dc": ("dc comics", "dc universe"),
    "jurassic park": ("jurassic park", "jurassic world"),
    "the lord of the rings": (
        "the lord of the rings", "the hobbit",
    ),
    "mission impossible": ("mission impossible",),
    "toy story": ("toy story",),
}

FOOD_DIVERSITY_GROUPS = {
    "pizza": ("pizza", "pizzeria"),
    "burger": ("burger", "hamburger"),
    "sushi": ("sushi", "japanese restaurant"),
    "biryani": ("biryani",),
    "coffee": ("coffee", "cafe", "espresso"),
    "bakery": ("bakery", "pastry", "bread"),
    "dessert": ("dessert", "ice cream", "cake", "patisserie"),
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, dict):
        value = " ".join(
            str(v) for v in value.values() if v is not None
        )
    elif isinstance(value, (list, tuple, set)):
        value = " ".join(str(v) for v in value)

    value = str(value).lower()
    value = re.sub(r"[_\-/\\:]+", " ", value)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def phrase_in_text(phrase: Any, text: Any) -> bool:
    phrase = normalize_text(phrase)
    text = normalize_text(text)

    if not phrase or not text:
        return False

    return re.search(
        r"(?<![a-z0-9])"
        + re.escape(phrase)
        + r"(?![a-z0-9])",
        text,
    ) is not None


def split_interests(interests: Any) -> list[str]:
    if interests is None:
        return []

    if isinstance(interests, (list, tuple, set)):
        values = [str(x).strip() for x in interests]
    else:
        values = re.split(r"[,;\n]+", str(interests))

    output = []
    seen = set()

    for value in values:
        key = normalize_text(value)
        if key and key not in seen:
            output.append(value.strip())
            seen.add(key)

    return output


def normalize_category(category: Any) -> str:
    value = normalize_text(category)

    for supported in SUPPORTED_CATEGORIES:
        if value == normalize_text(supported):
            return supported

    return {
        normalize_text(alias): target
        for alias, target in CATEGORY_ALIASES.items()
    }.get(value, "")


def get_entity_properties(entity: dict) -> dict:
    properties = entity.get("properties", {})
    return properties if isinstance(properties, dict) else {}


def get_nested_value(data: Any, *keys: str) -> Any:
    if not isinstance(data, dict):
        return None

    for key in keys:
        value = data.get(key)
        if value not in (None, "", [], {}):
            return value

    return None


def get_entity_name(entity: dict) -> str:
    properties = get_entity_properties(entity)

    value = (
        entity.get("name")
        or entity.get("title")
        or entity.get("label")
        or properties.get("name")
        or properties.get("title")
    )

    return str(value).strip() if value else ""


def get_entity_id(entity: dict) -> str:
    properties = get_entity_properties(entity)

    value = (
        entity.get("entity_id")
        or entity.get("id")
        or properties.get("entity_id")
        or properties.get("id")
    )

    return str(value).strip() if value else ""


def get_entity_metadata(entity: dict) -> dict:
    properties = get_entity_properties(entity)

    title = get_entity_name(entity)

    description = get_nested_value(
        entity, "description", "short_description", "overview"
    ) or get_nested_value(
        properties, "description", "short_description", "overview"
    ) or ""

    genres = (
        entity.get("genres")
        or properties.get("genres")
        or entity.get("genre")
        or properties.get("genre")
        or []
    )

    if not isinstance(genres, list):
        genres = [genres] if genres else []

    entity_type = (
        entity.get("entity_type")
        or entity.get("type")
        or properties.get("entity_type")
        or properties.get("type")
        or ""
    )

    metadata_parts = [
        entity.get("category"),
        entity.get("subtype"),
        entity.get("keywords"),
        entity.get("tags"),
        properties.get("category"),
        properties.get("subtype"),
        properties.get("keywords"),
        properties.get("tags"),
        properties.get("address"),
        properties.get("location"),
        properties.get("city"),
        properties.get("region"),
        properties.get("country"),
        properties.get("destination"),
    ]

    metadata = normalize_text(" ".join(
        normalize_text(x)
        for x in metadata_parts
        if x not in (None, "", [], {})
    ))

    all_text = normalize_text(" ".join([
        title,
        str(description),
        normalize_text(genres),
        metadata,
        str(entity_type),
    ]))

    return {
        "title": title,
        "description": str(description),
        "genres": genres,
        "metadata": metadata,
        "entity_type": normalize_text(entity_type),
        "all_text": all_text,
        "properties": properties,
    }


def get_verified_location_text(entity: dict) -> str:
    """
    Read location-specific fields only.

    Deliberately exclude the entity title and general description:
    a Japanese-themed venue outside Japan must not count as a
    destination located in Japan.
    """
    properties = get_entity_properties(entity)

    location_keys = (
        "country",
        "country_name",
        "country_code",
        "location",
        "address",
        "formatted_address",
        "city",
        "region",
        "state",
        "administrative_area",
        "destination",
        "geo",
        "geocode",
        "geocoding",
        "coordinates",
    )

    values = []

    for source in (entity, properties):
        for key in location_keys:
            value = source.get(key)
            if value not in (None, "", [], {}):
                values.append(normalize_text(value))

    # Handle common nested location objects.
    for source in (entity, properties):
        for key in ("location", "address", "geo", "geocoding"):
            value = source.get(key)

            if isinstance(value, dict):
                for nested_key in (
                    "country",
                    "country_name",
                    "country_code",
                    "city",
                    "region",
                    "state",
                    "address",
                    "formatted_address",
                    "name",
                ):
                    nested_value = value.get(nested_key)
                    if nested_value not in (None, "", [], {}):
                        values.append(normalize_text(nested_value))

    return normalize_text(" ".join(values))


def find_target_country(interests: Any) -> str:
    interest_text = normalize_text(interests)

    for country, aliases in COUNTRY_ALIASES.items():
        for alias in aliases:
            if phrase_in_text(alias, interest_text):
                return country

    return ""


def country_matches_location(country: str, location_text: str) -> bool:
    if not country or not location_text:
        return False

    aliases = COUNTRY_ALIASES.get(country, (country,))

    return any(
        phrase_in_text(alias, location_text)
        for alias in aliases
    )


def match_interests(
    interests: Any,
    metadata: dict,
    category: str = "",
) -> tuple[list[str], int, list[str]]:
    phrases = split_interests(interests)

    title = normalize_text(metadata.get("title", ""))
    description = normalize_text(metadata.get("description", ""))
    genres = normalize_text(metadata.get("genres", []))
    other_metadata = normalize_text(metadata.get("metadata", ""))

    matched = []
    reasons = []
    score = 0

    for phrase in phrases:
        query = normalize_text(phrase)

        if not query:
            continue

        alternatives = INTEREST_SYNONYMS.get(query, (query,))
        best_score = 0
        best_reason = ""

        for alternative in alternatives:
            alternative = normalize_text(alternative)

            if not alternative:
                continue

            if phrase_in_text(alternative, title):
                candidate_score = 95
                reason = f"Matches interest in the title: {phrase}"
            elif phrase_in_text(alternative, genres):
                candidate_score = 90
                reason = f"Matches the genre or style: {phrase}"
            elif phrase_in_text(alternative, description):
                candidate_score = 75
                reason = f"Matches the description: {phrase}"
            elif phrase_in_text(alternative, other_metadata):
                candidate_score = 70
                reason = f"Matches the metadata: {phrase}"
            else:
                words = [
                    word for word in query.split()
                    if word not in STOP_WORDS and len(word) > 2
                ]

                matched_words = [
                    word for word in words
                    if phrase_in_text(word, metadata.get("all_text", ""))
                ]

                if words and matched_words:
                    candidate_score = int(
                        55 * len(matched_words) / len(words)
                    )
                    reason = f"Partial interest match: {phrase}"
                else:
                    candidate_score = 0
                    reason = ""

            if candidate_score > best_score:
                best_score = candidate_score
                best_reason = reason

        if best_score:
            matched.append(phrase)
            score = max(score, best_score)
            reasons.append(best_reason)

    if matched and len(matched) > 1:
        score = min(100, score + 5 * (len(matched) - 1))

    return matched, score, reasons


def category_confirmed(category: str, metadata: dict) -> bool:
    category = normalize_category(category)

    if not category:
        return False

    entity_type = normalize_text(metadata.get("entity_type", ""))
    all_text = normalize_text(metadata.get("all_text", ""))

    if category == "Movies":
        movie_types = ("movie", "film", "cinema")
        if any(term in entity_type for term in movie_types):
            return True

    elif category == "Music":
        music_types = ("artist", "musical", "recording")
        if any(term in entity_type for term in music_types):
            return True

    elif category == "Food":
        food_types = ("restaurant", "food", "place", "venue", "cafe")
        if any(term in entity_type for term in food_types):
            return True

    elif category == "Travel":
        # A generic place is not sufficient evidence that it is a
        # destination relevant to the requested country.
        travel_types = (
            "destination",
            "tourist_attraction",
            "national_park",
            "point_of_interest",
            "locality",
            "country",
            "city",
            "region",
            "landmark",
            "place",
        )

        if not any(term in entity_type for term in travel_types):
            # Some Qloo place entities have no populated entity_type.
            # Continue only if there is travel-related evidence.
            travel_terms = CATEGORY_TERMS["Travel"]
            if not any(phrase_in_text(term, all_text) for term in travel_terms):
                return False

        # Actual country validation is performed in score_recommendation.
        return True

    return any(
        phrase_in_text(term, all_text)
        for term in CATEGORY_TERMS[category]
    )


def get_food_group(text: str) -> str:
    normalized = normalize_text(text)

    for group, terms in FOOD_DIVERSITY_GROUPS.items():
        if any(phrase_in_text(term, normalized) for term in terms):
            return group

    return ""


def get_movie_group(text: str) -> str:
    normalized = normalize_text(text)

    for group, terms in MOVIE_FRANCHISES.items():
        if any(phrase_in_text(term, normalized) for term in terms):
            return group

    return ""


def score_recommendation(
    entity: dict,
    interests: Any,
    category: str,
) -> dict | None:
    if not isinstance(entity, dict):
        return None

    category = normalize_category(category)

    if not category:
        return None

    metadata = get_entity_metadata(entity)
    title = metadata["title"]

    if not title:
        return None

    if not category_confirmed(category, metadata):
        return None

    if category == "Travel":
        # Only recommend a destination in the country requested.
        # Never infer country from the title or cultural description.
        target_country = find_target_country(interests)
        verified_location = get_verified_location_text(entity)

        if target_country:
            if not country_matches_location(
                target_country, verified_location
            ):
                return None
        elif not verified_location:
            # Without verifiable location, do not claim this is a
            # valid travel destination.
            return None

    matched, match_score, reasons = match_interests(
        interests, metadata, category
    )

    if not matched:
        return None

    description = metadata["description"]

    if not description:
        description = f"Explore {title} based on your interests."

    identifier = get_entity_id(entity)

    return {
        "id": identifier or normalize_text(title),
        "entity_id": identifier,
        "title": title,
        "name": title,
        "description": description,
        "category": category,
        "score": match_score,
        "match_score": match_score,
        "matched_interests": matched,
        "reasons": reasons,
        "entity_type": metadata["entity_type"],
        "source": "qloo",
        "metadata": metadata["metadata"],
        "location": get_verified_location_text(entity),
    }


def is_near_duplicate(first: str, second: str) -> bool:
    a = normalize_text(first)
    b = normalize_text(second)

    if not a or not b:
        return False

    if a == b or a in b or b in a:
        return True

    return SequenceMatcher(None, a, b).ratio() >= 0.90


def select_diverse_recommendations(
    recommendations: list[dict],
    category: str,
    limit: int = RESULT_LIMIT,
) -> list[dict]:
    ordered = sorted(
        recommendations,
        key=lambda item: item.get("score", 0),
        reverse=True,
    )

    selected = []
    seen_titles = set()
    seen_groups = set()

    for item in ordered:
        title = item.get("title", "")
        normalized_title = normalize_text(title)

        if not normalized_title or normalized_title in seen_titles:
            continue

        if any(
            is_near_duplicate(title, existing["title"])
            for existing in selected
        ):
            continue

        diversity_group = ""

        if category == "Movies":
            diversity_group = get_movie_group(title)

        elif category == "Food":
            diversity_group = get_food_group(
                title + " " + item.get("description", "")
            )

        # Prefer different franchises and food groups when possible.
        # If the list would otherwise be too short, a second pass below
        # can fill it with other non-duplicate recommendations.
        if diversity_group and diversity_group in seen_groups:
            continue

        selected.append(item)
        seen_titles.add(normalized_title)

        if diversity_group:
            seen_groups.add(diversity_group)

        if len(selected) >= limit:
            return selected

    # Fill remaining slots with valid recommendations not selected
    # during the diversity pass.
    for item in ordered:
        if len(selected) >= limit:
            break

        title = item.get("title", "")
        normalized_title = normalize_text(title)

        if not normalized_title or normalized_title in seen_titles:
            continue

        if any(
            is_near_duplicate(title, existing["title"])
            for existing in selected
        ):
            continue

        selected.append(item)
        seen_titles.add(normalized_title)

    return selected


def create_recommendation_request(
    interests: Any,
    category: str,
    plan: list | None = None,
    cultural_data: dict | list | None = None,
) -> dict:
    phrases = split_interests(interests)
    category_name = normalize_category(category)

    base = {
        "interests": ", ".join(phrases),
        "category": category_name or category,
        "plan_received": plan is not None,
        "plan": plan,
        "recommendation_status": "no_results",
        "status": "no_results",
        "recommendations": [],
        "results": [],
        "count": 0,
        "source": "qloo",
        "message": "",
    }

    if not phrases:
        return {
            **base,
            "status": "error",
            "recommendation_status": "error",
            "message": "Interests are required.",
        }

    if not category_name:
        return {
            **base,
            "status": "error",
            "recommendation_status": "error",
            "message": (
                "Unsupported category. Choose Movies, Music, Food, or Travel."
            ),
        }

    if isinstance(cultural_data, dict):
        raw_results = cultural_data.get("results", [])
        source = cultural_data.get("source", "qloo")
        research_status = cultural_data.get("status", "")
    elif isinstance(cultural_data, list):
        raw_results = cultural_data
        source = "qloo"
        research_status = ""
    else:
        raw_results = []
        source = "qloo"
        research_status = ""

    if not isinstance(raw_results, list):
        raw_results = []

    if not raw_results:
        message = (
            "Qloo returned no usable entities for these interests."
            if research_status != "error"
            else "The research step failed to retrieve cultural entities."
        )

        return {
            **base,
            "source": source,
            "status": research_status or "no_results",
            "recommendation_status": research_status or "no_results",
            "message": message,
        }

    scored = []

    for entity in raw_results:
        recommendation = score_recommendation(
            entity,
            phrases,
            category_name,
        )

        if recommendation is not None:
            scored.append(recommendation)

    recommendations = select_diverse_recommendations(
        scored,
        category_name,
        RESULT_LIMIT,
    )

    if not recommendations:
        message = (
            "No results passed relevance and location validation. "
            "For Travel, the destination's country must be verifiable "
            "from its location metadata."
        )

        return {
            **base,
            "source": source,
            "status": "no_results",
            "recommendation_status": "no_results",
            "message": message,
        }

    return {
        **base,
        "source": source,
        "status": "success",
        "recommendation_status": "success",
        "recommendations": recommendations,
        "results": recommendations,
        "count": len(recommendations),
        "message": (
            f"Found {len(recommendations)} relevant "
            f"{category_name.lower()} recommendations."
        ),
    }



                






    












