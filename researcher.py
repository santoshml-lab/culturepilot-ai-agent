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
    "Travel": "urn:entity:place",
}


def normalize_text(value: Any) -> str:
    """Convert a value to normalized searchable text."""
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        value = str(value)

    return re.sub(r"\s+", " ", str(value)).strip()


def split_interests(interests: Any) -> list[str]:
    """Convert user interests into a list of search phrases."""
    if isinstance(interests, str):
        values = re.split(r"[,;\n]+", interests)
    elif isinstance(interests, (list, tuple, set)):
        values = list(interests)
    else:
        values = [interests] if interests is not None else []

    phrases = []
    seen = set()

    for value in values:
        phrase = normalize_text(value)

        if not phrase:
            continue

        key = phrase.casefold()

        if key not in seen:
            seen.add(key)
            phrases.append(phrase)

    return phrases[:10]


def detect_category(category: Any) -> str:
    """Normalize a category supplied by the frontend."""
    value = normalize_text(category).casefold()

    aliases = {
        "movie": "Movies",
        "movies": "Movies",
        "film": "Movies",
        "films": "Movies",
        "music": "Music",
        "artist": "Music",
        "artists": "Music",
        "food": "Food",
        "foods": "Food",
        "restaurant": "Food",
        "restaurants": "Food",
        "travel": "Travel",
        "travelling": "Travel",
        "traveling": "Travel",
        "destination": "Travel",
        "destinations": "Travel",
    }

    return aliases.get(value, "")


def qloo_headers() -> dict[str, str]:
    """Build authenticated Qloo request headers."""
    api_key = os.getenv("QLOO_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "QLOO_API_KEY is missing from the backend environment."
        )

    return {
        "X-Api-Key": api_key,
        "Accept": "application/json",
    }


