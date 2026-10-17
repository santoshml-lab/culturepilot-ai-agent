import re
from difflib import SequenceMatcher
from typing import Any


RESULT_LIMIT = 10

SUPPORTED_CATEGORIES = {
    "movies": "Movies",
    "music": "Music",
    "food": "Food",
    "travel": "Travel",
}

CATEGORY_TERMS = {
    "Movies": [
        "movie", "film", "cinema", "actor", "actress",
        "director", "screenplay", "motion picture",
        "science fiction", "sci fi",
    ],
    "Music": [
        "music", "musical", "singer", "artist", "album",
        "song", "band", "musician", "composer", "genre",
        "classical", "hindustani", "carnatic", "piano",
    ],
    "Food": [
        "food", "cuisine", "restaurant", "street food",
        "dish", "dishes", "recipe", "cooking", "culinary",
        "snack", "snacks", "dessert", "bakery", "cafe",
        "coffee", "seafood", "pizza", "pasta", "sushi",
        "vegan", "vegetarian", "indian cuisine",
        "indian food", "indian street food",
        "specialty dishes", "speciality dishes",
    ],
    "Travel": [
        "travel", "destination", "tourism", "tourist",
        "vacation", "holiday", "landmark", "attraction",
        "island", "city", "country", "national park",
        "travel destination", "mountain", "nature",
        "heritage", "cultural heritage", "landscape",
    ],
}

STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this",
    "into", "about", "best", "good", "great", "some",
    "want", "like", "love", "recommend", "recommendations",
    "suggest", "suggestions", "please", "find", "show",
    "give", "tell", "explore", "discover", "popular",
    "famous", "type", "types", "things", "something",
    "near", "very", "more", "most", "which", "what",
}

INTEREST_SYNONYMS = {
    "indian street food": [
        "indian street food", "street food", "indian cuisine",
        "indian food", "street snacks",
    ],
    "indian food": [
        "indian food", "indian cuisine",
        "indian restaurant", "indian dishes",
    ],
    "street food": [
        "street food", "street snacks", "local snacks",
    ],
    "science fiction": [
        "science fiction", "sci-fi", "science-fiction",
    ],
    "sci-fi": [
        "sci-fi", "science fiction", "science-fiction",
    ],
    "indian classical": [
        "indian classical", "indian classical music",
        "hindustani classical", "carnatic music",
        "indian raga", "raga",
    ],
    "relaxing music": [
        "relaxing music", "relaxation music", "calm music",
        "soothing music", "ambient music",
        "meditative music", "instrumental music",
    ],
    "relaxing instrumental piano": [
        "relaxing instrumental piano", "instrumental piano",
        "piano music", "relaxing music", "classical piano",
        "ambient piano",
    ],
    "space exploration": [
        "space exploration", "space adventure", "outer space",
        "space travel", "space mission", "interstellar",
    ],
    "cultural heritage": [
        "cultural heritage", "heritage sites", "historical sites",
        "historic landmarks", "cultural landmarks",
        "history and culture",
    ],
}

