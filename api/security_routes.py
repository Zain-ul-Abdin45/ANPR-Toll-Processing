from fastapi import APIRouter
import psycopg2
import json
from modules.security import fetch_security_incidents

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

@router.get("/incidents")
def get_incidents():
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            incidents = fetch_security_incidents(cur)
            return {"incidents": incidents}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}
