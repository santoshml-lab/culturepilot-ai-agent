CATEGORY_KEYWORDS = {
    "Movies": [
        "movie", "movies", "film", "films", "cinema",
        "science fiction", "sci-fi", "sci fi", "thriller",
        "comedy", "horror", "drama", "animation",
        "interstellar", "artificial intelligence movie",
    ],
    "Music": [
        "music", "song", "songs", "singer", "artist",
        "indie pop", "indie rock", "jazz", "hip hop",
        "hip-hop", "rock music", "classical music",
    ],
    "Food": [
        "food", "cuisine", "restaurant", "restaurants",
        "street food", "indian food", "italian food",
        "japanese food", "vegan food",
    ],
    "Travel": [
        "travel", "destination", "destinations",
        "mountain", "mountains", "beach", "beaches",
        "historical places", "adventure travel",
        "nature destinations",
    ],
}


def detect_category(interests: str) -> str | None:
    """Detect a supported cultural category from a user's query."""
    query = interests.strip().casefold()

    if not query:
        return None

    matches = []

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query:
                matches.append((len(keyword), category))

    if not matches:
        return None

    # Prefer the most specific matching phrase.
    matches.sort(reverse=True)
    return matches[0][1]


def create_plan(
    interests: str,
    category: str | None = None,
) -> dict:
    """Create a five-agent plan with optional automatic category detection."""

    interests = interests.strip()

    if not interests:
        raise ValueError("Please provide your interests.")

    if category and category.strip().casefold() not in {
        "auto", "automatic", "all experiences", "all"
    }:
        normalised = category.strip().casefold()

        aliases = {
            "movie": "Movies",
            "movies": "Movies",
            "film": "Movies",
            "films": "Movies",
            "music": "Music",
            "food": "Food",
            "travel": "Travel",
        }

        category = aliases.get(normalised)

        if category is None:
            raise ValueError(
                "Choose Movies, Music, Food, Travel, or Auto."
            )
    else:
        category = None

    # Detect a category if none was explicitly selected.
    if category is None:
        category = detect_category(interests)

    steps = [
        {
            "step": 1,
            "agent": "planner",
            "task": "Understand the user's interests and detect a supported category.",
        },
        {
            "step": 2,
            "agent": "researcher",
            "task": "Retrieve relevant cultural data from Qloo when available.",
        },
        {
            "step": 3,
            "agent": "recommender",
            "task": "Select recommendations relevant to the user's interests.",
        },
        {
            "step": 4,
            "agent": "reviewer",
            "task": "Check recommendation relevance and available data.",
        },
        {
            "step": 5,
            "agent": "executor",
            "task": "Return reviewed results or a clear no-results message.",
        },
    ]

    if category is None:
        return {
            "interests": interests,
            "category": None,
            "plan": steps,
            "status": "unsupported_or_unclear_category",
            "message": (
                "We couldn't identify a supported cultural category. "
                "Try Movies, Music, Food, or Travel."
            ),
            "qloo_required": True,
            "qloo_connected": False,
        }

    return {
        "interests": interests,
        "category": category,
        "plan": steps,
        "status": "plan_created",
        "category_detection": "automatic" if not category else "supported",
        "qloo_required": True,
        "qloo_connected": False,
    }