def qloo_get(
    endpoint: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Make a safe GET request to the Qloo API."""
    url = f"{QLOO_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"

    response = requests.get(
        url,
        headers=qloo_headers(),
        params=params,
        timeout=TIMEOUT,
    )

    if not response.ok:
        logger.warning(
            "Qloo request failed: endpoint=%s status=%s",
            endpoint,
            response.status_code,
        )
        response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Qloo returned invalid JSON for {endpoint}."
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Qloo returned an unexpected response format.")

    return payload


def extract_entities(payload: Any) -> list[dict[str, Any]]:
    """Extract entity dictionaries from common Qloo response shapes."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    for key in ("results", "entities", "items", "data"):
        value = payload.get(key)

        if isinstance(value, list):
            return [
                item for item in value
                if isinstance(item, dict)
            ]

        if isinstance(value, dict):
            nested = extract_entities(value)

            if nested:
                return nested

    return []


def get_entity_properties(entity: dict[str, Any]) -> dict[str, Any]:
    """Read entity properties without assuming one response shape."""
    properties = entity.get("properties", {})

    return properties if isinstance(properties, dict) else {}


def entity_id(entity: dict[str, Any]) -> str:
    properties = get_entity_properties(entity)

    for source in (entity, properties):
        for key in ("entity_id", "id", "qid"):
            value = source.get(key)

            if value:
                return normalize_text(value)

    return ""


def entity_name(entity: dict[str, Any]) -> str:
    properties = get_entity_properties(entity)

    for source in (entity, properties):
        for key in ("name", "title", "display_name"):
            value = source.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

    return ""


def entity_text(entity: dict[str, Any]) -> str:
    """Create text useful for deduplication and filtering."""
    properties = get_entity_properties(entity)

    parts = [
        entity_name(entity),
        normalize_text(entity.get("name")),
        normalize_text(entity.get("type")),
        normalize_text(entity.get("subtype")),
    ]

    for key in (
        "description",
        "short_description",
        "category",
        "genres",
        "location",
        "address",
        "country",
        "release_year",
    ):
        value = properties.get(key, entity.get(key))

        if value:
            parts.append(normalize_text(value))

    return " ".join(part for part in parts if part).casefold()


def filter_food_entities(
    entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep food-related place results when their type is known."""
    food_terms = (
        "restaurant",
        "food",
        "cafe",
        "café",
        "bakery",
        "cuisine",
        "dining",
        "barbecue",
        "street food",
    )

    filtered = []

    for entity in entities:
        properties = get_entity_properties(entity)

        description = " ".join(
            normalize_text(properties.get(key, entity.get(key)))
            for key in ("type", "subtype", "category", "description")
        ).casefold()

        # Keep results if Qloo has not provided enough metadata
        # to classify the place reliably.
        if not description.strip() or any(
            term in description for term in food_terms
        ):
            filtered.append(entity)

    return filtered


def search_tag(
    phrase: str,
    category: str,
) -> list[dict[str, Any]]:
    """Search Qloo tags for a phrase."""
    try:
        payload = qloo_get(
            "/v2/tags",
            {
                "filter.query": phrase,
                "take": RESULT_LIMIT,
            },
        )
        return extract_entities(payload)
    except (requests.RequestException, RuntimeError) as exc:
        logger.info("Qloo tag search unavailable: %s", exc)
        return []


def search_entity(
    phrase: str,
    category: str,
) -> list[dict[str, Any]]:
    """Search Qloo entities using the selected category."""
    entity_type = CATEGORY_TYPES.get(category)

    if not entity_type:
        return []

    payload = qloo_get(
        "/search",
        {
            "query": phrase,
            "types": entity_type,
            "take": RESULT_LIMIT,
        },
    )

    return extract_entities(payload)


def get_insights(
    category: str,
    entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Request related recommendations from Qloo Insights."""
    entity_type = CATEGORY_TYPES.get(category)

    if not entity_type:
        return []

    ids = []

    for entity in entities:
        identifier = entity_id(entity)

        if identifier and identifier not in ids:
            ids.append(identifier)

    if not ids:
        return []

    payload = qloo_get(
        "/v2/insights",
        {
            "filter.type": entity_type,
            "signal.interests.entities": ",".join(ids[:3]),
            "take": RESULT_LIMIT,
        },
    )

    return extract_entities(payload)


def log_entity_diagnostics(
    entities: list[dict[str, Any]],
    category: str,
) -> None:
    """Log result counts without exposing API credentials."""
    logger.info(
        "CulturePilot research: category=%s result_count=%d",
        category,
        len(entities),
    )


def research_cultural_data(
    interests: Any,
    category: str,
) -> dict[str, Any]:
    """
    Research cultural interests using Qloo search and insights.

    Returns a dictionary for the existing backend workflow.
    """
    normalized_category = detect_category(category)
    phrases = split_interests(interests)

    if not normalized_category:
        return {
            "source": "qloo",
            "category": normalize_text(category),
            "interests": phrases,
            "search_phrases": phrases,
            "status": "error",
            "retrieval_method": [],
            "results": [],
            "message": "Unsupported category.",
        }

    if not phrases:
        return {
            "source": "qloo",
            "category": normalized_category,
            "interests": [],
            "search_phrases": [],
            "status": "error",
            "retrieval_method": [],
            "results": [],
            "message": "Please provide at least one interest.",
        }

    collected = []
    methods = []
    seen_ids = set()
    seen_names = set()
    errors = []

    def add_results(items: list[dict[str, Any]]) -> None:
        for item in items:
            identifier = entity_id(item)
            name = entity_name(item)

            if not identifier and not name:
                continue

            dedup_key = (
                identifier.casefold()
                if identifier
                else name.casefold()
            )

            if dedup_key in seen_ids or (
                name and name.casefold() in seen_names
            ):
                continue

            seen_ids.add(dedup_key)

            if name:
                seen_names.add(name.casefold())

            collected.append(item)

            if len(collected) >= RESULT_LIMIT:
                return

    for phrase in phrases:
        if len(collected) >= RESULT_LIMIT:
            break

        try:
            entities = search_entity(
                phrase,
                normalized_category,
            )

            if entities:
                methods.append("entity_search")

                if normalized_category == "Food":
                    entities = filter_food_entities(entities)

                insights = get_insights(
                    normalized_category,
                    entities[:3],
                )

                if insights:
                    methods.append("entity_insights")
                    add_results(insights)

                # Search results are a fallback for categories other
                # than Travel. Travel must avoid unverified locations.
                elif normalized_category != "Travel":
                    add_results(entities)

        except (
            requests.RequestException,
            RuntimeError,
            ValueError,
        ) as exc:
            logger.warning(
                "Qloo research failed for one search phrase: %s",
                exc,
            )
            errors.append(type(exc).__name__)
            continue

    log_entity_diagnostics(collected, normalized_category)

    if collected:
        status = "success"
        message = "Cultural recommendations retrieved from Qloo."
    elif errors:
        status = "error"
        message = (
            "Qloo research could not be completed. "
            "Check the API key, endpoint access, and backend logs."
        )
    else:
        status = "empty"
        message = (
            "No suitable results were returned. "
            "Try a more specific interest."
        )

    return {
        "source": "qloo",
        "category": normalized_category,
        "interests": phrases,
        "search_phrases": phrases,
        "status": status,
        "retrieval_method": list(dict.fromkeys(methods)),
        "results": collected[:RESULT_LIMIT],
        "message": message,
        }



                






    












