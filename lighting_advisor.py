
import re


CULTURAL_SEEDS = {
    "Music": [
        "indie rock", "indie pop", "classical music",
        "classical", "hip hop", "jazz", "rock", "pop",
    ],
    "Movies": [
        "science fiction", "sci-fi", "thriller",
        "comedy", "horror", "drama", "animation",
    ],
    "Food": [
        "indian street food", "indian food",
        "italian food", "japanese food", "vegan food",
    ],
    "Travel": [
        "mountain destinations", "adventure travel",
        "historical places", "mountains", "beaches",
    ],
}


def is_lighting_query(text: str) -> bool:
    text = (text or "").casefold()
    terms = (
        "lighting", "light setup", "room light",
        "room lights", "light for my room", "light in my room",
        "bulb", "lamp", "ambient light", "task lighting",
        "bedroom light", "living room light", "study room light",
    )
    return any(term in text for term in terms)


def extract_taste_seed(text: str):
    """Find an explicitly stated, supported cultural taste."""
    normalized = re.sub(r"[^a-z0-9]+", " ", (text or "").casefold())

    matches = []
    for category, phrases in CULTURAL_SEEDS.items():
        for phrase in phrases:
            pattern = r"\b" + re.escape(phrase) + r"\b"
            if re.search(pattern, normalized):
                matches.append((len(phrase), category, phrase))

    if not matches:
        return None

    matches.sort(reverse=True)
    _, category, phrase = matches[0]
    return {"category": category, "query": phrase}


def create_lighting_recommendation(
    interests: str,
    qloo_context=None,
    taste_seed=None,
):
    text = (interests or "").casefold()
    qloo_context = qloo_context or []

    if "bedroom" in text:
        room = "Bedroom"
    elif "study" in text or "desk" in text:
        room = "Study room"
    elif "kitchen" in text:
        room = "Kitchen"
    elif "bathroom" in text:
        room = "Bathroom"
    else:
        room = "Living room"

    if any(word in text for word in ("focus", "study", "reading", "work")):
        activity = "focused tasks"
        task_advice = (
            "Use a well-positioned task lamp and even room lighting. "
            "Avoid glare on books and screens."
        )
    elif any(word in text for word in ("relax", "calm", "sleep", "cozy", "warm")):
        activity = "relaxation"
        task_advice = (
            "Use warm, dimmable ambient lighting and indirect lamps. "
            "Keep bright light away from the direct line of sight."
        )
    elif any(word in text for word in ("gaming", "movie", "cinema", "entertainment")):
        activity = "entertainment"
        task_advice = (
            "Try soft indirect lighting behind the screen and adjustable "
            "ambient lights. Avoid reflections on the display."
        )
    else:
        activity = "everyday use"
        task_advice = (
            "Combine general ambient lighting with a separate task light "
            "where needed. Use multiple light sources instead of relying "
            "on one harsh ceiling light."
        )

    if any(word in text for word in ("minimalist", "minimal", "simple")):
        style = "Minimal and clean"
        style_advice = (
            "Choose discreet fixtures, simple shapes and concealed "
            "indirect lighting."
        )
    elif any(word in text for word in ("modern", "smart", "colorful", "rgb")):
        style = "Modern and adjustable"
        style_advice = (
            "Consider adjustable fixtures or smart bulbs, with subtle "
            "accent lighting rather than constant saturated colors."
        )
    elif taste_seed and taste_seed["query"] in ("jazz", "classical", "classical music"):
        style = "Calm, layered ambience"
        style_advice = (
            "Try warm ambient light, a shaded floor or table lamp, "
            "and a separate dimmable accent source."
        )
    elif taste_seed and taste_seed["query"] in ("sci-fi", "science fiction"):
        style = "Contemporary accent lighting"
        style_advice = (
            "Consider indirect LED accents and adjustable white light. "
            "Keep the main room lighting comfortable and functional."
        )
    else:
        style = "Comfort-focused"
        style_advice = (
            "Use layered lighting with a comfortable ambient source, "
            "a practical task light and optional accent lighting."
        )

    recommendations = [
        {
            "title": f"{room}: {style}",
            "category": "Lighting",
            "description": style_advice,
            "image_url": None,
            "match_score": 85,
            "match_reason": (
                "Design guidance based on the stated room and style "
                "preferences; this is not a Qloo-ranked lighting product."
            ),
            "source": "Lighting rules",
        },
        {
            "title": f"Lighting for {activity}",
            "category": "Lighting",
            "description": task_advice,
            "image_url": None,
            "match_score": 90,
            "match_reason": (
                "Advice based on the activity and comfort requirements "
                "stated in the request."
            ),
            "source": "Lighting rules",
        },
        {
            "title": "Practical lighting setup",
            "category": "Lighting",
            "description": (
                "Prefer dimmable, appropriately placed fixtures. "
                "Choose bulb brightness and color temperature for the "
                "room's purpose, and follow fixture and electrical "
                "safety instructions."
            ),
            "image_url": None,
            "match_score": 80,
            "match_reason": (
                "General functional guidance; exact bulb specifications "
                "depend on room size and fixture requirements."
            ),
            "source": "Lighting rules",
        },
    ]

    return {
        "interests": interests,
        "category": "Lighting",
        "recommendation_status": "success",
        "recommendations": recommendations,
        "personalization": {
            "room": room,
            "activity": activity,
            "style": style,
            "explicit_taste_seed": taste_seed,
            "qloo_entities": qloo_context,
            "qloo_personalization_status": (
                "taste_context_available" if qloo_context
                else "no_verified_taste_context"
            ),
        },
        "message": (
            "Created room-lighting guidance. Cultural taste context "
            "is reported separately from lighting rules."
        ),
    }
