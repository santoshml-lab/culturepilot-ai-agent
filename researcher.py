
import os
import re
import logging
import requests

QLOO_BASE_URL = "https://hackathon.api.qloo.com"
TIMEOUT = 20
RESULT_LIMIT = 10
DESCRIPTION_LIMIT = 250

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    "artist": "Music",
    "artists": "Music",
    "food": "Food",
    "restaurant": "Food",
    "restaurants": "Food",
    "travel": "Travel",
    "destination": "Travel",
    "destinations": "Travel",
}

CATEGORY_SEARCH_HINTS = {
    "Movies": [
        "science fiction",
        "comedy",
        "horror",
        "thriller",
        "romance",
        "drama",
        "action",
        "animation",
        "documentary",
        "fantasy",
    ],
    "Music": [
        "jazz",
        "indie rock",
        "indie pop",
        "pop music",
        "rock music",
        "classical music",
        "hip hop",
        "electronic music",
    ],
    "Food": [
        "Indian cuisine",
        "Indian street food",
        "street food",
        "Italian cuisine",
        "Japanese cuisine",
        "vegan food",
    ],
    "Travel": [
        "mountain destinations",
        "beaches",
        "historical destinations",
        "adventure travel",
        "nature destinations",
    ],
}


def normalize(value):
    """Normalize text for reliable comparisons."""
    return " ".join(str(value or "").casefold().split())


def normalize_category(category):
    """Normalize a supported category name."""
    value = normalize(category)
    return CATEGORY_ALIASES.get(
        value,
        category if category in CATEGORY_TYPES else None,
    )


def split_interests(interests):
    """Split a natural-language request into useful search phrases."""
    text = str(interests or "").strip()

    text = re.sub(
        r"^\s*(i\s+)?(love|like|enjoy|prefer)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^\s*(recommend|suggest)\s+(me\s+)?(some\s+)?",
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
            r"^(some|songs|movies|films)\s+",
            "",
            phrase,
            flags=re.IGNORECASE,
        )

        if phrase and normalize(phrase) not in {
            normalize(item) for item in cleaned
        }:
            cleaned.append(phrase)

    return cleaned or [text]


def extract_tags(payload):
    """Read tag records from common Qloo response shapes."""
    if not isinstance(payload, dict):
        return []

    results = payload.get("results", {})

    if isinstance(results, dict):
        tags = results.get("tags", [])
        if isinstance(tags, list):
            return tags

    data = payload.get("data", {})

    if isinstance(data, dict):
        tags = data.get("tags", [])
        if isinstance(tags, list):
            return tags

    if isinstance(results, list):
        return results

    return []


def extract_entities(payload):
    """Read entity records from common Qloo response shapes."""
    if not isinstance(payload, dict):
        return []

    results = payload.get("results", {})

    if isinstance(results, dict):
        entities = results.get("entities", [])
        if isinstance(entities, list):
            return entities

    data = payload.get("data", {})

    if isinstance(data, dict):
        entities = data.get("entities", [])
        if isinstance(entities, list):
            return entities

    return []


def get_tag_id(tag):
    if not isinstance(tag, dict):
        return None

    return (
        tag.get("id")
        or tag.get("tag_id")
        or tag.get("entity_id")
    )


def get_entity_id(entity):
    if not isinstance(entity, dict):
        return None

    return entity.get("entity_id") or entity.get("id")


def entity_text(entity):
    """Build searchable text from available entity metadata."""
    if not isinstance(entity, dict):
        return ""

    parts = [
        entity.get("name"),
        entity.get("title"),
        entity.get("description"),
        entity.get("short_description"),
    ]

    properties = entity.get("properties")

    if isinstance(properties, dict):
        parts.extend([
            properties.get("name"),
            properties.get("description"),
        ])

    return " ".join(
        str(part) for part in parts if part
    )


