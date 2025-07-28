from fastapi import APIRouter, Query
import psycopg2
import json
from modules.notification import get_notifications_by_plate_and_tag, get_notifications_by_plate

router = APIRouter()

def get_connection():
    with open("configs/config.json") as f:
        db_config = json.load(f)
    return psycopg2.connect(
        dbname=db_config["database"],
        user=db_config["username"],
        password=db_config["password"],
        host=db_config["host"],
        port=db_config["port"]
    )

@router.get("/")
def view_notifications(plate: str = Query(None), tag_id: str = Query(None)):
    if not plate and not tag_id:
        return {"status": "ERROR", "message": "At least plate or tag_id must be provided."}

    try:
        conn = get_connection()
        with conn.cursor() as cur:

            if plate and not tag_id:
                # Check if vehicle exists
                cur.execute("SELECT vehicle_id FROM vehicles WHERE license_plate = %s", (plate,))
                vehicle = cur.fetchone()
                if not vehicle:
                    return {"status": "PLATE_MISSING", "message": f"Plate '{plate}' not found.", "notifications": []}

                cur.execute("SELECT 1 FROM rfid_tags WHERE vehicle_id = %s AND is_active = TRUE", (vehicle[0],))
                if not cur.fetchone():
                    return {"status": "TAG_MISSING", "plate": plate, "message": "RFID tag not found or inactive for the given plate.", "notifications": []}

                # Get notifications
                results = get_notifications_by_plate(cur, plate)
                return {"plate": plate, "notifications": results}

            elif tag_id and not plate:
                # Find vehicle by tag
                cur.execute("SELECT vehicle_id FROM rfid_tags WHERE tag_id = %s AND is_active = TRUE", (tag_id,))
                tag_info = cur.fetchone()
                if not tag_info:
                    return {"status": "TAG_NOT_FOUND", "tag_id": tag_id, "message": "Tag not found or inactive."}

                cur.execute("SELECT license_plate FROM vehicles WHERE vehicle_id = %s", (tag_info[0],))
                vehicle = cur.fetchone()
                if not vehicle or not vehicle[0]:
                    return {"status": "PLATE_MISSING", "tag_id": tag_id, "message": "Plate not registered for this tag.", "notifications": []}

                results = get_notifications_by_plate(cur, vehicle[0])
                return {"plate": vehicle[0], "tag_id": tag_id, "notifications": results}

            elif plate and tag_id:
                # Cross-validate match
                cur.execute("""
                    SELECT v.license_plate FROM vehicles v
                    JOIN rfid_tags r ON v.vehicle_id = r.vehicle_id
                    WHERE v.license_plate = %s AND r.tag_id = %s AND r.is_active = TRUE
                """, (plate, tag_id))

                if not cur.fetchone():
                    return {"status": "MISMATCH", "message": "Plate and tag do not match or tag inactive.", "notifications": []}

                results = get_notifications_by_plate(cur, plate)
                return {"plate": plate, "tag_id": tag_id, "notifications": results}

    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