# Known franchises are used only to improve diversity.
# They do not determine whether a recommendation is relevant.
MOVIE_FRANCHISES = {
    "star trek": [
        "star trek",
    ],
    "star wars": [
        "star wars",
    ],
    "marvel": [
        "marvel cinematic universe",
        "marvel studios",
        "avengers",
        "iron man",
        "captain america",
        "thor",
        "guardians of the galaxy",
        "ant man",
        "doctor strange",
        "black panther",
        "spider man",
        "spider-man",
    ],
    "dc": [
        "dc comics",
        "dc extended universe",
        "batman",
        "superman",
        "wonder woman",
        "aquaman",
        "justice league",
    ],
    "jurassic": [
        "jurassic park",
        "jurassic world",
    ],
    "planet of the apes": [
        "planet of the apes",
    ],
    "alien": [
        "alien",
        "aliens",
    ],
    "predator": [
        "predator",
    ],
    "terminator": [
        "terminator",
    ],
    "the matrix": [
        "the matrix",
    ],
    "avatar": [
        "avatar",
    ],
    "transformers": [
        "transformers",
    ],
    "men in black": [
        "men in black",
    ],
    "back to the future": [
        "back to the future",
    ],
    "ghostbusters": [
        "ghostbusters",
    ],
    "mad max": [
        "mad max",
    ],
    "blade runner": [
        "blade runner",
    ],
    "dune": [
        "dune",
    ],
    "the hunger games": [
        "the hunger games",
    ],
    "divergent": [
        "divergent",
    ],
    "maze runner": [
        "maze runner",
    ],
    "resident evil": [
        "resident evil",
    ],
    "robocop": [
        "robocop",
    ],
    "x-men": [
        "x men",
        "x-men",
    ],
    "mission impossible": [
        "mission impossible",
    ],
    "fast and furious": [
        "fast and furious",
        "fast furious",
    ],
    "godzilla": [
        "godzilla",
    ],
    "king kong": [
        "king kong",
    ],
    "toy story": [
        "toy story",
    ],
    "shrek": [
        "shrek",
    ],
    "how to train your dragon": [
        "how to train your dragon",
    ],
}

# These labels are used for ranking diversity, not as proof
# that an entity actually offers a particular dish.
FOOD_DIVERSITY_GROUPS = {
    "chaat": [
        "chaat", "aloo tikki", "papdi chaat",
        "dahi puri", "sev puri", "bhel puri",
    ],
    "pani_puri": [
        "pani puri", "pani poori", "golgappa",
        "gol gappa", "puchka", "phuchka",
    ],
    "rolls": [
        "kathi roll", "kati roll", "frankie",
        "street roll", "wrap",
    ],
    "sandwiches": [
        "sandwich", "vada pav", "dabeli",
        "burger", "toast",
    ],
    "south_indian": [
        "dosa", "idli", "uttapam", "vada",
        "sambar", "south indian",
    ],
    "indo_chinese": [
        "momos", "manchurian", "chow mein",
        "noodles", "fried rice", "indo chinese",
    ],
    "sweets": [
        "jalebi", "gulab jamun", "kulfi",
        "rasgulla", "mithai", "dessert",
        "sweet shop", "falooda",
    ],
    "grilled": [
        "kebab", "kabab", "tikka", "tandoori",
        "grilled", "seekh",
    ],
    "beverages": [
        "chai", "tea", "lassi", "juice",
        "coffee", "sharbat", "beverage",
    ],
    "meals": [
        "thali", "biryani", "paratha", "pav bhaji",
        "rice", "meal", "curry",
    ],
}

FOOD_RESTAURANT_TERMS = {
    "restaurant", "restaurants", "cafe", "cafes",
    "eatery", "eateries", "food court",
    "diner", "food outlet",
}


def normalize(value: Any) -> str:
    """Convert supported scalar values to normalized lowercase text."""
    if value is None or isinstance(value, (dict, list, tuple, set)):
        return ""

    text = str(value).lower().strip()
    text = text.replace("&", " and ")
    text = re.sub(r"[_/|-]+", " ", text)
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def get_properties(entity: dict) -> dict:
    """Safely retrieve Qloo entity properties."""
    if not isinstance(entity, dict):
        return {}

    properties = entity.get("properties", {})
    return properties if isinstance(properties, dict) else {}


def text_from_value(value: Any) -> str:
    """Extract searchable text from strings, lists, and tag objects."""
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, dict):
        parts = []

        for key in (
            "name", "value", "label", "description",
            "title", "id", "url",
        ):
            item = value.get(key)
            if isinstance(item, (str, int, float)):
                parts.append(str(item))

        return " ".join(parts)

    if isinstance(value, (list, tuple, set)):
        return " ".join(
            text_from_value(item)
            for item in value
            if item is not None
        )

    return ""