def log_entity_diagnostics(entities, category, retrieval_method):
    """
    Log limited metadata for debugging.
    Never log request headers or the Qloo API key.
    """
    logger.info(
        "QLOO DIAGNOSTICS: category=%s method=%s count=%s",
        category,
        retrieval_method,
        len(entities),
    )

    for index, entity in enumerate(entities[:RESULT_LIMIT], start=1):
        if not isinstance(entity, dict):
            logger.info(
                "QLOO ENTITY %s: unexpected record type=%s",
                index,
                type(entity).__name__,
            )
            continue

        properties = entity.get("properties")
        if not isinstance(properties, dict):
            properties = {}

        # Only inspect potentially useful metadata fields.
        metadata_fields = (
            "name",
            "description",
            "short_description",
            "genres",
            "tags",
            "categories",
            "keywords",
            "types",
            "category",
            "address",
            "country",
            "location",
        )

        selected_metadata = {}

        for key in metadata_fields:
            value = entity.get(key)

            if value is None:
                value = properties.get(key)

            if value is not None:
                selected_metadata[key] = str(value)[:DESCRIPTION_LIMIT]

        name = (
            entity.get("name")
            or entity.get("title")
            or properties.get("name")
            or "Unknown"
        )

        description = (
            entity.get("description")
            or entity.get("short_description")
            or properties.get("description")
            or ""
        )

        logger.info(
            "QLOO ENTITY %s: id=%s name=%r description=%r",
            index,
            str(get_entity_id(entity) or "")[:100],
            str(name)[:150],
            str(description)[:DESCRIPTION_LIMIT],
        )

        logger.info(
            "QLOO ENTITY %s METADATA: property_keys=%s selected=%s",
            index,
            sorted(str(key) for key in properties.keys()),
            selected_metadata,
        )


def search_tag(session, query, category):
    """Find a real Qloo tag; return None if no exact tag is found."""
    params = {
        "filter.query": query,
        "take": 20,
    }

    try:
        response = session.get(
            f"{QLOO_BASE_URL}/v2/tags",
            params=params,
            timeout=TIMEOUT,
        )

        logger.info(
            "QLOO TAG SEARCH: category=%s query=%r status=%s",
            category,
            query,
            response.status_code,
        )

        response.raise_for_status()
        payload = response.json()
        tags = extract_tags(payload)

        query_norm = normalize(query)

        for tag in tags:
            if not isinstance(tag, dict):
                continue

            name = normalize(
                tag.get("name") or tag.get("title")
            )
            tag_id = get_tag_id(tag)

            if name == query_norm and tag_id:
                logger.info(
                    "QLOO TAG MATCH: category=%s name=%r",
                    category,
                    name,
                )
                return str(tag_id)

        logger.info(
            "QLOO TAG MATCH: none for %r; records=%s",
            query,
            len(tags),
        )

    except (requests.RequestException, ValueError) as exc:
        logger.warning(
            "QLOO TAG SEARCH ERROR for %r: %s",
            query,
            exc,
        )

    return None


def search_entity(session, query, category):
    """Resolve a specific title, artist, or entity through Qloo."""
    params = {
        "query": query,
        "types": CATEGORY_TYPES[category],
        "take": RESULT_LIMIT,
    }

    try:
        response = session.get(
            f"{QLOO_BASE_URL}/search",
            params=params,
            timeout=TIMEOUT,
        )

        logger.info(
            "QLOO ENTITY SEARCH: category=%s query=%r status=%s",
            category,
            query,
            response.status_code,
        )

        response.raise_for_status()
        payload = response.json()

        results = payload.get("results", {})

        if isinstance(results, dict):
            entities = results.get("entities", [])
        elif isinstance(results, list):
            entities = results
        else:
            entities = []

        query_norm = normalize(query)

        for entity in entities:
            if not isinstance(entity, dict):
                continue

            name = normalize(
                entity.get("name") or entity.get("title")
            )
            entity_id = get_entity_id(entity)

            if name and entity_id and name == query_norm:
                logger.info(
                    "QLOO ENTITY MATCH: %s",
                    name,
                )
                return str(entity_id)

        logger.info(
            "QLOO ENTITY SEARCH: no exact match for %r",
            query,
        )

    except (requests.RequestException, ValueError) as exc:
        logger.warning(
            "QLOO ENTITY SEARCH ERROR for %r: %s",
            query,
            exc,
        )

    return None


def get_insights(session, category, tag_ids=None, entity_ids=None):
    """Ask Qloo for related entities using actual Qloo identifiers."""
    params = {
        "filter.type": CATEGORY_TYPES[category],
        "take": RESULT_LIMIT,
    }

    if tag_ids:
        params["signal.interests.tags"] = ",".join(tag_ids)

    if entity_ids:
        params["signal.interests.entities"] = ",".join(entity_ids)

    # IDs are safe to log; never log session headers or API credentials.
    logger.info(
        "QLOO INSIGHTS REQUEST: category=%s tag_count=%s entity_count=%s",
        category,
        len(tag_ids or []),
        len(entity_ids or []),
    )

    response = session.get(
        f"{QLOO_BASE_URL}/v2/insights",
        params=params,
        timeout=TIMEOUT,
    )

    logger.info(
        "QLOO INSIGHTS STATUS: %s",
        response.status_code,
    )

    response.raise_for_status()

    payload = response.json()
    entities = extract_entities(payload)

    logger.info(
        "QLOO INSIGHTS RESULT COUNT: %s",
        len(entities),
    )

    return entities


