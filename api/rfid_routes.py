from fastapi import APIRouter
import psycopg2
import json
from modules.rfid import assign_rfid_to_vehicle, blacklist_tag

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

@router.post("/assign")
def assign_rfid(plate: str, tag_id: str):
    try:
        conn = get_connection()
        conn.autocommit = True
        with conn.cursor() as cur:
            assign_rfid_to_vehicle(cur, tag_id, plate)
        return {
            "status": "OK",
            "message": "RFID assigned successfully.",
            "data": {
                "plate": plate,
                "tag_id": tag_id
            }
        }
    
    except Exception as e:
        return {
            "status": "ERROR",
            "message": "The RFID tag is already assigned to another vehicle."
        }

@router.post("/blacklist")
def blacklist(tag_id: str, reason: str = "Cloned tag detected", severity: str = "HIGH"):
    try:
        conn = get_connection()
        conn.autocommit = True
        with conn.cursor() as cur:
            blacklist_tag(cur, tag_id, reason, severity)
        return {
            "status": "OK",
            "message": "RFID tag blacklisted successfully.",
            "data": {
                "tag_id": tag_id,
                "reason": reason,
                "severity": severity
            }
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "message": str(e)
        }
