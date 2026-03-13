from fastapi import APIRouter, Query

from app.schemas import AutocompleteItem, AutocompleteResponse, Viewport, LatLng
from app.services import google_places

router = APIRouter(prefix="/api", tags=["autocomplete"])


@router.get("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete_endpoint(q: str = Query(..., min_length=1, max_length=256)):
    raw = await google_places.autocomplete(q)
    predictions = []
    for item in raw:
        viewport = None
        if item.get("viewport"):
            vp = item["viewport"]
            viewport = Viewport(
                low=LatLng(latitude=vp["low"]["latitude"], longitude=vp["low"]["longitude"]),
                high=LatLng(latitude=vp["high"]["latitude"], longitude=vp["high"]["longitude"]),
            )
        predictions.append(
            AutocompleteItem(
                description=item["description"],
                place_id=item["place_id"],
                viewport=viewport,
            )
        )
    return AutocompleteResponse(predictions=predictions)
