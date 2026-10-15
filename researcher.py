
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


def research_cultural_data(
    interests: str,
    category: str,
) -> dict:
    interests = interests.strip()
    category = category.strip().title()

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

    try:
        # Resolve the first interest to a Qloo entity ID.
        search_response = requests.get(
            f"{QLOO_BASE_URL}/search",
            headers=headers,
            params={
                "query": interests.split(",")[0].strip(),
                "types": CATEGORY_TYPES[category],
                "take": 5,
            },
            timeout=TIMEOUT,
        )
        search_response.raise_for_status()
        search_data = search_response.json()

        entities = search_data.get("results", [])
        if not entities:
            entities = search_data.get("entities", [])

        entity_id = None
        if entities:
            entity_id = (
                entities[0].get("entity_id")
                or entities[0].get("id")
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
                    "Try a more specific interest."
                ),
            }

        # Request recommendations using the resolved entity ID.
        insights_response = requests.get(
            f"{QLOO_BASE_URL}/v2/insights",
            headers=headers,
            params={
                "filter.type": CATEGORY_TYPES[category],
                "signal.interests.entities": entity_id,
                "take": 10,
            },
            timeout=TIMEOUT,
        )
        insights_response.raise_for_status()
        insights_data = insights_response.json()

        results = insights_data.get("results", {}).get(
            "entities", []
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

    except requests.RequestException:
        return {
            "agent": "researcher",
            "status": "api_error",
            "interests": interests,
            "category": category,
            "source": "Qloo",
            "results": [],
            "message": (
                "Qloo request failed. Check the API key, "
                "hackathon access, endpoint parameters, "
                "and backend logs."
            ),
        }
    except (ValueError, TypeError, AttributeError):
        return {
            "agent": "researcher",
            "status": "invalid_api_response",
            "interests": interests,
            "category": category,
            "source": "Qloo",
            "results": [],
            "message": "Qloo returned an unexpected response.",
        }

