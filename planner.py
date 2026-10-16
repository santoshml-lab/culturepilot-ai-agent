
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

    matches.sort(reverse=True)
    return matches[0][1]


def create_plan(
    interests: str,
    category: str | None = None,
) -> dict:
    interests = interests.strip()

    if not interests:
        raise ValueError("Please provide your interests.")

    if category is None:
        category = detect_category(interests)

    if category is not None:
        aliases = {
            "movies": "Movies",
            "movie": "Movies",
            "film": "Movies",
            "films": "Movies",
            "music": "Music",
            "food": "Food",
            "travel": "Travel",
        }

        category = aliases.get(category.strip().casefold())

    if category is None:
        return {
            "interests": interests,
            "category": None,
            "status": "unsupported_or_unclear_category",
            "message": (
                "Try a supported category: Movies, Music, Food, or Travel."
            ),
            "plan": [],
            "qloo_required": True,
            "qloo_connected": False,
        }

    steps = [
        {
            "step": 1,
            "agent": "planner",
            "task": "Understand interests and identify the category.",
        },
        {
            "step": 2,
            "agent": "researcher",
            "task": "Retrieve relevant cultural data from Qloo.",
        },
        {
            "step": 3,
            "agent": "recommender",
            "task": "Select relevant recommendations from retrieved data.",
        },
        {
            "step": 4,
            "agent": "reviewer",
            "task": "Check recommendation relevance and available data.",
        },
        {
            "step": 5,
            "agent": "executor",
            "task": "Return the reviewed results.",
        },
    ]

    return {
        "interests": interests,
        "category": category,
        "status": "plan_created",
        "plan": steps,
        "qloo_required": True,
        "qloo_connected": False,
    }


