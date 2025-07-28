from fastapi import APIRouter, Body
import psycopg2
import json
import random
from datetime import datetime
from modules.vehicle import register_vehicle_with_rfid
from modules.rfid import assign_rfid_to_vehicle
from datetime import timedelta

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


@router.post("/register")
def register_vehicle(payload: dict = Body(...)):
    try:
        conn = get_connection()
        conn.autocommit = True
        if "tag_id" not in payload:
            raise ValueError("Missing 'tag_id' in payload")

        with conn.cursor() as cur:
            plate = payload.get("license_plate") or payload.get("plate")
            if not plate:
                return {"status": "ERROR", "message": "License plate is required."}

            # Check if vehicle with this plate already exists
            cur.execute("SELECT vehicle_id FROM vehicles WHERE license_plate = %s", (plate,))
            existing = cur.fetchone()

            if existing:
                return {
                    "status": "ALREADY_REGISTERED",
                    "message": f"Vehicle with plate '{plate}' is already registered.",
                    "vehicle_id": existing[0]
                }

            # Register the vehicle
            result = register_vehicle_with_rfid(cur, payload)
            return {"status": "REGISTERED", "details": result}

    except Exception as e:
        return {"status": "ERROR", "message": str(e)}



# {
#   "owner_id": "OWN082",
#   "tag_id": "TAG147",
#   "license_plate": "EU-7899-YY",
#   "vehicle_type": "SUV",
#   "model": "Tucson",
#   "color": "Silver"
# }