def get_text(entity: dict, *keys: str) -> str:
    """Collect text from entity fields and properties."""
    if not isinstance(entity, dict):
        return ""

    properties = get_properties(entity)
    parts = []

    for key in keys:
        value = entity.get(key)
        if value is None:
            value = properties.get(key)

        extracted = text_from_value(value)
        if extracted:
            parts.append(extracted)

    return " ".join(parts)


def get_field(entity: dict, *keys: str) -> str:
    """Return the first available field as text."""
    if not isinstance(entity, dict):
        return ""

    properties = get_properties(entity)

    for key in keys:
        value = entity.get(key)
        if value is None:
            value = properties.get(key)

        extracted = text_from_value(value).strip()
        if extracted:
            return extracted

    return ""


def get_image_url(entity: dict) -> str | None:
    """Find an HTTP image URL if Qloo supplies one."""
    if not isinstance(entity, dict):
        return None

    properties = get_properties(entity)

    candidates = [
        entity.get("image"), entity.get("image_url"),
        entity.get("photo"), entity.get("thumbnail"),
        properties.get("image"), properties.get("image_url"),
        properties.get("photo"), properties.get("thumbnail"),
    ]

    for candidate in candidates:
        if isinstance(candidate, str):
            url = candidate.strip()
            if url.startswith(("https://", "http://")):
                return url

        if isinstance(candidate, dict):
            url = (
                candidate.get("url")
                or candidate.get("image_url")
                or candidate.get("src")
            )

            if isinstance(url, str) and url.startswith(
                ("https://", "http://")
            ):
                return url

    return None


def get_genres(entity: dict) -> list[str]:
    """Extract genre names from Qloo entity data."""
    if not isinstance(entity, dict):
        return []

    properties = get_properties(entity)
    genres = []

    for source in (entity, properties):
        for key in ("genres", "genre", "primary_genre"):
            value = source.get(key)
            if value is None:
                continue

            items = (
                value if isinstance(value, (list, tuple, set))
                else [value]
            )

            for item in items:
                genre = normalize(text_from_value(item))
                if genre and genre not in genres:
                    genres.append(genre)

    return genres


def split_interests(interests: Any) -> list[str]:
    """Split comma-, semicolon-, or newline-separated interests."""
    if isinstance(interests, (list, tuple, set)):
        raw_items = list(interests)
    else:
        raw_items = re.split(r"[,;\n]+", str(interests or ""))

    result = []

    for item in raw_items:
        value = normalize(item)
        if value and value not in result:
            result.append(value)

    return result


def expand_interest(interest: str) -> list[str]:
    """Expand known phrases into useful alternatives."""
    normalized = normalize(interest)

    if not normalized:
        return []

    alternatives = [normalized]

    for original, synonyms in INTEREST_SYNONYMS.items():
        if normalized == normalize(original):
            alternatives.extend(synonyms)

    result = []

    for alternative in alternatives:
        value = normalize(alternative)
        if value and value not in result:
            result.append(value)

    return result


def get_interest_terms(interests: Any) -> list[str]:
    """Return useful interest phrases and meaningful words."""
    terms = []

    for phrase in split_interests(interests):
        if phrase not in terms:
            terms.append(phrase)

        for alternative in expand_interest(phrase):
            if alternative not in terms:
                terms.append(alternative)

        for word in phrase.split():
            if (
                len(word) >= 4
                and word not in STOP_WORDS
                and word not in terms
            ):
                terms.append(word)

    return terms


def phrase_in_text(phrase: str, text: str) -> bool:
    """Check a normalized phrase against normalized text."""
    phrase = normalize(phrase)
    text = normalize(text)

    if not phrase or not text:
        return False

    return f" {phrase} " in f" {text} "


