
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

# Alternative search phrases for each supported category.
CATEGORY_SEARCH_HINTS = {
    "Movies": {
        "science fiction": [
            "science fiction", "sci-fi", "sci fi"
        ],
        "sci-fi": [
            "sci-fi", "science fiction", "sci fi"
        ],
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
        "indie pop": [
            "indie pop", "indie music", "pop music"
        ],
        "indie rock": ["indie rock", "indie music"],
        "pop": ["pop music", "pop"],
        "rock": ["rock music", "rock"],
        "jazz": ["jazz"],
        "classical": ["classical music"],
        "hip hop": ["hip hop", "hip-hop"],
        "electronic": ["electronic music"],
    },
    "Food": {
        "indian street food": [
            "Indian street food", "street food"
        ],
        "indian food": ["Indian cuisine", "Indian food"],
        "street food": ["street food"],
        "italian food": ["Italian cuisine", "Italian food"],
        "japanese food": ["Japanese cuisine", "Japanese food"],
        "vegan food": ["vegan food", "vegan restaurants"],
    },
    "Travel": {
        "mountain destinations": [
            "mountain destinations", "mountain travel"
        ],
        "mountains": ["mountain destinations", "mountains"],
        "beaches": ["beach destinations", "beaches"],
        "historical places": [
            "historical destinations", "historic places"
        ],
        "adventure travel": [
            "adventure travel", "adventure destinations"
        ],
        "nature": ["nature destinations", "nature travel"],
    },
}


def _normalise(value):
    return " ".join(str(value or "").casefold().split())


def _get_tag_list(data):
    if not isinstance(data, dict):
        return []

    results = data.get("results", {})

    if isinstance(results, dict):
        tags = results.get("tags", [])
        if isinstance(tags, list):
            return tags

    tags = data.get("tags", [])
    return tags if isinstance(tags, list) else []


def _find_tag_id(data, search_terms):
    tags = _get_tag_list(data)
    terms = {_normalise(term) for term in search_terms}

    # Prefer exact matches.
    for tag in tags:
        if not isinstance(tag, dict):
            continue

        name = _normalise(tag.get("name"))
        tag_id = tag.get("id") or tag.get("tag_id")

        if name in terms and tag_id:
            return tag_id

    # Accept conservative partial matches only.
    for tag in tags:
        if not isinstance(tag, dict):
            continue

        name = _normalise(tag.get("name"))
        tag_id = tag.get("id") or tag.get("tag_id")

        if not name or not tag_id:
            continue

        if any(
            len(term) >= 4 and (term in name or name in term)
            for term in terms
        ):
            return tag_id

    return None


def _extract_entities(data):
    if not isinstance(data, dict):
        return []

    results = data.get("results", {})

    if isinstance(results, dict):
        entities = results.get("entities", [])
        return entities if isinstance(entities, list) else []

    return []


def _entity_text(entity):
    if not isinstance(entity, dict):
        return ""

    fields = [
        entity.get("name"),
        entity.get("title"),
        entity.get("description"),
        entity.get("short_description"),
    ]

    return " ".join(str(value) for value in fields if value)


def _entity_matches_interest(entity, interests):
    """
    Conservative validation for named-entity fallback.
    This prevents accepting an unrelated first search result.
    """
    name = _normalise(interests)
    text = _normalise(_entity_text(entity))

    if not name or not text:
        return False

    # Full phrase match.
    if name in text:
        return True

    # Require meaningful overlap for multiword queries.
    words = {
        word for word in name.split()
        if len(word) >= 4
    }

    if not words:
        return False

    matched = sum(1 for word in words if word in text)

    return matched >= max(1, len(words) - 1)


def _search_genre_tag(headers, search_term, category):
    category_type = CATEGORY_TYPES[category]
    hints = CATEGORY_SEARCH_HINTS.get(category, {})

    candidates = hints.get(
        _normalise(search_term),
        [search_term],
    )

    for candidate in candidates:
        try:
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

            tag_id = _find_tag_id(
                response.json(),
                [candidate],
            )

            if tag_id:
                print("QLOO TAG FOUND:", category, tag_id)
                return tag_id

        except (
            requests.RequestException,
            ValueError,
            TypeError,
        ) as exc:
            print("QLOO TAG SEARCH ERROR:", str(exc))

    return None


def _search_entity(headers, search_term, category_type):
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

    # Do not blindly use the first entity.
    for entity in entities:
        if not isinstance(entity, dict):
            continue

        entity_id = entity.get("entity_id") or entity.get("id")

        if not entity_id:
            continue

        if _entity_matches_interest(entity, search_term):
            print(
                "QLOO ENTITY MATCH:",
                _entity_text(entity),
                entity_id,
            )
            return entity_id

    print(
        "QLOO ENTITY SEARCH:",
        "No sufficiently close entity match found.",
    )
    return None


def _get_insights(headers, params):
    print("QLOO INSIGHTS PARAMS:", params)

    response = requests.get(
        f"{QLOO_BASE_URL}/v2/insights",
        headers=headers,
        params=params,
        timeout=TIMEOUT,
    )

    print("QLOO INSIGHTS STATUS:", response.status_code)
    print("QLOO INSIGHTS RESPONSE:", response.text[:1500])

    response.raise_for_status()

    results = _extract_entities(response.json())

    print("QLOO INSIGHTS RESULT COUNT:", len(results))

    return results


def research_cultural_data(interests: str, category: str) -> dict:
    interests = (interests or "").strip()
    category = (category or "").strip().title()

    if not interests:
        raise ValueError("Please provide your interests.")

    if category not in CATEGORY_TYPES:
        return {
            "agent": "researcher",
            "status": "unsupported_category",
            "results": [],
            "message": (
                "Supported categories: Movies, Music, Food, Travel."
            ),
        }

    api_key = os.getenv("QLOO_API_KEY")

    if not api_key:
        return {
            "agent": "researcher",
            "status": "waiting_for_api_key",
            "results": [],
            "message": "Qloo API key is not configured on the backend.",
        }

    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json",
    }

    category_type = CATEGORY_TYPES[category]
    search_term = interests.split(",")[0].strip()

    try:
        results = []
        tag_id = None

        # Step 1: Search for a category-specific tag.
        try:
            tag_id = _search_genre_tag(
                headers,
                search_term,
                category,
            )
        except Exception as exc:
            print("QLOO TAG LOOKUP FAILED:", str(exc))

        # Step 2: Retrieve recommendations associated with the tag.
        if tag_id:
            try:
                results = _get_insights(
                    headers,
                    {
                        "filter.type": category_type,
                        "filter.tags": tag_id,
                        "take": RESULT_LIMIT,
                    },
                )
            except requests.RequestException as exc:
                print("QLOO TAG INSIGHTS ERROR:", str(exc))

        # Step 3: Fall back to a named entity only when no tag results exist.
        if not results:
            print("QLOO: Trying validated entity fallback.")

            entity_id = _search_entity(
                headers,
                search_term,
                category_type,
            )

            if entity_id:
                results = _get_insights(
                    headers,
                    {
                        "filter.type": category_type,
                        "signal.interests.entities": entity_id,
                        "take": RESULT_LIMIT,
                    },
                )

        # Do not label empty results as success.
        status = "success" if results else "no_results"

        return {
            "agent": "researcher",
            "status": status,
            "interests": interests,
            "category": category,
            "source": "Qloo",
            "results": results,
            "message": (
                f"Retrieved {len(results)} results from Qloo."
                if results
                else (
                    "No usable Qloo recommendations were found. "
                    "Try a specific title, artist, restaurant, "
                    "or destination."
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





