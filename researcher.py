
import os
import re
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

QLOO_BASE_URL = "https://hackathon.api.qloo.com"
TIMEOUT = 35
RESULT_LIMIT = 10

# Entity type used to find the user's starting interest.
SEARCH_TYPES = {
    "Movies": "urn:entity:movie",
    "Music": "urn:entity:artist",
    "Food": "urn:entity:place",
    "Travel": "urn:entity:place",
}

# Entity type used for recommendations.
INSIGHT_TYPES = {
    "Movies": "urn:entity:movie",
    "Music": "urn:entity:artist",
    "Food": "urn:entity:place",
    "Travel": "urn:entity:place",
}

# Country codes supported by Qloo's geocode filter.
COUNTRY_CODES = {
    "japan": "JP",
    "india": "IN",
    "france": "FR",
    "italy": "IT",
    "thailand": "TH",
    "indonesia": "ID",
    "china": "CN",
    "south korea": "KR",
    "korea": "KR",
    "usa": "US",
    "united states": "US",
    "america": "US",
    "uk": "GB",
    "united kingdom": "GB",
    "england": "GB",
    "australia": "AU",
    "spain": "ES",
    "germany": "DE",
    "singapore": "SG",
    "malaysia": "MY",
    "nepal": "NP",
    "sri lanka": "LK",
    "vietnam": "VN",
    "turkey": "TR",
    "turkiye": "TR",
    "greece": "GR",
    "switzerland": "CH",
    "canada": "CA",
    "mexico": "MX",
    "brazil": "BR",
    "new zealand": "NZ",
    "portugal": "PT",
    "netherlands": "NL",
    "ireland": "IE",
    "egypt": "EG",
    "uae": "AE",
    "united arab emirates": "AE",
    "south africa": "ZA",
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        value = str(value)

    return re.sub(r"\s+", " ", str(value)).strip()


def split_interests(interests: Any) -> list[str]:
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
        raise RuntimeError(
            "Qloo returned an unexpected response format."
        )

    return payload


def extract_entities(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [
            item for item in payload
            if isinstance(item, dict)
        ]

    if not isinstance(payload, dict):
        return []

    # Qloo responses may wrap results in nested objects.
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


def get_entity_properties(
    entity: dict[str, Any],
) -> dict[str, Any]:
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

    return " ".join(
        part for part in parts if part
    ).casefold()


def filter_food_entities(
    entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
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
        "sushi",
        "ramen",
        "izakaya",
        "noodle",
        "pizza",
        "seafood",
        "food court",
        "eatery",
        "bistro",
        "diner",
        "tea house",
        "tea shop",
        "sushi bar",
    )

    non_food_terms = (
        "hotel",
        "inn",
        "ryokan",
        "hostel",
        "resort",
        "accommodation",
        "lodging",
        "guesthouse",
        "guest house",
        "hot spring",
        "onsen",
        "museum",
        "airport",
        "train station",
        "shopping mall",
    )

    filtered = []

    for entity in entities:
        properties = get_entity_properties(entity)

        name = entity_name(entity).casefold()

        description = " ".join(
            normalize_text(
                properties.get(key, entity.get(key))
            )
            for key in (
                "type",
                "subtype",
                "category",
                "description",
                "short_description",
            )
        ).casefold()

        combined = f"{name} {description}"

        # Reject clearly unrelated places, especially lodging.
        if any(term in combined for term in non_food_terms):
            continue

        # Keep only entities with a recognizable food connection.
        if any(term in combined for term in food_terms):
            filtered.append(entity)

    logger.info(
        "Food relevance filter: input=%d accepted=%d rejected=%d",
        len(entities),
        len(filtered),
        len(entities) - len(filtered),
    )

    return filtered




        


def search_tag(
    phrase: str,
    category: str,
) -> list[dict[str, Any]]:
    try:
        payload = qloo_get(
            "/v2/tags",
            {
                "filter.query": phrase,
                "take": RESULT_LIMIT,
            },
        )
        return extract_entities(payload)

    except (
        requests.RequestException,
        RuntimeError,
    ) as exc:
        logger.info("Qloo tag search unavailable: %s", exc)
        return []


def search_entity(
    phrase: str,
    category: str,
) -> list[dict[str, Any]]:
    entity_type = SEARCH_TYPES.get(category)

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
    interests: list[str] | None = None,
) -> list[dict[str, Any]]:
    entity_type = INSIGHT_TYPES.get(category)

    if not entity_type:
        return []

    ids = []

    for entity in entities:
        identifier = entity_id(entity)

        if identifier and identifier not in ids:
            ids.append(identifier)

    if not ids:
        return []

    params: dict[str, Any] = {
        "filter.type": entity_type,
        "signal.interests.entities": ",".join(ids[:3]),
        "take": RESULT_LIMIT,
    }

    # Restrict travel recommendations to the requested country
    # whenever the interest maps to a known country code.
    if category == "Travel":
        phrases = interests or []
        country_code = None

        for phrase in phrases:
            key = normalize_text(phrase).casefold()

            if key in COUNTRY_CODES:
                country_code = COUNTRY_CODES[key]
                break

        if country_code:
            params["filter.geocode.country_code"] = country_code
            logger.info(
                "Travel Insights country filter enabled: %s",
                country_code,
            )
        else:
            # Do not request broad global place recommendations
            # when the country cannot be safely identified.
            logger.info(
                "Travel country code not recognized; "
                "skipping unrestricted Insights."
            )
            return []

    payload = qloo_get("/v2/insights", params)
    results = extract_entities(payload)

    logger.info(
        "Qloo Insights: category=%s count=%d",
        category,
        len(results),
    )

    return results


def log_entity_diagnostics(
    entities: list[dict[str, Any]],
    category: str,
) -> None:
    logger.info(
        "CulturePilot research: category=%s result_count=%d",
        category,
        len(entities),
    )


def research_cultural_data(
    interests: Any,
    category: str,
) -> dict[str, Any]:
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

    collected: list[dict[str, Any]] = []
    methods: list[str] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    errors: list[str] = []

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

            if dedup_key in seen_ids:
                continue

            if name and name.casefold() in seen_names:
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

            logger.info(
                "Qloo entity search: category=%s phrase=%s count=%d",
                normalized_category,
                phrase,
                len(entities),
            )

            if not entities:
                continue

            methods.append("entity_search")

            if normalized_category == "Food":
                entities = filter_food_entities(entities)

            # Keep direct destination search results only if their
            # names actually match the requested travel interest.
            if normalized_category == "Travel":
                phrase_key = phrase.casefold()

                matching_destinations = [
                    entity for entity in entities
                    if entity_name(entity).casefold() == phrase_key
                ]

                try:
                    insights = get_insights(
                        normalized_category,
                        entities[:3],
                        interests=[phrase],
                    )

                    if insights:
                        methods.append("entity_insights")
                        add_results(insights)
                    else:
                        logger.info(
                            "No country-filtered travel insights "
                            "for interest=%s",
                            phrase,
                        )

                except (
                    requests.RequestException,
                    RuntimeError,
                    ValueError,
                ) as exc:
                    logger.warning(
                        "Travel Insights failed for %s: %s",
                        phrase,
                        type(exc).__name__,
                    )
                    errors.append(type(exc).__name__)

                # A matched country entity is a safe fallback,
                # unlike unrelated attractions from another country.
                if not collected and matching_destinations:
                    add_results(matching_destinations)
                    if matching_destinations:
                        methods.append("destination_search_fallback")

            else:
                try:
                    insights = get_insights(
                        normalized_category,
                        entities[:3],
                        interests=[phrase],
                    )

                    
                    if insights:
                        if normalized_category == "Food":
                            insights = filter_food_entities(insights)

                        if insights:
                            methods.append("entity_insights")
                            add_results(insights)
                   else:
    # Preserve the existing non-travel fallback.
                       add_results(entities)

                        
                        
                    else:
                        # Preserve the existing non-travel fallback.
                        add_results(entities)

                except (
                    requests.RequestException,
                    RuntimeError,
                    ValueError,
                ) as exc:
                    logger.warning(
                        "Qloo Insights failed for %s: %s",
                        phrase,
                        type(exc).__name__,
                    )
                    errors.append(type(exc).__name__)
                    add_results(entities)

        except (
            requests.RequestException,
            RuntimeError,
            ValueError,
        ) as exc:
            logger.warning(
                "Qloo entity search failed for %s: %s",
                phrase,
                type(exc).__name__,
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
            "Try a supported country or a more specific interest."
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




                






    












