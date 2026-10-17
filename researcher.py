
import os
import requests

QLOO_BASE_URL = "https://hackathon.api.qloo.com"
TIMEOUT = 20
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
    "Movies": {
        "science fiction": ["science fiction", "sci-fi"],
        "sci-fi": ["sci-fi", "science fiction"],
        "comedy": ["comedy"],
        "horror": ["horror"],
        "thriller": ["thriller"],
        "romance": ["romance"],
        "drama": ["drama"],
        "action": ["action"],
        "animation": ["animation"],
        "documentary": ["documentary"],
        "fantasy": ["fantasy"],
    },
    "Music": {
        "indie pop": ["indie pop", "indie music"],
        "indie rock": ["indie rock", "indie music"],
        "pop": ["pop music", "pop"],
        "rock": ["rock music", "rock"],
        "jazz": ["jazz"],
        "classical": ["classical music"],
        "hip hop": ["hip hop", "hip-hop"],
        "electronic": ["electronic music"],
    },
    "Food": {
        "indian street food": ["Indian street food", "street food"],
        "indian food": ["Indian cuisine", "Indian food"],
        "street food": ["street food"],
        "italian food": ["Italian cuisine", "Italian food"],
        "japanese food": ["Japanese cuisine", "Japanese food"],
        "vegan food": ["vegan food", "vegan restaurants"],
    },
    "Travel": {
        "mountain destinations": ["mountain destinations", "mountain travel"],
        "mountains": ["mountain destinations", "mountains"],
        "beaches": ["beach destinations", "beaches"],
        "historical places": ["historical destinations", "historic places"],
        "adventure travel": ["adventure travel", "adventure destinations"],
        "nature": ["nature destinations", "nature travel"],
    },
}


def normalize(value):
    return " ".join(str(value or "").casefold().split())


def normalize_category(category):
    return CATEGORY_ALIASES.get(normalize(category))


def get_tag_list(data):
    if not isinstance(data, dict):
        return []

    results = data.get("results")

    if isinstance(results, dict):
        tags = results.get("tags")
        if isinstance(tags, list):
            return tags

    tags = data.get("tags", [])
    return tags if isinstance(tags, list) else []


def find_tag_id(data, search_terms):
    tags = get_tag_list(data)
    terms = {normalize(term) for term in search_terms}

    for tag in tags:
        if not isinstance(tag, dict):
            continue

        name = normalize(tag.get("name"))
        tag_id = tag.get("id") or tag.get("tag_id")

        if name in terms and tag_id:
            return tag_id

    return None


def extract_entities(data):
    if not isinstance(data, dict):
        return []

    results = data.get("results", {})

    if isinstance(results, dict):
        entities = results.get("entities", [])
        return entities if isinstance(entities, list) else []

    return []


def entity_text(entity):
    if not isinstance(entity, dict):
        return ""

    properties = entity.get("properties", {})
    if not isinstance(properties, dict):
        properties = {}

    values = [
        entity.get("name"),
        entity.get("title"),
        entity.get("description"),
        entity.get("short_description"),
        properties.get("name"),
        properties.get("description"),
    ]

    return " ".join(str(value) for value in values if value)


def search_genre_tag(headers, search_term, category):
    category_type = CATEGORY_TYPES[category]
    hints = CATEGORY_SEARCH_HINTS.get(category, {})
    candidates = hints.get(normalize(search_term), [search_term])

    for candidate in candidates:
        response = requests.get(
            f"{QLOO_BASE_URL}/v2/tags",
            headers=headers,
            params={
                "filter.query": candidate,
                "filter.parents.types": category_type,
                "take": 20,
            },
            timeout=TIMEOUT,
        )

        print(
            "QLOO TAG SEARCH:",
            category,
            candidate,
            response.status_code,
        )
        response.raise_for_status()

        tag_id = find_tag_id(response.json(), [candidate])

        if tag_id:
            print("QLOO TAG FOUND:", tag_id)
            return tag_id

    return None


def search_entity(headers, search_term, category_type):
    response = requests.get(
        f"{QLOO_BASE_URL}/search",
        headers=headers,
        params={
            "query": search_term,
            "types": category_type,
            "take": 10,
        },
        timeout=TIMEOUT,
    )

    print("QLOO ENTITY SEARCH STATUS:", response.status_code)
    response.raise_for_status()

    data = response.json()
    entities = data.get("results", [])

    if isinstance(entities, dict):
        entities = entities.get("entities", [])

    if not isinstance(entities, list):
        return None

    query = normalize(search_term)

    for entity in entities:
        if not isinstance(entity, dict):
            continue

        entity_id = entity.get("entity_id") or entity.get("id")
        if not entity_id:
            continue

        # Avoid choosing an unrelated first search result.
        if query and query in normalize(entity_text(entity)):
            print("QLOO ENTITY MATCH:", entity_text(entity), entity_id)
            return entity_id

    print("QLOO ENTITY SEARCH: No exact phrase match found.")
    return None


