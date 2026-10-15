
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

# Common genre phrases. These are search hints, not Qloo tag IDs.
GENRE_HINTS = {
    "science fiction",
    "sci-fi",
    "comedy",
    "horror",
    "thriller",
    "romance",
    "drama",
    "action",
    "animation",
    "documentary",
    "fantasy",
}


def _extract_list(data, *keys):
    """Extract a list from common Qloo response shapes."""
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return []
        current = current.get(key)

    return current if isinstance(current, list) else []


def _find_tag_id(tag_data, search_term):
    """Find a matching tag ID in a Qloo tags response."""
    search_term = search_term.casefold().strip()

    possible_lists = [
        _extract_list(tag_data, "results", "tags"),
        _extract_list(tag_data, "results"),
        _extract_list(tag_data, "tags"),
    ]

    for tags in possible_lists:
        for tag in tags:
            if not isinstance(tag, dict):
                continue

            name = str(tag.get("name") or "").casefold().strip()
            tag_id = (
                tag.get("tag_id")
                or tag.get("id")
                or tag.get("tag_value")
            )

            if tag_id and name == search_term:
                return tag_id

    return None


def _search_genre_tag(headers, search_term, category_type):
    """
    Attempt Qloo tag lookup.

    The tag-search query parameters must match the active Qloo
    API schema. If lookup fails, return None so entity search
    can be attempted instead.
    """
    try:
        response = requests.get(
            f"{QLOO_BASE_URL}/v2/tags",
            headers=headers,
            params={
                "filter.parents.types": category_type,
                "take": 10,
                "query": search_term,
            },
            timeout=TIMEOUT,
        )

        print(
            "QLOO TAG SEARCH STATUS:",
            response.status_code,
        )
        print(
            "QLOO TAG SEARCH RESPONSE:",
            response.text[:1500],
        )

        response.raise_for_status()
        tag_data = response.json()
        return _find_tag_id(tag_data, search_term)

    except (requests.RequestException, ValueError, TypeError) as exc:
        print(
            "Qloo tag lookup unavailable:",
            type(exc).__name__,
            str(exc),
        )
        return None


def research_cultural_data(
    interests: str,
    category: str,
) -> dict:
    interests = (interests or "").strip()
    category = (category or "").strip().title()
    stage = "initialization"

    if not interests:
        raise ValueError("Please provide your interests.")

    api_key = os.getenv("QLOO_API_KEY")

    if not api_key:
        return {
            "agent": "researcher",
            "status": "waiting_for_api_key",
            "results": [],
            "message": "Qloo API key is not configured on the backend.",
        }

    if category not in CATEGORY_TYPES:
        return {
            "agent": "researcher",
            "status": "unsupported_category",
            "results": [],
            "message": (
                "Live Qloo search currently supports Movies, "
                "Music, Food, and Travel."
            ),
        }

    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json",
    }

    category_type = CATEGORY_TYPES[category]
    search_term = interests.split(",")[0].strip()

    try:
        # Step 1: For likely movie genres, try tag lookup first.
        tag_id = None

        if (
            category == "Movies"
            and search_term.casefold() in GENRE_HINTS
        ):
            stage = "tag_search"
            tag_id = _search_genre_tag(
                headers,
                search_term,
                category_type,
            )

        # Step 2: Request Insights using a valid tag ID if found.
        if tag_id:
            stage = "insights"
            insights_params = {
                "filter.type": category_type,
                "signal.interests.tags": tag_id,
                "take": 10,
            }

        else:
            # Preserve the existing entity-search workflow.
            stage = "search"

            search_response = requests.get(
                f"{QLOO_BASE_URL}/search",
                headers=headers,
                params={
                    "query": search_term,
                    "types": category_type,
                    "take": 5,
                },
                timeout=TIMEOUT,
            )

            search_response.raise_for_status()
            search_data = search_response.json()

            print(
                "QLOO SEARCH RESPONSE:",
                search_response.text[:3000],
            )

            entities = search_data.get("results", [])

            if not entities:
                entities = search_data.get("entities", [])

            if isinstance(entities, dict):
                entities = entities.get("entities", [])

            entity_id = None

            if isinstance(entities, list) and entities:
                first_entity = entities[0]

                if isinstance(first_entity, dict):
                    entity_id = (
                        first_entity.get("entity_id")
                        or first_entity.get("id")
                    )

            if not entity_id:
                return {
                    "agent": "researcher",
                    "status": "no_matching_entity",
                    "interests": interests,
                    "category": category,
                    "source": "Qloo",
                    "results": [],
                    "message": (
                        "Qloo did not return a matching entity. "
                        "Check the Render logs."
                    ),
                }

            insights_params = {
                "filter.type": category_type,
                "signal.interests.entities": entity_id,
                "take": 10,
            }

        print("QLOO INSIGHTS PARAMS:", insights_params)

        stage = "insights"

        insights_response = requests.get(
            f"{QLOO_BASE_URL}/v2/insights",
            headers=headers,
            params=insights_params,
            timeout=TIMEOUT,
        )

        insights_response.raise_for_status()
        insights_data = insights_response.json()

        results_data = insights_data.get("results", {})

        if not isinstance(results_data, dict):
            raise ValueError(
                "Unexpected Qloo insights response structure."
            )

        results = results_data.get("entities", [])

        if not isinstance(results, list):
            raise ValueError(
                "Qloo insights entities was not a list."
            )

        print(
            f"Qloo insights succeeded: "
            f"{len(results)} entities returned."
        )

        return {
            "agent": "researcher",
            "status": "success",
            "interests": interests,
            "category": category,
            "source": "Qloo",
            "results": results,
            "message": (
                f"Retrieved {len(results)} results from Qloo."
            ),
        }

    except requests.RequestException as exc:
        response = getattr(exc, "response", None)

        if response is not None:
            error_body = (response.text or "")[:500]

            print(
                f"Qloo {stage} failed: "
                f"HTTP {response.status_code}; "
                f"response={error_body}"
            )

            error_message = (
                f"Qloo {stage} request failed with HTTP "
                f"{response.status_code}. Check Render logs."
            )
        else:
            print(
                f"Qloo {stage} request failed: "
                f"{type(exc).__name__}: {exc}"
            )

            error_message = (
                f"Qloo {stage} request failed due to a "
                "connection or timeout error. Check Render logs."
            )

        return {
            "agent": "researcher",
            "status": "api_error",
            "interests": interests,
            "category": category,
            "source": "Qloo",
            "results": [],
            "message": error_message,
        }

    except (ValueError, TypeError, AttributeError) as exc:
        print(
            f"Qloo {stage} response parsing failed: "
            f"{type(exc).__name__}: {exc}"
        )

        return {
            "agent": "researcher",
            "status": "invalid_api_response",
            "interests": interests,
            "category": category,
            "source": "Qloo",
            "results": [],
            "message": (
                f"Qloo returned an unexpected response during "
                f"{stage}. Check Render logs."
            ),
        }



