from fastapi import APIRouter, Query
from typing import Optional
from modules.toll_logic import process_toll_flexible

router = APIRouter()

@router.post("/process")
def process_toll(
    plaza_id: str = Query(..., description="Toll plaza identifier"),
    license_plate: Optional[str] = Query(None),
    tag_id: Optional[str] = Query(None)
):
    if not license_plate and not tag_id:
        return {"status": "ERROR", "message": "Either license_plate or tag_id must be provided."}

    result = process_toll_flexible(plaza_id, license_plate, tag_id)
    return {"status": "OK", "result": result}
