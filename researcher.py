
import os
import re
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

QLOO_BASE_URL = "https://hackathon.api.qloo.com"
TIMEOUT = 35
RESULT_LIMIT = 10

CATEGORY_TYPES = {
    "Movies": "urn:entity:movie",
    "Music": "urn:entity:artist",
    "Food": "urn:entity:place",
    "Travel": "urn:entity:destination",
}

CATEGORY_ALIASES = {
    "movie": "Movies",
    "movies": "Movies",
    "film": "Movies",
    "films": "Movies",
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

FOOD_TERMS = {
    "indian": {
        "indian", "india", "indian cuisine", "south indian",
        "north indian", "punjabi", "bengali", "gujarati",
        "rajasthani", "tamil", "kerala"
    },
    "street food": {
        "street food", "chaat", "pani puri", "golgappa",
        "samosa", "pakora", "vada pav", "pav bhaji",
        "bhel puri", "kathi roll", "street snacks"
    },
    "pizza": {"pizza", "pizzeria", "wood-fired pizza"},
    "sushi": {"sushi", "sashimi", "japanese cuisine"},
    "vegan": {"vegan", "plant-based"},
    "vegetarian": {"vegetarian", "vegetarian cuisine"},
    "seafood": {"seafood", "fish dishes", "shellfish"},
    "chinese": {"chinese cuisine", "szechuan", "dim sum"},
    "mexican": {"mexican cuisine", "tacos", "burritos"},
}

FOOD_METADATA_FIELDS = (
    "name",
    "title",
    "description",
    "short_description",
    "cuisine_description",
    "specialty_dishes",
    "keywords",
    "tags",
    "primary_genre",
    "overall_description",
    "good_for",
    "service_description",
    "unique_selling_points",
    "categories",
    "category",
    "type",
)

LODGING_TERMS = {
    "hotel", "resort", "hostel", "accommodation",
    "guesthouse", "guest house", "motel", "holiday rental",
    "vacation rental", "beach resort", "inn and suites",
}

FOOD_TERMS_STRONG = {
    "restaurant", "cafe", "café", "eatery", "diner",
    "food stall", "street food", "food truck", "food court",
    "bakery", "pizzeria", "bistro", "canteen",
    "cuisine", "specialty dishes", "menu",
}


def normalize_text(value: Any) -> str:
    """Convert nested metadata into searchable text safely."""
    if value is None:
        return ""

    if isinstance(value, dict):
        return " ".join(
            f"{normalize_text(key)} {normalize_text(item)}"
            for key, item in value.items()
        )

    if isinstance(value, (list, tuple, set)):
        return " ".join(normalize_text(item) for item in value)

    return str(value).lower().replace("_", " ").strip()


def split_interests(interests: Any) -> list[str]:
    """Normalize a string or list of interests into phrases."""
    if isinstance(interests, str):
        raw = re.split(r"[,;\n]+", interests)
    elif isinstance(interests, (list, tuple, set)):
        raw = []
        for item in interests:
            if isinstance(item, str):
                raw.extend(re.split(r"[,;\n]+", item))
            elif item is not None:
                raw.append(str(item))
    else:
        raw = []

    phrases = []
    seen = set()

    for item in raw:
        phrase = " ".join(item.lower().split()).strip()
        if phrase and phrase not in seen:
            phrases.append(phrase)
            seen.add(phrase)

    return phrases


def detect_category(value: str) -> str | None:
    """Resolve common category aliases."""
    text = (value or "").strip().lower()
    return CATEGORY_ALIASES.get(text)


def get_entity_properties(entity: dict) -> dict:
    properties = entity.get("properties")
    return properties if isinstance(properties, dict) else {}


def entity_text(entity: dict) -> str:
    """Flatten entity fields and nested properties into searchable text."""
    parts = [
        entity.get("name"),
        entity.get("title"),
        entity.get("description"),
        entity.get("short_description"),
        entity.get("type"),
    ]

    properties = get_entity_properties(entity)
    parts.append(properties)

    return normalize_text(parts)


def get_food_metadata_text(entity: dict) -> str:
    """Extract relevant food-related metadata from a Qloo place."""
    properties = get_entity_properties(entity)
    values = []

    for field in FOOD_METADATA_FIELDS:
        if field in entity:
            values.append(entity[field])
        if field in properties:
            values.append(properties[field])

    # Include entity-level names and descriptions.
    values.extend([
        entity.get("name"),
        entity.get("title"),
        entity.get("description"),
        entity.get("short_description"),
    ])

    return normalize_text(values)


def food_interest_terms(interests: list[str]) -> set[str]:
    """Expand known food interests without inventing results."""
    text = " ".join(interests).lower()
    terms = set()

    for interest, related_terms in FOOD_TERMS.items():
        if interest in text or any(term in text for term in related_terms):
            terms.update(related_terms)
            terms.add(interest)

    # Preserve substantive user-supplied phrases.
    for phrase in interests:
        if phrase not in {"food", "foods", "restaurant", "restaurants"}:
            terms.add(phrase)

    return terms


def filter_food_entities(
    entities: list[dict],
    interests: list[str],
) -> list[dict]:
    """
    Keep only places with evidence relevant to the requested food interest.

    Generic place/hotel metadata alone is not sufficient evidence.
    """
    accepted = []
    interest_terms = food_interest_terms(interests)
    query_text = " ".join(interests).lower()

    broad_food_query = query_text.strip() in {
        "food", "foods", "restaurants", "restaurant",
        "places to eat", "food places"
    }

    for entity in entities:
        name = str(entity.get("name") or entity.get("title") or "Unnamed entity")
        metadata = get_food_metadata_text(entity)
        properties = get_entity_properties(entity)

        # Search explicit food metadata separately from general place metadata.
        cuisine_text = normalize_text([
            properties.get("cuisine_description"),
            properties.get("specialty_dishes"),
            properties.get("primary_genre"),
            properties.get("menu_url"),
            properties.get("keywords"),
            properties.get("tags"),
            entity.get("cuisine_description"),
            entity.get("specialty_dishes"),
        ])

        lodging_text = normalize_text([
            entity.get("name"),
            entity.get("description"),
            properties.get("hotel_class"),
            properties.get("number_of_rooms"),
            properties.get("check_in_time"),
            properties.get("check_out_time"),
            properties.get("amenities_description"),
        ])

        lodging_signals = any(
            term in lodging_text for term in LODGING_TERMS
        )

        interest_matches = [
            term for term in interest_terms
            if len(term) >= 3 and term in cuisine_text
        ]

        explicit_food_evidence = any(
            term in cuisine_text
            for term in FOOD_TERMS_STRONG
        )

        # A lodging entity is only eligible when its own food metadata
        # independently supports the user's requested cuisine or dish.
        if lodging_signals and not interest_matches:
            logger.info(
                "FOOD FILTER REJECT: name=%r reason=lodging_without_interest_match",
                name[:100],
            )
            continue

        if interest_matches:
            accepted.append(entity)
            logger.info(
                "FOOD FILTER ACCEPT: name=%r matched=%s",
                name[:100],
                interest_matches[:5],
            )
            continue

        if broad_food_query and explicit_food_evidence and not lodging_signals:
            accepted.append(entity)
            logger.info(
                "FOOD FILTER ACCEPT: name=%r reason=food_metadata",
                name[:100],
            )
            continue

        logger.info(
            "FOOD FILTER REJECT: name=%r reason=insufficient_food_evidence",
            name[:100],
        )

    logger.info(
        "FOOD FILTER SUMMARY: input=%d accepted=%d rejected=%d",
        len(entities),
        len(accepted),
        len(entities) - len(accepted),
    )

    return accepted


def qloo_headers() -> dict:
    api_key = os.getenv("QLOO_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("QLOO_API_KEY environment variable is missing.")

    return {
        "X-Api-Key": api_key,
        "Accept": "application/json",
    }


def qloo_get(path: str, params: dict) -> dict:
    """Make a Qloo request and return its JSON response."""
    url = f"{QLOO_BASE_URL}{path}"

    try:
        response = requests.get(
            url,
            headers=qloo_headers(),
            params=params,
            timeout=TIMEOUT,
        )

        logger.info(
            "QLOO REQUEST: path=%s status=%s",
            path,
            response.status_code,
        )

        response.raise_for_status()
        data = response.json()

        return data if isinstance(data, dict) else {}

    except requests.Timeout:
        logger.warning("QLOO TIMEOUT: path=%s timeout=%ss", path, TIMEOUT)
        return {"_error": "timeout"}

    except requests.RequestException as exc:
        logger.warning(
            "QLOO REQUEST ERROR: path=%s error=%s",
            path,
            str(exc)[:250],
        )
        return {"_error": "request_failed"}

    except ValueError:
        logger.warning("QLOO INVALID JSON: path=%s", path)
        return {"_error": "invalid_json"}


def extract_entities(data: dict) -> list[dict]:
    """Handle common Qloo response shapes."""
    if not isinstance(data, dict):
        return []

    results = data.get("results", {})

    if isinstance(results, list):
        return [item for item in results if isinstance(item, dict)]

    if isinstance(results, dict):
        entities = results.get("entities", [])
        if isinstance(entities, list):
            return [item for item in entities if isinstance(item, dict)]

    entities = data.get("entities", [])
    if isinstance(entities, list):
        return [item for item in entities if isinstance(item, dict)]

    return []


def search_tag(query: str, category: str) -> list[dict]:
    data = qloo_get(
        "/v2/tags",
        {
            "filter.query": query,
            "take": 20,
        },
    )

    tags = extract_entities(data)
    if not tags:
        results = data.get("results", {})
        if isinstance(results, dict):
            raw_tags = results.get("tags", [])
            if isinstance(raw_tags, list):
                tags = [tag for tag in raw_tags if isinstance(tag, dict)]

    query_normalized = " ".join(query.lower().split())
    exact = []

    for tag in tags:
        name = str(tag.get("name", "")).lower().strip()
        if name == query_normalized:
            exact.append(tag)

    if exact:
        logger.info(
            "QLOO TAG MATCH: category=%s name=%r",
            category,
            query,
        )
        return exact

    return tags[:5]


def search_entity(query: str, category: str) -> list[dict]:
    entity_type = CATEGORY_TYPES.get(category)

    params = {
        "query": query,
        "take": RESULT_LIMIT,
    }

    if entity_type:
        params["types"] = entity_type

    data = qloo_get("/search", params)
    entities = extract_entities(data)

    logger.info(
        "QLOO ENTITY SEARCH: category=%s query=%r count=%d",
        category,
        query,
        len(entities),
    )

    return entities


def get_insights(
    category: str,
    tags: list[dict] | None = None,
    entities: list[dict] | None = None,
) -> list[dict]:
    """Retrieve Qloo cultural insights for tag/entity signals."""
    tags = tags or []
    entities = entities or []

    params = {
        "filter.type": CATEGORY_TYPES[category],
        "take": RESULT_LIMIT,
    }

    tag_ids = [
        str(tag.get("id"))
        for tag in tags
        if tag.get("id")
    ]

    entity_ids = [
        str(entity.get("entity_id") or entity.get("id"))
        for entity in entities
        if entity.get("entity_id") or entity.get("id")
    ]

    if tag_ids:
        for index, tag_id in enumerate(tag_ids):
            params[f"signal.interests.tags[{index}]"] = tag_id

    if entity_ids:
        for index, entity_id in enumerate(entity_ids):
            params[f"signal.interests.entities[{index}]"] = entity_id

    logger.info(
        "QLOO INSIGHTS REQUEST: category=%s tag_count=%d entity_count=%d",
        category,
        len(tag_ids),
        len(entity_ids),
    )

    data = qloo_get("/v2/insights", params)
    results = extract_entities(data)

    logger.info("QLOO INSIGHTS RESULT COUNT: %d", len(results))
    return results


def log_entity_diagnostics(
    entities: list[dict],
    category: str,
    method: str,
) -> None:
    """Log result metadata to help debug Qloo relevance."""
    logger.info(
        "QLOO DIAGNOSTICS: category=%s method=%s count=%d",
        category,
        method,
        len(entities),
    )

    for index, entity in enumerate(entities[:RESULT_LIMIT], start=1):
        properties = get_entity_properties(entity)
        name = entity.get("name") or entity.get("title") or "Unnamed"
        description = (
            entity.get("description")
            or entity.get("short_description")
            or properties.get("description")
            or ""
        )

        logger.info(
            "QLOO ENTITY %d: name=%r description=%r",
            index,
            str(name)[:120],
            str(description)[:240],
        )

        logger.info(
            "QLOO ENTITY %d METADATA: keys=%s cuisine=%r dishes=%r "
            "keywords=%r tags=%r",
            index,
            list(properties.keys())[:35],
            str(properties.get("cuisine_description", ""))[:180],
            str(properties.get("specialty_dishes", ""))[:180],
            str(properties.get("keywords", ""))[:180],
            str(properties.get("tags", ""))[:180],
        )


def research_cultural_data(
    interests: Any,
    category: str,
) -> dict:
    """
    Research cultural entities using Qloo.

    Response keys are maintained for downstream workflow compatibility:
    status, source, category, interests, search_phrases,
    retrieval_method, results, and message.
    """
    normalized_category = detect_category(category) or category

    if normalized_category not in CATEGORY_TYPES:
        return {
            "status": "error",
            "source": "Qloo",
            "category": normalized_category,
            "interests": interests,
            "search_phrases": [],
            "retrieval_method": "none",
            "results": [],
            "message": "Unsupported category.",
        }

    phrases = split_interests(interests)

    logger.info(
        "QLOO RESEARCH: category=%s phrases=%s",
        normalized_category,
        phrases,
    )

    if not phrases:
        return {
            "status": "no_results",
            "source": "Qloo",
            "category": normalized_category,
            "interests": interests,
            "search_phrases": [],
            "retrieval_method": "none",
            "results": [],
            "message": "Please provide at least one interest.",
        }

    all_results = []
    seen_ids = set()
    retrieval_method = "none"

    for phrase in phrases[:5]:
        tags = search_tag(phrase, normalized_category)

        # Prefer tag insights when a matching tag is available.
        results = get_insights(normalized_category, tags=tags) if tags else []

        if results:
            retrieval_method = "qloo_tag_insights"
        else:
            matching_entities = search_entity(phrase, normalized_category)

            if matching_entities:
                results = get_insights(
                    normalized_category,
                    entities=matching_entities[:3],
                )

                if results:
                    retrieval_method = "qloo_entity_insights"
                else:
                    # Preserve actual Qloo search entities if insights
                    # have no results; never manufacture recommendations.
                    results = matching_entities
                    retrieval_method = "qloo_entity_search"

        for entity in results:
            entity_id = (
                entity.get("entity_id")
                or entity.get("id")
                or entity.get("name")
                or entity.get("title")
            )

            if entity_id is None:
                entity_id = repr(entity)[:200]

            if entity_id not in seen_ids:
                seen_ids.add(entity_id)
                all_results.append(entity)

    # Always diagnose raw Qloo results before applying the Food filter.
    log_entity_diagnostics(
        all_results,
        normalized_category,
        retrieval_method,
    )

    filtered_results = all_results

    if normalized_category == "Food":
        filtered_results = filter_food_entities(all_results, phrases)

    if not filtered_results:
        message = (
            "Qloo returned places, but none had sufficient food or cuisine "
            "metadata for this interest. Try a specific dish or cuisine. "
            "No unverified matches were promoted."
            if normalized_category == "Food"
            else "Qloo did not return usable results for these interests."
        )

        return {
            "status": "no_results",
            "source": "Qloo",
            "category": normalized_category,
            "interests": interests,
            "search_phrases": phrases,
            "retrieval_method": retrieval_method,
            "results": [],
            "message": message,
        }

    return {
        "status": "success",
        "source": "Qloo",
        "category": normalized_category,
        "interests": interests,
        "search_phrases": phrases,
        "retrieval_method": retrieval_method,
        "results": filtered_results[:RESULT_LIMIT],
        "message": (
            f"Retrieved {len(filtered_results[:RESULT_LIMIT])} "
            f"Qloo results for {normalized_category}."
        ),
    }