def get_insights(headers, params):
    print("QLOO INSIGHTS PARAMS:", params)

    response = requests.get(
        f"{QLOO_BASE_URL}/v2/insights",
        headers=headers,
        params=params,
        timeout=TIMEOUT,
    )

    print("QLOO INSIGHTS STATUS:", response.status_code)
    response.raise_for_status()

    results = extract_entities(response.json())
    print("QLOO INSIGHTS RESULT COUNT:", len(results))

    return results


def research_cultural_data(interests: str, category: str) -> dict:
    interests = (interests or "").strip()
    category = normalize_category(category)

    if not interests:
        raise ValueError("Please provide your interests.")

    if not category:
        return {
            "agent": "researcher",
            "status": "unsupported_category",
            "source": "Qloo",
            "results": [],
            "message": "Supported categories: Movies, Music, Food, Travel.",
        }

    api_key = os.getenv("QLOO_API_KEY")

    if not api_key:
        return {
            "agent": "researcher",
            "status": "waiting_for_api_key",
            "source": "Qloo",
            "results": [],
            "message": "QLOO_API_KEY is not configured on the backend.",
        }

    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json",
    }

    category_type = CATEGORY_TYPES[category]
    search_term = interests.split(",")[0].strip()

    try:
        results = []
        retrieval_method = None

        # Route 1: Look for a Qloo cultural tag.
        try:
            tag_id = search_genre_tag(
                headers,
                search_term,
                category,
            )
        except requests.RequestException as exc:
            print("QLOO TAG SEARCH ERROR:", str(exc))
            tag_id = None
        except (ValueError, TypeError) as exc:
            print("QLOO TAG RESPONSE ERROR:", str(exc))
            tag_id = None

        if tag_id:
            try:
                results = get_insights(
                    headers,
                    {
                        "filter.type": category_type,
                        "signal.interests.tags": tag_id,
                        "take": RESULT_LIMIT,
                    },
                )

                if results:
                    retrieval_method = "qloo_tag_insights"

            except requests.RequestException as exc:
                print("QLOO TAG INSIGHTS ERROR:", str(exc))

        # Route 2: Use a named Qloo entity as the taste signal.
        if not results:
            try:
                entity_id = search_entity(
                    headers,
                    search_term,
                    category_type,
                )

                if entity_id:
                    results = get_insights(
                        headers,
                        {
                            "filter.type": category_type,
                            "signal.interests.entities": entity_id,
                            "take": RESULT_LIMIT,
                        },
                    )

                    if results:
                        retrieval_method = "qloo_entity_insights"

            except requests.RequestException as exc:
                print("QLOO ENTITY/INSIGHTS ERROR:", str(exc))

        # Keep only actual entity objects with a stable identifier.
        usable_results = []

        for item in results:
            if not isinstance(item, dict):
                continue

            entity_id = item.get("entity_id") or item.get("id")
            if not entity_id:
                continue

            item = dict(item)
            item["source"] = "Qloo"
            item["retrieval_method"] = retrieval_method
            usable_results.append(item)

        status = "success" if usable_results else "no_results"

        return {
            "agent": "researcher",
            "status": status,
            "interests": interests,
            "category": category,
            "source": "Qloo",
            "retrieval_method": retrieval_method,
            "results": usable_results[:RESULT_LIMIT],
            "message": (
                f"Retrieved {len(usable_results[:RESULT_LIMIT])} "
                "usable entities from Qloo."
                if usable_results
                else (
                    "Qloo returned no usable entities for this query. "
                    "Try a specific title, artist, cuisine, or destination."
                )
            ),
        }

    except requests.RequestException as exc:
        response = getattr(exc, "response", None)

        if response is not None:
            print(
                "QLOO API ERROR:",
                response.status_code,
                response.text[:1200],
            )
        else:
            print("QLOO CONNECTION ERROR:", str(exc))

        return {
            "agent": "researcher",
            "status": "api_error",
            "interests": interests,
            "category": category,
            "source": "Qloo",
            "results": [],
            "message": "Qloo API request failed. Check backend logs.",
        }

    except (ValueError, TypeError, AttributeError) as exc:
        print("QLOO RESPONSE ERROR:", type(exc).__name__, str(exc))

        return {
            "agent": "researcher",
            "status": "invalid_api_response",
            "interests": interests,
            "category": category,
            "source": "Qloo",
            "results": [],
            "message": "Qloo returned an unexpected response.",
        }






