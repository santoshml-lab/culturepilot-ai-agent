
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

    try:
        # Step 1: Search for a matching Qloo entity.
        stage = "search"

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
        print("QLOO SEARCH RESPONSE:", search_response.text[:3000])

        entities = search_data.get("results", [])
        if not entities:
            entities = search_data.get("entities", [])

        # Support either a list or a dictionary containing entities.
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
            print(
                "Qloo search returned no usable entity. "
                f"Response keys: {list(search_data.keys())}"
            )

            return {
                "agent": "researcher",
                "status": "no_matching_entity",
                "interests": interests,
                "category": category,
                "source": "Qloo",
                "results": [],
                "message": (
                    "Qloo did not return a matching entity. "
                    "Check the search response in Render logs."
                ),
            }

        # Step 2: Request recommendations for the entity.
        stage = "insights"
        print("QLOO INSIGHTS PARAMS:", {
            "filter.type": CATEGORY_TYPES[category],
            "signal.interests.entities": entity_id,
            "take": 10,
})

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
            f"Qloo {stage} succeeded: "
            f"{len(results)} entities returned."
        )

        return {
            "agent": "researcher",
            "status": "success",
            "interests": interests,
            "category": category,
            "source": "Qloo",
            "results": results,
            "message": f"Retrieved {len(results)} results from Qloo.",
        }

    except requests.RequestException as exc:
        response = getattr(exc, "response", None)

        if response is not None:
            # Log diagnostic details, but never log the API key.
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