def get_entity_metadata(entity: dict) -> dict:
    """Collect metadata used for relevance and category matching."""
    if not isinstance(entity, dict):
        entity = {}

    properties = get_properties(entity)

    title = get_field(
        entity, "name", "title", "entity_name", "display_name"
    )

    description = get_field(
        entity, "description", "short_description",
        "overall_description", "overview", "summary"
    )

    metadata_keys = [
        "akas", "genres", "genre", "primary_genre",
        "tags", "keywords", "themes", "categories",
        "cuisine_description", "specialty_dishes",
        "speciality_dishes", "overall_description",
        "good_for", "menu_url", "food_type", "cuisine",
        "dish", "dishes", "location", "address",
        "known_for", "interests", "type", "entity_type",
        "destination", "country", "region", "city",
        "attractions", "landmarks", "cultural_significance",
        "heritage", "natural_features", "activities",
    ]

    metadata_parts = []

    for key in metadata_keys:
        value = entity.get(key)
        if value is None:
            value = properties.get(key)

        extracted = text_from_value(value)
        if extracted:
            metadata_parts.append(extracted)

    metadata_text = " ".join(metadata_parts)
    entity_type = get_field(entity, "entity_type", "type")

    all_text = normalize(" ".join([
        title, description, metadata_text, entity_type
    ]))

    return {
        "title": title,
        "description": description,
        "genres": get_genres(entity),
        "metadata": metadata_text,
        "entity_type": normalize(entity_type),
        "all_text": all_text,
    }


def match_interests(
    interests: Any,
    metadata: dict,
) -> tuple[list[str], int, list[str]]:
    """Match user interests against available entity information."""
    title = normalize(metadata.get("title", ""))
    description = normalize(metadata.get("description", ""))
    genres = normalize(" ".join(metadata.get("genres", [])))
    other_metadata = normalize(metadata.get("metadata", ""))
    all_text = normalize(metadata.get("all_text", ""))

    matched_interests = []
    matched_phrases = []
    score = 0

    for interest in split_interests(interests):
        alternatives = expand_interest(interest)

        title_match = any(
            phrase_in_text(p, title) for p in alternatives
        )
        genre_match = any(
            phrase_in_text(p, genres) for p in alternatives
        )
        description_match = any(
            phrase_in_text(p, description) for p in alternatives
        )
        metadata_match = any(
            phrase_in_text(p, other_metadata) for p in alternatives
        )

        if title_match:
            score += 95
        elif genre_match:
            score += 90
        elif description_match:
            score += 75
        elif metadata_match:
            score += 70
        else:
            meaningful_words = [
                word for word in interest.split()
                if len(word) >= 4 and word not in STOP_WORDS
            ]

            if not meaningful_words:
                continue

            matched_words = [
                word for word in meaningful_words
                if phrase_in_text(word, all_text)
            ]

            required_matches = (
                1 if len(meaningful_words) == 1 else 2
            )

            if len(matched_words) < required_matches:
                continue

            score += 55
            matched_phrases.extend(matched_words)

        matched_interests.append(interest)
        matched_phrases.append(interest)

    return (
        list(dict.fromkeys(matched_interests)),
        score,
        list(dict.fromkeys(matched_phrases)),
    )


def category_confirmed(category: str, metadata: dict) -> bool:
    """Check for evidence that an entity belongs to the category."""
    normalized_category = normalize(category)

    category_name = next(
        (
            value for key, value in SUPPORTED_CATEGORIES.items()
            if key == normalized_category
        ),
        category,
    )

    all_text = normalize(metadata.get("all_text", ""))
    entity_type = normalize(metadata.get("entity_type", ""))

    if category_name not in CATEGORY_TERMS:
        return False

    if category_name == "Movies":
        if "movie" in entity_type or "film" in entity_type:
            return True

    if category_name == "Music":
        if "artist" in entity_type or "music" in entity_type:
            return True

    if category_name == "Travel":
        if "destination" in entity_type:
            return True

    if category_name == "Food":
        food_evidence = [
            "cuisine_description", "specialty_dishes",
            "speciality_dishes", "food_type", "cuisine",
            "dish", "dishes", "menu_url", "restaurant",
            "street food", "indian food", "indian cuisine",
            "food", "culinary", "bakery", "seafood",
        ]

        food_text = normalize(" ".join([
            metadata.get("description", ""),
            metadata.get("metadata", ""),
            metadata.get("title", ""),
            entity_type,
        ]))

        return any(
            phrase_in_text(term, food_text)
            for term in food_evidence
        )

    return any(
        phrase_in_text(term, all_text)
        for term in CATEGORY_TERMS[category_name]
    )


