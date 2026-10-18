
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


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(item) for item in value)

    if isinstance(value, dict):
        value = " ".join(
            str(item) for item in value.values()
            if item is not None
        )

    value = re.sub(r"[_\-/:]+", " ", str(value).lower())
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def split_interests(interests: Any) -> list[str]:
    if interests is None:
        return []

    values = (
        [str(x).strip() for x in interests]
        if isinstance(interests, (list, tuple, set))
        else re.split(r"[,;\n]+", str(interests))
    )

    output = []
    seen = set()

    for value in values:
        key = normalize_text(value)
        if key and key not in seen:
            output.append(value)
            seen.add(key)

    return output


def detect_category(value: Any) -> str:
    normalized = normalize_text(value)

    for category in CATEGORY_TYPES:
        if normalized == normalize_text(category):
            return category

    alias_map = {
        normalize_text(key): category
        for key, category in CATEGORY_ALIASES.items()
    }

    if normalized in alias_map:
        return alias_map[normalized]

    return "Movies"


def qloo_headers() -> dict[str, str]:
    key = os.getenv("QLOO_API_KEY", "").strip()
    headers = {"Accept": "application/json"}

    if key:
        headers["X-Api-Key"] = key

    return headers


def qloo_get(path: str, params: dict | None = None) -> dict:
    if not os.getenv("QLOO_API_KEY", "").strip():
        logger.error("QLOO_API_KEY is missing.")
        return {"_error": "missing_api_key"}

    try:
        response = requests.get(
            f"{QLOO_BASE_URL}{path}",
            headers=qloo_headers(),
            params=params or {},
            timeout=TIMEOUT,
        )

        if not response.ok:
            logger.error(
                "QLOO HTTP ERROR: path=%s status=%s body=%s",
                path,
                response.status_code,
                response.text[:500],
            )
            return {
                "_error": "request_failed",
                "_status_code": response.status_code,
            }

        payload = response.json()

        if not isinstance(payload, dict):
            return {"_error": "unexpected_response"}

        return payload

    except (requests.RequestException, ValueError) as exc:
        logger.error(
            "QLOO REQUEST FAILED: path=%s error=%s",
            path,
            str(exc)[:300],
        )
        return {"_error": "request_failed"}


def extract_entities(data: Any) -> list[dict]:
    """Read entity or tag arrays from common Qloo response shapes."""
    if not isinstance(data, dict) or data.get("_error"):
        return []

    results = data.get("results")

    if isinstance(results, list):
        return [x for x in results if isinstance(x, dict)]

    if isinstance(results, dict):
        for key in ("entities", "results", "items", "tags"):
            value = results.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]

    for key in ("entities", "items", "tags"):
        value = data.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]

    return []


def get_entity_properties(entity: dict) -> dict:
    value = entity.get("properties", {})
    return value if isinstance(value, dict) else {}


def entity_id(entity: dict) -> str:
    properties = get_entity_properties(entity)
    value = (
        entity.get("entity_id")
        or entity.get("id")
        or entity.get("tag_id")
        or properties.get("entity_id")
    )
    return str(value).strip() if value else ""


def entity_name(entity: dict) -> str:
    properties = get_entity_properties(entity)
    value = (
        entity.get("name")
        or entity.get("title")
        or properties.get("name")
        or entity.get("label")
    )
    return str(value).strip() if value else ""


def entity_text(entity: dict) -> str:
    properties = get_entity_properties(entity)
    fields = [
        entity_name(entity),
        entity.get("description"),
        entity.get("type"),
        entity.get("entity_type"),
        entity.get("category"),
        properties.get("description"),
        properties.get("short_description"),
        properties.get("genre"),
        properties.get("genres"),
        properties.get("keywords"),
        properties.get("tags"),
    ]
    return normalize_text(" ".join(
        normalize_text(x) for x in fields if x is not None
    ))


def filter_food_entities(entities: list[dict]) -> list[dict]:
    filtered = []

    for entity in entities:
        properties = get_entity_properties(entity)
        entity_type = normalize_text(
            entity.get("entity_type") or entity.get("type") or ""
        )
        metadata = normalize_text(" ".join(str(x) for x in [
            entity_name(entity),
            entity.get("description", ""),
            properties.get("description", ""),
            properties.get("category", ""),
            properties.get("subtype", ""),
            properties.get("cuisine", ""),
            properties.get("genres", ""),
            properties.get("tags", ""),
        ]))

        is_place = "place" in entity_type or "restaurant" in entity_type
        has_food_context = any(
            normalize_text(term) in metadata for term in FOOD_TERMS
        )

        if is_place or has_food_context:
            filtered.append(entity)

    return filtered


def search_tag(query: str, category: str) -> list[dict]:
    data = qloo_get(
        "/v2/tags",
        {"filter.query": query, "take": 20},
    )

    candidates = extract_entities(data)
    query_text = normalize_text(query)
    exact, partial = [], []

    for tag in candidates:
        name = normalize_text(entity_name(tag))
        tag_id = normalize_text(
            tag.get("tag_id") or tag.get("id") or ""
        )

        if not name:
            continue

        if category == "Travel":
            # Do not treat media, food or sports tags as destinations.
            if not any(
                marker in tag_id
                for marker in ("destination", "travel", "tourism")
            ):
                continue

        if name == query_text:
            exact.append(tag)
        elif query_text in name or name in query_text:
            partial.append(tag)

    selected = (exact + partial)[:5]

    logger.info(
        "QLOO TAG SEARCH: category=%s query=%s count=%d tags=%s",
        category,
        query,
        len(selected),
        [
            {"name": entity_name(x), "id": entity_id(x)}
            for x in selected
        ],
    )

    return selected


