import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

BASE_URL = "https://places.googleapis.com/v1"


def _headers(field_mask: str | None = None) -> dict[str, str]:
    settings = get_settings()
    h: dict[str, str] = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_API_KEY,
    }
    if field_mask:
        h["X-Goog-FieldMask"] = field_mask
    return h


async def autocomplete(query: str) -> list[dict]:
    """Call Places Autocomplete (New) and enrich each suggestion with viewport bounds."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{BASE_URL}/places:autocomplete",
            headers=_headers(),
            json={"input": query},
        )
        resp.raise_for_status()
        data = resp.json()

    suggestions = data.get("suggestions", [])
    results: list[dict] = []

    async with httpx.AsyncClient(timeout=10) as client:
        for suggestion in suggestions:
            place_prediction = suggestion.get("placePrediction")
            if not place_prediction:
                continue

            place_id = place_prediction.get("placeId")
            description = (
                place_prediction.get("text", {}).get("text", "")
                or place_prediction.get("structuredFormat", {}).get("mainText", {}).get("text", "")
            )

            viewport = None
            if place_id:
                try:
                    detail_resp = await client.get(
                        f"{BASE_URL}/places/{place_id}",
                        headers=_headers("viewport"),
                    )
                    detail_resp.raise_for_status()
                    detail = detail_resp.json()
                    vp = detail.get("viewport")
                    if vp:
                        viewport = {
                            "low": {
                                "latitude": vp["low"]["latitude"],
                                "longitude": vp["low"]["longitude"],
                            },
                            "high": {
                                "latitude": vp["high"]["latitude"],
                                "longitude": vp["high"]["longitude"],
                            },
                        }
                except httpx.HTTPError:
                    logger.warning("Failed to fetch viewport for place_id=%s", place_id)

            results.append(
                {
                    "description": description,
                    "place_id": place_id or "",
                    "viewport": viewport,
                }
            )

    return results


async def search_text(sector: str, bounds: dict, max_reviews: int, min_rating: int) -> list[dict]:
    """Search for businesses in the given bounds using Places searchText.

    Returns only businesses with a website and fewer than 10 reviews.
    """
    payload = {
        "textQuery": sector,
        "locationRestriction": {
            "rectangle": {
                "low": {
                    "latitude": bounds["low"]["latitude"],
                    "longitude": bounds["low"]["longitude"],
                },
                "high": {
                    "latitude": bounds["high"]["latitude"],
                    "longitude": bounds["high"]["longitude"],
                },
            }
        },
    }

    field_mask = "places.displayName,places.websiteUri,places.userRatingCount,places.rating"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{BASE_URL}/places:searchText",
            headers=_headers(field_mask),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    places = data.get("places", [])
    filtered: list[dict] = []

    for place in places:
        website = place.get("websiteUri")
        rating_count = place.get("userRatingCount", 0)
        rating = place.get("rating", 0)
        display_name = place.get("displayName", {}).get("text", "Unknown")

        if not website:
            continue
        if rating_count >= max_reviews and rating >= min_rating:
            continue

        filtered.append(
            {
                "business_name": display_name,
                "website": website,
                "review_count": rating_count,
                "rating": rating,
            }
        )

    logger.info("searchText returned %d places, %d after filtering", len(places), len(filtered))
    return filtered