def get_food_group(recommendation: dict) -> str:
    """
    Infer a food group only from evidence in available entity text.
    Unknown entities remain in the general group.
    """
    searchable = normalize(" ".join([
        recommendation.get("title", ""),
        recommendation.get("description", ""),
        " ".join(recommendation.get("matched_terms", [])),
        " ".join(recommendation.get("genres", [])),
    ]))

    priority = [
        "pani_puri", "chaat", "rolls", "south_indian",
        "indo_chinese", "sweets", "grilled", "beverages",
        "sandwiches", "meals",
    ]

    for group in priority:
        terms = FOOD_DIVERSITY_GROUPS[group]

        if any(phrase_in_text(term, searchable) for term in terms):
            return group

    return "general"


def get_movie_franchise(recommendation: dict) -> str:
    """
    Identify a known franchise from the available movie title
    and description. Unknown movies are not forced into a franchise.
    """
    searchable = normalize(" ".join([
        recommendation.get("title", ""),
        recommendation.get("description", ""),
    ]))

    for franchise, aliases in MOVIE_FRANCHISES.items():
        for alias in aliases:
            if phrase_in_text(alias, searchable):
                return franchise

    return "standalone"


def get_movie_diversity_group(recommendation: dict) -> str:
    """
    Estimate a broad movie style using available genres and text.
    This is a diversity hint, not a definitive classification.
    """
    searchable = normalize(" ".join([
        recommendation.get("title", ""),
        recommendation.get("description", ""),
        " ".join(recommendation.get("genres", [])),
    ]))

    genre_groups = {
        "space_science_fiction": [
            "space opera", "space adventure", "space exploration",
            "outer space", "space travel", "interstellar",
            "starship", "alien planet",
        ],
        "cyberpunk": [
            "cyberpunk", "dystopian technology",
            "virtual reality", "artificial intelligence",
            "cybernetic",
        ],
        "dystopian": [
            "dystopian", "post apocalyptic",
            "post-apocalyptic", "totalitarian",
        ],
        "time_travel": [
            "time travel", "time loop", "time machine",
            "alternate timeline",
        ],
        "first_contact": [
            "first contact", "alien contact",
            "extraterrestrial communication",
        ],
        "thriller_horror": [
            "science fiction horror", "sci fi horror",
            "psychological horror", "horror thriller",
        ],
        "comedy": [
            "science fiction comedy", "sci fi comedy",
            "science fiction satire", "parody",
        ],
        "action_adventure": [
            "science fiction action", "sci fi action",
            "action adventure", "space battle",
        ],
        "drama": [
            "science fiction drama", "sci fi drama",
            "character drama",
        ],
    }

    for group, terms in genre_groups.items():
        if any(phrase_in_text(term, searchable) for term in terms):
            return group

    return "general"


def get_dedup_text(recommendation: dict) -> str:
    """Normalize a title for duplicate detection."""
    title = normalize(recommendation.get("title", ""))

    title = re.sub(
        r"\b(restaurant|restaurants|cafe|cafes|official|india)\b",
        " ",
        title,
    )

    return re.sub(r"\s+", " ", title).strip()


def are_similar_titles(first: str, second: str) -> bool:
    """
    Detect exact and near-duplicate names.
    Similarity is a heuristic, so short titles use stricter checks.
    """
    first = get_dedup_text({"title": first})
    second = get_dedup_text({"title": second})

    if not first or not second:
        return False

    if first == second:
        return True

    first_tokens = set(first.split())
    second_tokens = set(second.split())

    if not first_tokens or not second_tokens:
        return False

    overlap = len(first_tokens & second_tokens) / max(
        len(first_tokens | second_tokens), 1
    )

    ratio = SequenceMatcher(None, first, second).ratio()

    if min(len(first), len(second)) < 8:
        return overlap >= 0.8 and ratio >= 0.9

    return overlap >= 0.8 or ratio >= 0.9


