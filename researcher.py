
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

FOOD_TERMS = {
    "food", "restaurant", "restaurants", "cuisine", "cuisines",
    "dish", "dishes", "street food", "indian food", "italian food",
    "chinese food", "japanese food", "thai food", "mexican food",
    "korean food", "cafe", "cafes", "coffee", "pizza", "burger",
    "biryani", "sushi", "dessert", "desserts", "bakery",
    "bakery items",
}

CATEGORY_KEYWORDS = {
    "Movies": {
        "movie", "film", "cinema", "director", "actor", "actress",
        "science fiction", "sci-fi", "thriller", "drama", "comedy",
        "horror", "animation",
    },
    "Music": {
        "music", "song", "songs", "artist", "singer", "classical",
        "indian classical", "hindustani", "carnatic", "raga",
        "relaxing music", "ambient", "rock", "pop", "jazz",
        "hip hop", "instrumental",
    },
    "Food": FOOD_TERMS,
    "Travel": {
        "travel", "destination", "destinations", "tourism",
        "holiday", "vacation", "adventure", "beach", "mountain",
        "city", "museum", "nature",
    },
}


def normalize_text(value: Any) -> str:
    """Normalize text for consistent matching."""
    if value is None:
        return ""

    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(item) for item in value)

    if isinstance(value, dict):
        value = " ".join(
            str(item)
            for item in value.values()
            if item is not None
        )

    text = str(value).lower()
    text = re.sub(r"[_\-/:]+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_interests(interests: Any) -> list[str]:
    """Convert comma-separated or list-based interests into phrases."""
    if interests is None:
        return []

    if isinstance(interests, (list, tuple, set)):
        values = [str(item).strip() for item in interests]
    else:
        values = re.split(r"[,;\n]+", str(interests))

    output = []
    seen = set()

    for value in values:
        value = value.strip()
        key = normalize_text(value)

        if key and key not in seen:
            output.append(value)
            seen.add(key)

    return output


def detect_category(value: Any) -> str:
    """Detect a supported CulturePilot category."""
    normalized = normalize_text(value)

    if normalized in CATEGORY_TYPES:
        return normalized

    if normalized in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[normalized]

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(
            normalize_text(word) in normalized
            for word in keywords
        ):
            return category

    return "Movies"


def qloo_headers() -> dict[str, str]:
    """Create request headers without logging the API key."""
    api_key = os.getenv("QLOO_API_KEY", "").strip()

    headers = {"Accept": "application/json"}

    if api_key:
        headers["X-Api-Key"] = api_key

    return headers


def qloo_get(path: str, params: dict | None = None) -> dict:
    """Make a Qloo request and handle HTTP/API errors."""
    if not os.getenv("QLOO_API_KEY", "").strip():
        logger.error("QLOO_API_KEY environment variable is missing.")
        return {"_error": "missing_api_key"}

    url = f"{QLOO_BASE_URL}{path}"

    try:
        response = requests.get(
            url,
            headers=qloo_headers(),
            params=params or {},
            timeout=TIMEOUT,
        )

        if not response.ok:
            logger.error(
                "QLOO REQUEST ERROR: path=%s status=%s body=%s",
                path,
                response.status_code,
                response.text[:1000],
            )
            return {
                "_error": "request_failed",
                "_status_code": response.status_code,
            }

        try:
            payload = response.json()
        except ValueError:
            logger.error("QLOO returned invalid JSON for %s", path)
            return {"_error": "invalid_json"}

        if not isinstance(payload, dict):
            return {"_error": "unexpected_response"}

        return payload

    except requests.RequestException as exc:
        logger.error(
            "QLOO REQUEST EXCEPTION: path=%s error=%s",
            path,
            str(exc)[:500],
        )
        return {"_error": "request_failed"}


def extract_entities(data: Any) -> list[dict]:
    """Extract entity records from common Qloo response structures."""
    if not isinstance(data, dict) or data.get("_error"):
        return []

    results = data.get("results", [])

    if isinstance(results, list):
        return [item for item in results if isinstance(item, dict)]

    if isinstance(results, dict):
        for key in ("entities", "results", "items", "tags"):
            value = results.get(key)
            if isinstance(value, list):
                return [
                    item for item in value
                    if isinstance(item, dict)
                ]

    for key in ("entities", "items", "tags"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    return []


def get_entity_properties(entity: dict) -> dict:
    """Read entity properties safely."""
    properties = entity.get("properties", {})
    return properties if isinstance(properties, dict) else {}


def entity_text(entity: dict) -> str:
    """Build searchable text from available entity fields."""
    properties = get_entity_properties(entity)

    values = [
        entity.get("name"),
        entity.get("title"),
        entity.get("description"),
        entity.get("type"),
        entity.get("entity_type"),
        entity.get("category"),
        entity.get("subtype"),
        properties.get("name"),
        properties.get("description"),
        properties.get("short_description"),
        properties.get("genre"),
        properties.get("genres"),
        properties.get("keywords"),
        properties.get("tags"),
        properties.get("category"),
        properties.get("subtype"),
    ]

    return normalize_text(" ".join(
        normalize_text(value)
        for value in values
        if value is not None
    ))


def get_food_metadata_text(entity: dict) -> str:
    """Collect metadata used by the Food relevance filter."""
    properties = get_entity_properties(entity)

    values = [
        entity.get("name"),
        entity.get("title"),
        entity.get("description"),
        entity.get("type"),
        entity.get("category"),
        properties.get("description"),
        properties.get("short_description"),
        properties.get("category"),
        properties.get("subtype"),
        properties.get("cuisine"),
        properties.get("genres"),
        properties.get("tags"),
    ]

    return normalize_text(" ".join(
        normalize_text(value)
        for value in values
        if value is not None
    ))


def filter_food_entities(entities: list[dict]) -> list[dict]:
    """Prefer likely food/place entities."""
    filtered = []

    for entity in entities:
        if not isinstance(entity, dict):
            continue

        entity_type = normalize_text(
            entity.get("entity_type") or entity.get("type") or ""
        )
        metadata = get_food_metadata_text(entity)

        is_place = (
            "place" in entity_type
            or "restaurant" in entity_type
            or "urn entity place" in entity_type
        )

        has_food_context = any(
            normalize_text(term) in metadata
            for term in FOOD_TERMS
        )

        if is_place or has_food_context:
            filtered.append(entity)

    return filtered


def search_tag(query: str, category: str) -> list[dict]:
    """Search Qloo tags for an interest phrase."""
    data = qloo_get(
        "/v2/tags",
        {
            "filter.query": query,
            "take": 20,
        },
    )

    if not isinstance(data, dict) or data.get("_error"):
        return []

    candidates = extract_entities(data)

    if not candidates:
        results = data.get("results", {})
        if isinstance(results, dict):
            tags = results.get("tags", [])
            if isinstance(tags, list):
                candidates = [
                    item for item in tags
                    if isinstance(item, dict)
                ]

    query_text = normalize_text(query)
    exact = []
    partial = []

    for tag in candidates:
        name = normalize_text(
            tag.get("name")
            or tag.get("title")
            or tag.get("label")
        )
        print(
            "[QLOO TAG DEBUG]",
           {
         "query": query,
        "name": tag.get("name") or tag.get("title") or tag.get("label"),
        "id": tag.get("id"),
        "tag_id": tag.get("tag_id"),
        "entity_id": tag.get("entity_id"),
          },
          flush=True,
        )


        

        if not name:
            continue

        if name == query_text:
            exact.append(tag)
        elif query_text in name or name in query_text:
            partial.append(tag)
            selected_tags = (exact + partial)[:5]

            print(
                "[QLOO SELECTED TAGS]",
    [
        {
                "name": tag.get("name") or tag.get("title") or tag.get("label"),
                "id": tag.get("id"),
        }
        for tag in selected_tags
    ],
    flush=True,
)

    return selected_tags

    return (exact + partial)[:5]


def search_entity(query: str, category: str) -> list[dict]:
    """Search Qloo entities for a phrase and category."""
    category_type = CATEGORY_TYPES.get(category)

    if not category_type:
        return []

    data = qloo_get(
        "/search",
        {
            "query": query,
            "take": RESULT_LIMIT,
            "types": category_type,
        },
    )

    if not isinstance(data, dict) or data.get("_error"):
        return []

    return extract_entities(data)


def get_insights(
    category: str,
    tags: list[dict] | None = None,
    entities: list[dict] | None = None,
) -> list[dict]:
    """Request Qloo insights using tag/entity IDs."""
    category_type = CATEGORY_TYPES.get(category)

    if not category_type:
        return []

    tag_ids = list(dict.fromkeys(
        str(tag.get("id"))
        for tag in (tags or [])
        if isinstance(tag, dict) and tag.get("id")
    ))

    entity_ids = list(dict.fromkeys(
        str(entity.get("entity_id") or entity.get("id"))
        for entity in (entities or [])
        if isinstance(entity, dict)
        and (entity.get("entity_id") or entity.get("id"))
    ))

    params = {
        "filter.type": category_type,
        "take": RESULT_LIMIT,
    }

    if tag_ids:
        params["signal.interests.tags"] = ",".join(tag_ids)

    if entity_ids:
        params["signal.interests.entities"] = ",".join(entity_ids)

    data = qloo_get("/v2/insights", params)

    if not isinstance(data, dict) or data.get("_error"):
        logger.warning(
            "Qloo insights unavailable for category=%s",
            category,
        )
        return []

    return extract_entities(data)


def log_entity_diagnostics(entities: list[dict]) -> None:
    """Log limited entity metadata for debugging."""
    for entity in entities[:10]:
        properties = get_entity_properties(entity)

        logger.info(
            "QLOO ENTITY: name=%s type=%s keys=%s metadata_keys=%s",
            entity.get("name") or entity.get("title"),
            entity.get("entity_type") or entity.get("type"),
            list(entity.keys())[:20],
            list(properties.keys())[:20],
        )


def research_cultural_data(
    interests: Any,
    category: str,
) -> dict:
    """Retrieve cultural data, prioritizing interest-based Qloo insights."""
    phrases = split_interests(interests)

    if category not in CATEGORY_TYPES:
        category = detect_category(category)

    if not phrases:
        return {
            "status": "no_results",
            "source": "qloo",
            "category": category,
            "interests": [],
            "search_phrases": [],
            "retrieval_method": "none",
            "results": [],
            "message": "Please provide at least one interest.",
        }

    if not os.getenv("QLOO_API_KEY", "").strip():
        return {
            "status": "error",
            "source": "qloo",
            "category": category,
            "interests": phrases,
            "search_phrases": phrases,
            "retrieval_method": "none",
            "results": [],
            "message": "QLOO_API_KEY is missing from the backend environment.",
        }

    collected = []
    seen = set()
    methods = []

    for phrase in phrases:
        logger.info(
            "QLOO RESEARCH: category=%s phrase=%s",
            category,
            phrase,
        )

        # Step 1: Search for an interest tag.
        tags = search_tag(phrase, category)

        logger.info(
            "QLOO TAG SEARCH RESULTS: category=%s phrase=%s count=%s names=%s",
            category,
            phrase,
            len(tags),
            [
                tag.get("name") or tag.get("title") or tag.get("label")
                for tag in tags[:10]
            ],
        )

        # Step 2: If tags exist, prioritize their insights.
        tag_results = []

        if tags:
            tag_results = get_insights(category, tags=tags)

            logger.info(
                "QLOO TAG INSIGHTS RESULTS: category=%s phrase=%s count=%s names=%s",
                category,
                phrase,
                len(tag_results),
                [
                    item.get("name") or item.get("title")
                    for item in tag_results[:10]
                ],
            )

            if tag_results:
                methods.append("tag_insights")
                collected.extend(tag_results)

        # Step 3: Only use entity search when tag insights
        # did not return results. This avoids mixing broad
        # entity-search results into successful tag insights.
        if not tag_results:
            search_results = search_entity(phrase, category)

            logger.info(
                "QLOO ENTITY SEARCH RESULTS: category=%s phrase=%s count=%s names=%s",
                category,
                phrase,
                len(search_results),
                [
                    item.get("name") or item.get("title")
                    for item in search_results[:10]
                ],
            )

            if search_results:
                methods.append("entity_search")
                collected.extend(search_results)

                # Use entity-based insights as an additional fallback.
                insight_results = get_insights(
                    category,
                    entities=search_results[:3],
                )

                logger.info(
                    "QLOO ENTITY INSIGHTS RESULTS: category=%s phrase=%s count=%s names=%s",
                    category,
                    phrase,
                    len(insight_results),
                    [
                        item.get("name") or item.get("title")
                        for item in insight_results[:10]
                    ],
                )

                if insight_results:
                    methods.append("entity_insights")
                    collected.extend(insight_results)

    # Step 4: Deduplicate returned entities.
    unique_results = []

    for entity in collected:
        if not isinstance(entity, dict):
            continue

        properties = get_entity_properties(entity)

        entity_id = (
            entity.get("entity_id")
            or entity.get("id")
            or entity.get("name")
            or entity.get("title")
            or properties.get("name")
        )

        if not entity_id:
            continue

        key = normalize_text(entity_id)

        if not key or key in seen:
            continue

        seen.add(key)
        unique_results.append(entity)

    # Step 5: Preserve the existing Food filtering behavior.
    if category == "Food":
        food_results = filter_food_entities(unique_results)

        if food_results:
            unique_results = food_results

    unique_results = unique_results[:RESULT_LIMIT]
    log_entity_diagnostics(unique_results)

    if unique_results:
        return {
            "status": "success",
            "source": "qloo",
            "category": category,
            "interests": phrases,
            "search_phrases": phrases,
            "retrieval_method": (
                ",".join(dict.fromkeys(methods))
                if methods
                else "fallback_search"
            ),
            "results": unique_results,
            "message": (
                f"Retrieved {len(unique_results)} cultural entities."
            ),
        }

    return {
        "status": "no_results",
        "source": "qloo",
        "category": category,
        "interests": phrases,
        "search_phrases": phrases,
        "retrieval_method": (
            ",".join(dict.fromkeys(methods))
            if methods
            else "none"
        ),
        "results": [],
        "message": (
            "Qloo returned no usable entities. "
            "Check Render logs for API errors and response details."
        ),
    }






    












