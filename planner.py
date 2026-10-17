
import re


SUPPORTED_CATEGORIES = ("Movies", "Music", "Food", "Travel")

CATEGORY_KEYWORDS = {
    "Movies": [
        "movies", "movie", "films", "film", "cinema",
        "science fiction", "sci-fi", "sci fi",
        "thriller", "comedy films", "horror films",
        "interstellar", "movie recommendations",
        "film recommendations", "watch a movie",
    ],
    "Music": [
        "music", "songs", "song", "singer", "singers",
        "musician", "musicians", "artists", "artist",
        "indie pop", "indie rock", "jazz", "hip hop",
        "hip-hop", "rock music", "classical music",
        "pop music", "music recommendations",
        "listen to", "playlists", "playlist",
    ],
    "Food": [
        "food", "cuisine", "restaurant", "restaurants",
        "street food", "indian food", "italian food",
        "japanese food", "vegan food", "what to eat",
        "food recommendations", "places to eat",
    ],
    "Travel": [
        "travel", "travelling", "traveling", "destination",
        "destinations", "mountain", "mountains", "beach",
        "beaches", "historical places", "adventure travel",
        "nature destinations", "places to visit",
        "travel recommendations", "holiday destinations",
    ],
}

CATEGORY_ALIASES = {
    "movie": "Movies",
    "movies": "Movies",
    "film": "Movies",
    "films": "Movies",
    "cinema": "Movies",
    "music": "Music",
    "artist": "Music",
    "artists": "Music",
    "song": "Music",
    "songs": "Music",
    "food": "Food",
    "restaurant": "Food",
    "restaurants": "Food",
    "travel": "Travel",
    "destination": "Travel",
    "destinations": "Travel",
}


def normalize_text(value):
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        str(value or "").casefold(),
    ).strip()


def contains_phrase(text, phrase):
    normalized_text = f" {normalize_text(text)} "
    normalized_phrase = normalize_text(phrase)

    return (
        bool(normalized_phrase)
        and f" {normalized_phrase} " in normalized_text
    )


def normalize_category(category):
    if not category:
        return None

    return CATEGORY_ALIASES.get(
        normalize_text(category)
    )


def detect_category(interests: str) -> str | None:
    query = normalize_text(interests)

    if not query:
        return None

    scores = {category: 0 for category in SUPPORTED_CATEGORIES}

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if contains_phrase(query, keyword):
                # Longer, more specific phrases carry more weight.
                scores[category] += 2 + len(
                    normalize_text(keyword).split()
                )

    # Resolve category using the strongest keyword evidence.
    best_score = max(scores.values())

    if best_score == 0:
        return None

    winners = [
        category
        for category, score in scores.items()
        if score == best_score
    ]

    # Ambiguous mixed-category input requires user selection.
    if len(winners) != 1:
        return None

    return winners[0]


def create_plan(
    interests: str,
    category: str | None = None,
) -> dict:
    interests = (interests or "").strip()

    if not interests:
        raise ValueError("Please provide your interests.")

    selected_category = normalize_category(category)

    if category and not selected_category:
        return {
            "interests": interests,
            "category": None,
            "status": "unsupported_category",
            "message": (
                "Choose Movies, Music, Food, or Travel."
            ),
            "plan": [],
            "qloo_required": True,
            "qloo_connected": False,
        }

    if selected_category is None:
        selected_category = detect_category(interests)

    if selected_category is None:
        return {
            "interests": interests,
            "category": None,
            "status": "needs_category",
            "message": (
                "Please select Movies, Music, Food, or Travel "
                "so Qloo can search the correct entity type."
            ),
            "plan": [],
            "qloo_required": True,
            "qloo_connected": False,
        }

    steps = [
        {
            "step": 1,
            "agent": "planner",
            "task": (
                f"Understand the interests and plan a "
                f"{selected_category} discovery request."
            ),
        },
        {
            "step": 2,
            "agent": "researcher",
            "task": (
                "Search Qloo and retrieve cultural insight entities."
            ),
        },
        {
            "step": 3,
            "agent": "recommender",
            "task": (
                "Rank Qloo results using available evidence "
                "and preserve valid insight results."
            ),
        },
        {
            "step": 4,
            "agent": "reviewer",
            "task": (
                "Validate entity identity, source and score."
            ),
        },
        {
            "step": 5,
            "agent": "executor",
            "task": (
                "Return the reviewed recommendations and explanations."
            ),
        },
    ]

    return {
        "interests": interests,
        "category": selected_category,
        "status": "plan_created",
        "plan": steps,
        "qloo_required": True,
        "qloo_connected": False,
    }



