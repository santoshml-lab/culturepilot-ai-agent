
import os
import requests

QLOO_BASE_URL = "https://hackathon.api.qloo.com"
TIMEOUT = 20

CATEGORY_TYPES = {
    "Movies": "urn:entity:movie",
    "Music": "urn:entity:artist",
    "Food": "urn:entity:place",
    "Travel": "urn:entity:destination",
}

GENRE_HINTS = {
    "science fiction": ["science fiction", "sci-fi", "sci fi"],
    "sci-fi": ["sci-fi", "science fiction", "sci fi"],
    "comedy": ["comedy"],
    "horror": ["horror"],
    "thriller": ["thriller"],
    "romance": ["romance"],
    "drama": ["drama"],
    "action": ["action"],
    "animation": ["animation"],
    "documentary": ["documentary"],
    "fantasy": ["fantasy"],
}


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
    terms = {
        term.casefold().strip()
        for term in search_terms
    }

    # Exact match first.
    for tag in tags:
        if not isinstance(tag, dict):
            continue

        name = str(tag.get("name") or "").casefold().strip()
        tag_id = tag.get("id") or tag.get("tag_id")

        if name in terms and tag_id:
            return tag_id

    # Conservative partial match.
    for tag in tags:
        if not isinstance(tag, dict):
            continue

        name = str(tag.get("name") or "").casefold().strip()
        tag_id = tag.get("id") or tag.get("tag_id")

        if not name or not tag_id:
            continue

        if any(term == name or term in name for term in terms):
            return tag_id

    return None


def _search_genre_tag(headers, search_term, category_type):
    candidates = GENRE_HINTS.get(
        search_term.casefold().strip(),
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

            print("QLOO TAG SEARCH:", candidate, response.status_code)
            response.raise_for_status()

            data = response.json()
            tag_id = _find_tag_id(data, [candidate])

            if tag_id:
                print("QLOO TAG FOUND:", tag_id)
                return tag_id

        except (requests.RequestException, ValueError, TypeError) as exc:
            print("QLOO TAG SEARCH ERROR:", str(exc))

    return None


def _extract_entities(data):
    if not isinstance(data, dict):
        return []

    results = data.get("results", {})

    if isinstance(results, dict):
        entities = results.get("entities", [])
        return entities if isinstance(entities, list) else []

    return []


def _search_entity(headers, search_term, category_type):
    response = requests.get(
        f"{QLOO_BASE_URL}/search",
        headers=headers,
        params={
            "query": search_term,
            "types": category_type,
            "take": 5,
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

    for entity in entities:
        if not isinstance(entity, dict):
            continue

        entity_id = entity.get("entity_id") or entity.get("id")

        if entity_id:
            return entity_id

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
    print("QLOO INSIGHTS RESPONSE:", response.text[:2000])

    response.raise_for_status()

    data = response.json()
    results = _extract_entities(data)

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
            "message": "Supported categories: Movies, Music, Food, Travel.",
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
    tag_id = None

    try:
        # Step 1: Try the genre tag for supported movie genres.
        if (
            category == "Movies"
            and search_term.casefold() in GENRE_HINTS
        ):
            tag_id = _search_genre_tag(
                headers,
                search_term,
                category_type,
            )

        results = []

        # Step 2: Try Insights with the genre tag.
        if tag_id:
            try:
                results = _get_insights(
                    headers,
                    {
                        "filter.type": category_type,
                        "filter.tags": tag_id,
                        "take": 10,
                    },
                )
            except requests.RequestException as exc:
                print("QLOO TAG INSIGHTS ERROR:", str(exc))

        # Step 3: Fallback to a named entity if tag results are empty.
        if not results:
            print("QLOO: Trying entity-based fallback.")

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
                        "take": 10,
                    },
                )

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
                    "Qloo returned no usable recommendations. "
                    "Try a specific movie title, artist, or place."
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
            "message": "Qloo API request failed. Check Render logs.",
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




