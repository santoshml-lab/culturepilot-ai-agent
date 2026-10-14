
def research_cultural_data(
    interests: str,
    category: str,
) -> dict:
    """
    Researcher scaffold for CulturePilot AI.
    Real cultural data retrieval will be added
    when Qloo API access becomes available.
    """

    interests = interests.strip()
    category = category.strip().title()

    if not interests:
        raise ValueError("Please provide your interests.")

    supported_categories = {
        "Movies",
        "Music",
        "Food",
        "Travel",
        "All experiences",
    }

    if category not in supported_categories:
        raise ValueError(
            "Choose Movies, Music, Food, Travel, "
            "or All experiences."
        )

    return {
        "agent": "researcher",
        "status": "waiting_for_api_access",
        "interests": interests,
        "category": category,
        "source": None,
        "results": [],
        "message": (
            "Qloo API access is pending. "
            "No external cultural data has been retrieved."
        ),
    }