def score_recommendation(
    entity: dict,
    interests: Any,
    category: str,
) -> dict | None:
    """Score one Qloo entity and reject weak matches."""
    if not isinstance(entity, dict):
        return None

    metadata = get_entity_metadata(entity)

    entity_id = (
        entity.get("entity_id")
        or entity.get("id")
        or entity.get("entityId")
    )

    if not entity_id:
        return None

    if not category_confirmed(category, metadata):
        return None

    matched_interests, raw_score, matched_phrases = (
        match_interests(interests, metadata)
    )

    if not matched_interests or raw_score < 60:
        return None

    title = metadata.get("title") or "Untitled recommendation"
    description = metadata.get("description") or (
        "No description was provided by Qloo."
    )

    recommendation = {
        "id": str(entity_id),
        "entity_id": str(entity_id),
        "title": title,
        "name": title,
        "description": description,
        "category": category,
        "score": min(raw_score, 100),
        "matched_interests": matched_interests,
        "matched_terms": matched_phrases,
        "genres": metadata.get("genres", []),
        "image_url": get_image_url(entity),
        "source": "Qloo",
        "reason": (
            "Matched your interests using the entity's available "
            "description, genre, or metadata."
        ),
    }

    if category == "Food":
        recommendation["diversity_group"] = get_food_group(
            recommendation
        )

    if category == "Movies":
        recommendation["movie_franchise"] = get_movie_franchise(
            recommendation
        )
        recommendation["movie_diversity_group"] = (
            get_movie_diversity_group(recommendation)
        )

    return recommendation


def select_diverse_recommendations(
    candidates: list[dict],
    category: str,
    limit: int = RESULT_LIMIT,
) -> list[dict]:
    """
    Greedy relevance-first selection with duplicate control.

    Food: apply a soft penalty to repeated food groups.
    Movies: apply soft penalties to repeated franchises and styles.

    Diversity is a ranking hint. It never makes an unrelated entity
    eligible, and the function can return fewer than limit results
    when too few distinct candidates are available.
    """
    if not candidates or limit <= 0:
        return []

    remaining = sorted(
        candidates,
        key=lambda item: item.get("score", 0),
        reverse=True,
    )

    selected = []
    seen_ids = set()
    seen_titles = set()

    food_group_counts = {}
    franchise_counts = {}
    movie_style_counts = {}

    while remaining and len(selected) < limit:
        best_item = None
        best_adjusted_score = float("-inf")

        for item in remaining:
            item_id = str(item.get("id", ""))
            title = item.get("title", "")

            if item_id in seen_ids:
                continue

            if any(
                are_similar_titles(title, previous_title)
                for previous_title in seen_titles
            ):
                continue

            base_score = float(item.get("score", 0))
            adjusted_score = base_score

            if category == "Food":
                group = item.get("diversity_group", "general")
                repeat_count = food_group_counts.get(group, 0)

                # Prefer other food groups when their relevance is close.
                adjusted_score -= min(repeat_count * 18, 36)

            elif category == "Movies":
                franchise = item.get(
                    "movie_franchise", "standalone"
                )
                style = item.get(
                    "movie_diversity_group", "general"
                )

                # Standalone films are not treated as one shared franchise.
                if franchise != "standalone":
                    franchise_repeat_count = franchise_counts.get(
                        franchise, 0
                    )
                    adjusted_score -= min(
                        franchise_repeat_count * 24, 48
                    )

                style_repeat_count = movie_style_counts.get(style, 0)
                if style != "general":
                    adjusted_score -= min(
                        style_repeat_count * 8, 16
                    )

            if adjusted_score > best_adjusted_score:
                best_item = item
                best_adjusted_score = adjusted_score

        if best_item is None:
            break

        selected.append(best_item)

        selected_id = str(best_item.get("id", ""))
        selected_title = best_item.get("title", "")

        seen_ids.add(selected_id)
        seen_titles.add(selected_title)

        if category == "Food":
            group = best_item.get("diversity_group", "general")
            food_group_counts[group] = (
                food_group_counts.get(group, 0) + 1
            )

        elif category == "Movies":
            franchise = best_item.get(
                "movie_franchise", "standalone"
            )
            style = best_item.get(
                "movie_diversity_group", "general"
            )

            if franchise != "standalone":
                franchise_counts[franchise] = (
                    franchise_counts.get(franchise, 0) + 1
                )

            if style != "general":
                movie_style_counts[style] = (
                    movie_style_counts.get(style, 0) + 1
                )

        remaining = [
            item for item in remaining
            if str(item.get("id", "")) != selected_id
        ]

    return selected


