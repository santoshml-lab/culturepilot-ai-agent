
import json
import os
import re

import requests



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
        "room lights", "light for my room",
        "light in my room", "bulb", "lamp",
        "ambient light", "task lighting",
        "bedroom light", "living room light",
        "study room light",
    )

    return any(term in text for term in terms)


def extract_taste_seed(text: str):
    """Find an explicitly stated, supported cultural taste."""
    normalized = re.sub(
        r"[^a-z0-9]+",
        " ",
        (text or "").casefold(),
    )

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

    return {
        "category": category,
        "query": phrase,
    }


def generate_groq_lighting_advice(
    interests: str,
    room: str,
    activity: str,
    style: str,
    qloo_context=None,
):
    """
    Generate personalized lighting recommendations with Groq.
    Return None if the API is unavailable or the response is invalid.
    """

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return None

    qloo_context = qloo_context or []

    prompt = f"""
You are CulturePilot AI, a personalized room-lighting advisor.

User request: {interests}
Room: {room}
Activity: {activity}
Preferred style: {style}
Qloo cultural context: {json.dumps(qloo_context)}

Requirements:
1. Return exactly three useful lighting recommendations.
2. Personalize advice using the room, activity and available cultural context.
3. Treat cultural preferences as inspiration, not as proof of lighting preferences.
4. Never claim Qloo ranked or recommended lighting products.
5. Do not invent cultural data, product specifications or prices.
6. Include practical, comfortable and electrically safe advice.
7. Use concise, clear English.

Return valid JSON only, using this structure:
{{
  "recommendations": [
    {{
      "title": "Short recommendation title",
      "description": "Practical lighting advice",
      "match_reason": "Why this recommendation fits the request"
    }}
  ]
}}
"""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-oss-20b",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You provide practical, honest and "
                            "personalized lighting recommendations. "
                            "Return valid JSON without markdown."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "temperature": 0.4,
            },
            timeout=30,
        )

        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        content = content.strip()

        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0].strip()

        data = json.loads(content)
        items = data.get("recommendations", [])

        if not isinstance(items, list) or len(items) != 3:
            return None

        recommendations = []

        for item in items:
            if not isinstance(item, dict):
                return None

            title = item.get("title")
            description = item.get("description")
            reason = item.get("match_reason")

            if not all(
                isinstance(value, str) and value.strip()
                for value in (title, description, reason)
            ):
                return None

            recommendations.append({
                "title": title.strip(),
                "category": "Lighting",
                "description": description.strip(),
                "image_url": None,
                "match_score": None,
                "match_reason": reason.strip(),
                "source": "Groq AI",
            })

        return recommendations

    except (
        requests.RequestException,
        ValueError,
        KeyError,
        TypeError,
    ):
        return None


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

    if any(
        word in text
        for word in ("focus", "study", "reading", "work")
    ):
        activity = "focused tasks"
        task_advice = (
            "Use a well-positioned task lamp and even room lighting. "
            "Avoid glare on books and screens."
        )

    elif any(
        word in text
        for word in ("relax", "calm", "sleep", "cozy", "warm")
    ):
        activity = "relaxation"
        task_advice = (
            "Use warm, dimmable ambient lighting and indirect lamps. "
            "Keep bright light away from the direct line of sight."
        )

    elif any(
        word in text
        for word in ("gaming", "movie", "cinema", "entertainment")
    ):
        activity = "entertainment"
        task_advice = (
            "Try soft indirect lighting behind the screen and "
            "adjustable ambient lights. Avoid screen reflections."
        )

    else:
        activity = "everyday use"
        task_advice = (
            "Combine general ambient lighting with a separate task "
            "light where needed. Avoid relying on one harsh ceiling light."
        )

    if any(
        word in text
        for word in ("minimalist", "minimal", "simple")
    ):
        style = "Minimal and clean"
        style_advice = (
            "Choose discreet fixtures, simple shapes and concealed "
            "indirect lighting."
        )

    elif any(
        word in text
        for word in ("modern", "smart", "colorful", "rgb")
    ):
        style = "Modern and adjustable"
        style_advice = (
            "Consider adjustable fixtures or smart bulbs, with subtle "
            "accent lighting rather than constant saturated colors."
        )

    elif (
        taste_seed
        and taste_seed.get("query")
        in ("jazz", "classical", "classical music")
    ):
        style = "Calm, layered ambience"
        style_advice = (
            "Try warm ambient light, a shaded floor or table lamp, "
            "and a separate dimmable accent source."
        )

    elif (
        taste_seed
        and taste_seed.get("query")
        in ("sci-fi", "science fiction")
    ):
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

    # Reliable local recommendations are always available as fallback.
    recommendations = [
        {
            "title": f"{room}: {style}",
            "category": "Lighting",
            "description": style_advice,
            "image_url": None,
            "match_score": None,
            "match_reason": (
                "Guidance based on the stated room and style preferences. "
                "This is not a Qloo-ranked lighting product."
            ),
            "source": "Lighting rules",
        },
        {
            "title": f"Lighting for {activity}",
            "category": "Lighting",
            "description": task_advice,
            "image_url": None,
            "match_score": None,
            "match_reason": (
                "Advice based on the requested activity and comfort needs."
            ),
            "source": "Lighting rules",
        },
        {
            "title": "Practical lighting setup",
            "category": "Lighting",
            "description": (
                "Use appropriately placed, dimmable fixtures where "
                "suitable. Select brightness and color temperature for "
                "the room's purpose, and follow electrical safety "
                "instructions."
            ),
            "image_url": None,
            "match_score": None,
            "match_reason": (
                "General functional guidance. Exact bulb specifications "
                "depend on room size and fixture requirements."
            ),
            "source": "Lighting rules",
        },
    ]

    # Replace the rule-based recommendations only after valid AI output.
    ai_recommendations = generate_groq_lighting_advice(
        interests=interests,
        room=room,
        activity=activity,
        style=style,
        qloo_context=qloo_context,
    )

    if ai_recommendations:
        recommendations = ai_recommendations
        recommendation_source = "Groq AI"
        recommendation_status = "success"
        message = "Personalized lighting advice generated by Groq AI."
    else:
        recommendation_source = "Lighting rules (fallback)"
        recommendation_status = "success"
        message = (
            "Rule-based lighting advice returned because Groq AI "
            "was unavailable or returned invalid data."
        )

    return {
        "interests": interests,
        "category": "Lighting",
        "recommendation_status": recommendation_status,
        "recommendation_source": recommendation_source,
        "recommendations": recommendations,
        "personalization": {
            "room": room,
            "activity": activity,
            "style": style,
            "explicit_taste_seed": taste_seed,
            "qloo_entities": qloo_context,
            "qloo_personalization_status": (
                "taste_context_available"
                if qloo_context
                else "no_verified_taste_context"
            ),
        },
        "message": message,
    }