def research_cultural_data(interests, category):
    """Retrieve cultural data from Qloo and log limited diagnostics."""
    category = normalize_category(category)

    if category not in CATEGORY_TYPES:
        return {
            "status": "invalid_category",
            "source": "Qloo",
            "category": category,
            "interests": interests,
            "results": [],
            "message": "Choose Movies, Music, Food, or Travel.",
        }

    if not str(interests or "").strip():
        return {
            "status": "no_results",
            "source": "Qloo",
            "category": category,
            "interests": interests,
            "results": [],
            "message": "Please enter an interest to search.",
        }

    api_key = os.getenv("QLOO_API_KEY")

    if not api_key:
        logger.error("QLOO API KEY IS NOT CONFIGURED")

        return {
            "status": "api_error",
            "source": "Qloo",
            "category": category,
            "interests": interests,
            "results": [],
            "message": "QLOO_API_KEY is not configured on the backend.",
        }

    session = requests.Session()
    session.headers.update({
        "X-Api-Key": api_key,
        "Accept": "application/json",
    })

    phrases = split_interests(interests)

    logger.info(
        "QLOO RESEARCH: category=%s phrases=%s",
        category,
        phrases,
    )

    tag_ids = []
    entity_ids = []
    errors = []

    # Step 1: Look for matching Qloo tags.
    for phrase in phrases:
        tag_id = search_tag(session, phrase, category)

        if tag_id and tag_id not in tag_ids:
            tag_ids.append(tag_id)

    # Step 2: Try relevant category hints only when no direct tag matched.
    # Hints are search queries, not invented recommendation results.
    if not tag_ids:
        normalized_phrases = [
            normalize(phrase) for phrase in phrases
        ]

        for hint in CATEGORY_SEARCH_HINTS.get(category, []):
            normalized_hint = normalize(hint)

            overlaps = any(
                phrase in normalized_hint
                or normalized_hint in phrase
                for phrase in normalized_phrases
                if phrase
            )

            if not overlaps:
                continue

            tag_id = search_tag(session, hint, category)

            if tag_id and tag_id not in tag_ids:
                tag_ids.append(tag_id)

    results = []
    retrieval_method = None

    # Step 3: Try tag-based cultural insights.
    if tag_ids:
        try:
            results = get_insights(
                session,
                category,
                tag_ids=tag_ids,
            )

            if results:
                retrieval_method = "qloo_tag_insights"

        except (requests.RequestException, ValueError) as exc:
            errors.append(str(exc))
            logger.warning(
                "QLOO TAG INSIGHTS ERROR: %s",
                exc,
            )

    # Step 4: If tags did not return results, try exact entity matches.
    if not results:
        for phrase in phrases:
            entity_id = search_entity(
                session,
                phrase,
                category,
            )

            if entity_id and entity_id not in entity_ids:
                entity_ids.append(entity_id)

        if entity_ids:
            try:
                results = get_insights(
                    session,
                    category,
                    entity_ids=entity_ids,
                )

                if results:
                    retrieval_method = "qloo_entity_insights"

            except (requests.RequestException, ValueError) as exc:
                errors.append(str(exc))
                logger.warning(
                    "QLOO ENTITY INSIGHTS ERROR: %s",
                    exc,
                )

    # Step 5: Log the raw metadata BEFORE recommendations are scored.
    # This helps us understand why irrelevant results may be returned.
    log_entity_diagnostics(
        results,
        category,
        retrieval_method or "unknown",
    )

    usable = []

    for entity in results:
        if not isinstance(entity, dict) or not get_entity_id(entity):
            continue

        item = dict(entity)
        item["source"] = "Qloo"
        item["retrieval_method"] = retrieval_method
        usable.append(item)

    if usable:
        return {
            "status": "success",
            "source": "Qloo",
            "category": category,
            "interests": interests,
            "search_phrases": phrases,
            "retrieval_method": retrieval_method,
            "results": usable[:RESULT_LIMIT],
            "message": (
                f"Retrieved {len(usable[:RESULT_LIMIT])} usable "
                "entities from Qloo."
            ),
        }

    if errors:
        return {
            "status": "api_error",
            "source": "Qloo",
            "category": category,
            "interests": interests,
            "search_phrases": phrases,
            "results": [],
            "message": (
                "Qloo API request failed. "
                "Check the backend logs for details."
            ),
        }

    return {
        "status": "no_results",
        "source": "Qloo",
        "category": category,
        "interests": interests,
        "search_phrases": phrases,
        "results": [],
        "message": (
            "Qloo returned no usable entities. Try a specific title, "
            "artist, cuisine, or destination."
        ),
    }








