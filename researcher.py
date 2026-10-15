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
    """Read tags from the common Qloo response structure."""
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
    """Find an exact or close matching genre tag."""
    tags = _get_tag_list(data)

    normalized_terms = {
        term.casefold().strip()
        for term in search_terms
    }

    # Prefer an exact name match.
    for tag in tags:
        if not isinstance(tag, dict):
            continue

        name = str(tag.get("name") or "").casefold().strip()
        tag_id = tag.get("id") or tag.get("tag_id")

        if name in normalized_terms and tag_id:
            return tag_id

    # Allow a close match only when the requested term
    # is contained in the tag name or vice versa.
    for tag in tags:
        if not isinstance(tag, dict):
            continue

        name = str(tag.get("name") or "").casefold().strip()
        tag_id = tag.get("id") or tag.get("tag_id")

        if not name or not tag_id:
            continue

        if any(
            term in name or name in term
            for term in normalized_terms
        ):
            return tag_id

    return None


def _search_genre_tag(headers, search_term, category_type):
    """Search Qloo tags and return a matching tag ID."""
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

            print(
                "QLOO TAG SEARCH STATUS:",
                response.status_code,
            )
            response.raise_for_status()

            data = response.json()
            print(
                "QLOO TAG SEARCH RESPONSE:",
                response.text[:1200],
            )

            tag_id = _find_tag_id(data, [candidate])

            if tag_id:
                print("QLOO TAG FOUND:", tag_id)
                return tag_id

        except (
            requests.RequestException,
            ValueError,
            TypeError,
        ) as exc:
            print(
                "QLOO TAG SEARCH ERROR:",
                type(exc).__name__,
                str(exc),
            )

    return None


def _extract_entities(data):
    """Extract entity results from the Qloo Insights response."""
    if not isinstance(data, dict):
        return []

    results = data.get("results", {})

    if isinstance(results, dict):
        entities = results.get("entities", [])
        return entities if isinstance(entities, list) else []

    return []


def research_cultural_data(
    interests: str,
    category: str,
) -> dict:
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
            "message": (
                "Qloo API key is not configured on the backend."
            ),
        }

    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json",
    }

    category_type = CATEGORY_TYPES[category]
    search_term = interests.split(",")[0].strip()

    try:
        # Step 1: Try a genre tag for movie genre requests.
        tag_id = None

        if (
            category == "Movies"
            and search_term.casefold() in GENRE_HINTS
        ):
            tag_id = _search_genre_tag(
                headers,
                search_term,
                category_type,
            )

        # Step 2: Build the Insights request.
        if tag_id:
            insights_params = {
                "filter.type": category_type,
                "filter.tags": tag_id,
                "take": 10,
            }
        else:
            # Search for a named entity, such as Interstellar.
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

            entities = search_data.get("results", [])

            if isinstance(entities, dict):
                entities = entities.get("entities", [])

            entity_id = None

            if isinstance(entities, list):
                for entity in entities:
                    if not isinstance(entity, dict):
                        continue

                    entity_id = (
                        entity.get("entity_id")
                        or entity.get("id")
                    )

                    if entity_id:
                        break

            if not entity_id:
                return {
                    "agent": "researcher",
                    "status": "no_matching_entity",
                    "interests": interests,
                    "category": category,
                    "source": "Qloo",
                    "results": [],
                    "message": (
                        "No matching Qloo entity was found. "
                        "Try a specific title, artist, or place."
                    ),
                }

            insights_params = {
                "filter.type": category_type,
                "signal.interests.entities": entity_id,
                "take": 10,
            }

        # Step 3: Request recommendations.
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
        results = _extract_entities(insights_data)
        
        # Fallback: if the genre tag returns no results,
        # try Qloo entity-based Insights instead.
        if tag_id and not results:
            print("QLOO TAG RETURNED 0 RESULTS; TRYING ENTITY FALLBACK")

            fallback_search = requests.get(
                f"{QLOO_BASE_URL}/search",
                headers=headers,
                params={
                    "query": search_term,
                    "types": category_type,
                    "take": 5,
                },
                timeout=TIMEOUT,
            )
            fallback_search.raise_for_status()
            fallback_data = fallback_search.json()
            fallback_entities = fallback_data.get("results", [])

            if isinstance(fallback_entities, dict):
                fallback_entities = fallback_entities.get(
                    "entities", []
                )

            fallback_entity_id = None

            if isinstance(fallback_entities, list):
                for entity in fallback_entities:
                    if isinstance(entity, dict):
                        fallback_entity_id = (
                            entity.get("entity_id")
                            or entity.get("id")
                        )
                        if fallback_entity_id:
                            break

            if fallback_entity_id:
                fallback_params = {
                    "filter.type": category_type,
                    "signal.interests.entities": fallback_entity_id,
                    "take": 10,
                }

                print("QLOO FALLBACK INSIGHTS PARAMS:", fallback_params)

                fallback_response = requests.get(
                    f"{QLOO_BASE_URL}/v2/insights",
                    headers=headers,
                    params=fallback_params,
                    timeout=TIMEOUT,
                )
                fallback_response.raise_for_status()

                fallback_insights = fallback_response.json()
                fallback_results = _extract_entities(
                    fallback_insights
                )

                print(
                    "QLOO FALLBACK RESULT COUNT:",
                    len(fallback_results),
                )

                if fallback_results:
                    results = fallback_results


        print(
            "QLOO INSIGHTS RESULT COUNT:",
            len(results),
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
            print(
                f"QLOO {stage if 'stage' in locals() else 'request'} "
                f"FAILED: HTTP {response.status_code}; "
                f"{(response.text or '')[:800]}"
            )
            message = (
                "Qloo API request failed. "
                "Check the Render logs for details."
            )
        else:
            print(
                "QLOO CONNECTION ERROR:",
                type(exc).__name__,
                str(exc),
            )
            message = (
                "Could not connect to Qloo. "
                "Check the backend logs and try again."
            )

        return {
            "agent": "researcher",
            "status": "api_error",
            "interests": interests,
            "category": category,
            "source": "Qloo",
            "results": [],
            "message": message,
        }

    except (ValueError, TypeError, AttributeError) as exc:
        print(
            "QLOO RESPONSE ERROR:",
            type(exc).__name__,
            str(exc),
        )

        return {
            "agent": "researcher",
            "status": "invalid_api_response",
            "interests": interests,
            "category": category,
            "source": "Qloo",
            "results": [],
            "message": (
                "Qloo returned an unexpected response. "
                "Check the Render logs."
            ),
        }