def create_recommendation_request(
    interests: Any,
    category: str,
    plan: Any = None,
    cultural_data: Any = None,
) -> dict:
    """
    Create relevance-ranked, diversity-aware recommendations.

    Keeps the function signature and response keys used by main.py.
    """
    normalized_category = normalize(category)

    category_name = next(
        (
            value for key, value in SUPPORTED_CATEGORIES.items()
            if key == normalized_category
        ),
        str(category or "").strip(),
    )

    if category_name not in CATEGORY_TERMS:
        return {
            "status": "error",
            "recommendation_status": "no_results",
            "category": category_name,
            "interests": interests,
            "recommendations": [],
            "results": [],
            "count": 0,
            "message": (
                f"Unsupported category: {category_name}. "
                "Use Movies, Music, Food, or Travel."
            ),
        }

    if isinstance(cultural_data, dict):
        entities = cultural_data.get("results", [])
    elif isinstance(cultural_data, list):
        entities = cultural_data
    else:
        entities = []

    if not isinstance(entities, list):
        entities = []

    candidates = []
    seen_ids = set()

    for entity in entities:
        if not isinstance(entity, dict):
            continue

        entity_id = (
            entity.get("entity_id")
            or entity.get("id")
            or entity.get("entityId")
        )

        if not entity_id:
            continue

        entity_id = str(entity_id)

        if entity_id in seen_ids:
            continue

        recommendation = score_recommendation(
            entity=entity,
            interests=interests,
            category=category_name,
        )

        metadata = get_entity_metadata(entity)

        print(
            "[RECOMMENDER DEBUG]",
            {
                "category": category_name,
                "title": metadata.get("title"),
                "entity_type": metadata.get("entity_type"),
                "category_ok": category_confirmed(
                    category_name, metadata
                ),
                "matched_interests": (
                    recommendation or {}
                ).get("matched_interests", []),
                "match_score": (
                    recommendation or {}
                ).get("score", 0),
                "food_group": (
                    recommendation or {}
                ).get("diversity_group"),
                "movie_franchise": (
                    recommendation or {}
                ).get("movie_franchise"),
                "movie_style": (
                    recommendation or {}
                ).get("movie_diversity_group"),
                "has_description": bool(
                    metadata.get("description")
                ),
            },
        )

        if recommendation is None:
            continue

        seen_ids.add(entity_id)
        candidates.append(recommendation)

    recommendations = select_diverse_recommendations(
        candidates=candidates,
        category=category_name,
        limit=RESULT_LIMIT,
    )

    if recommendations:
        return {
            "status": "success",
            "recommendation_status": "success",
            "category": category_name,
            "interests": interests,
            "plan": plan,
            "recommendations": recommendations,
            "results": recommendations,
            "count": len(recommendations),
            "message": (
                f"Found {len(recommendations)} relevant "
                f"{category_name.lower()} recommendations."
            ),
            "source": "Qloo",
        }

    return {
        "status": "success",
        "recommendation_status": "no_results",
        "category": category_name,
        "interests": interests,
        "plan": plan,
        "recommendations": [],
        "results": [],
        "count": 0,
        "message": (
            "Qloo research returned no results that met the "
            "current category and interest relevance checks. "
            "Try a more specific or alternative search phrase."
        ),
        "source": "Qloo",
            }