def search_entity(query: str, category: str) -> list[dict]:
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

    results = extract_entities(data)

    logger.info(
        "QLOO ENTITY SEARCH: category=%s query=%s count=%d names=%s",
        category,
        query,
        len(results),
        [entity_name(x) for x in results[:10]],
    )

    return results


def get_insights(
    category: str,
    tags: list[dict] | None = None,
    entities: list[dict] | None = None,
) -> list[dict]:
    category_type = CATEGORY_TYPES.get(category)
    if not category_type:
        return []

    tag_ids = list(dict.fromkeys(
        str(x.get("tag_id") or x.get("id"))
        for x in (tags or [])
        if isinstance(x, dict) and (x.get("tag_id") or x.get("id"))
    ))

    entity_ids = list(dict.fromkeys(
        entity_id(x)
        for x in (entities or [])
        if isinstance(x, dict) and entity_id(x)
    ))

    # Do not issue a broad, unanchored insights request.
    if not tag_ids and not entity_ids:
        logger.info(
            "QLOO INSIGHTS SKIPPED: no valid signal IDs for %s",
            category,
        )
        return []

    params = {
        "filter.type": category_type,
        "take": RESULT_LIMIT,
    }

    if tag_ids:
        params["signal.interests.tags"] = ",".join(tag_ids)

    if entity_ids:
        params["signal.interests.entities"] = ",".join(entity_ids)

    data = qloo_get("/v2/insights", params)
    results = extract_entities(data)

    logger.info(
        "QLOO INSIGHTS: category=%s count=%d names=%s",
        category,
        len(results),
        [entity_name(x) for x in results[:10]],
    )

    return results


def log_entity_diagnostics(entities: list[dict]) -> None:
    for entity in entities[:10]:
        properties = get_entity_properties(entity)
        logger.info(
            "QLOO ENTITY: name=%s id=%s type=%s keys=%s",
            entity_name(entity),
            entity_id(entity),
            entity.get("entity_type") or entity.get("type"),
            list(properties.keys())[:15],
        )


def research_cultural_data(
    interests: Any,
    category: str,
) -> dict:
    phrases = split_interests(interests)

    if category not in CATEGORY_TYPES:
        category = detect_category(category)

    base = {
        "source": "qloo",
        "category": category,
        "interests": phrases,
        "search_phrases": phrases,
    }

    if not phrases:
        return {
            **base,
            "status": "no_results",
            "retrieval_method": "none",
            "results": [],
            "message": "Please provide at least one interest.",
        }

    if not os.getenv("QLOO_API_KEY", "").strip():
        return {
            **base,
            "status": "error",
            "retrieval_method": "none",
            "results": [],
            "message": "QLOO_API_KEY is missing from the backend environment.",
        }

    collected = []
    methods = []
    seen = set()

    for phrase in phrases:
        logger.info(
            "QLOO RESEARCH START: category=%s phrase=%s",
            category,
            phrase,
        )

        # First: resolve the user's actual phrase to valid entities.
        # This is particularly important for Travel destinations.
        entities = search_entity(phrase, category)

        if entities:
            methods.append("entity_search")
            collected.extend(entities)

            insights = get_insights(
                category,
                entities=entities[:3],
            )

            if insights:
                methods.append("entity_insights")
                collected.extend(insights)

        # Tags can provide additional signals for non-Travel categories.
        # For Travel, don't let ambiguous country-name tags drive results.
        if category != "Travel":
            tags = search_tag(phrase, category)

            if tags:
                insights = get_insights(category, tags=tags)
                if insights:
                    methods.append("tag_insights")
                    collected.extend(insights)

        logger.info(
            "QLOO PHRASE COMPLETE: category=%s phrase=%s collected=%d",
            category,
            phrase,
            len(collected),
        )

    unique_results = []

    for entity in collected:
        if not isinstance(entity, dict):
            continue

        identifier = entity_id(entity) or entity_name(entity)
        key = normalize_text(identifier)

        if not key or key in seen:
            continue

        seen.add(key)
        unique_results.append(entity)

    if category == "Food":
        filtered = filter_food_entities(unique_results)
        if filtered:
            unique_results = filtered

    unique_results = unique_results[:RESULT_LIMIT]
    log_entity_diagnostics(unique_results)

    if unique_results:
        return {
            **base,
            "status": "success",
            "retrieval_method": ",".join(dict.fromkeys(methods)),
            "results": unique_results,
            "message": f"Retrieved {len(unique_results)} cultural entities.",
        }

    return {
        **base,
        "status": "no_results",
        "retrieval_method": ",".join(dict.fromkeys(methods)) or "none",
        "results": [],
        "message": (
            "Qloo returned no usable entities for these interests. "
            "Check the QLOO ENTITY SEARCH and QLOO INSIGHTS logs."
        ),
    }


                






    












