import psycopg2, json
from modules.logger import alert_logger


with open("configs/config.json") as f:
    db_config = json.load(f)

def get_connection():
    return psycopg2.connect(
        dbname=db_config["database"],
        user=db_config["user"],
        password=db_config["password"],
        host=db_config["host"],
        port=db_config["port"]
    )


def is_blacklisted_rfid(cur, tag_id):
    cur.execute("""
        SELECT reason, severity FROM blacklisted_rfid
        WHERE tag_id = %s
    """, (tag_id,))
    return cur.fetchone()


def is_stolen_vehicle(cur, license_plate):
    cur.execute("""
        SELECT reportedDate, reportingAgency FROM stolen_vehicle_registry
        WHERE licensePlate = %s AND status = TRUE
    """, (license_plate,))
    return cur.fetchone()


def generate_alert(cur, alert_type, message, priority):
    cur.execute("""
        INSERT INTO notification (notification_id, message, timestamp, type, priority)
        VALUES (gen_random_uuid(), %s, NOW(), %s, %s)
    """, (message, alert_type, priority))
    alert_logger.info(f"ALERT [{alert_type}] | {message}")


def run_security_checks(cur, license_plate, tag_id):
    # 1. Check stolen vehicle
    stolen = is_stolen_vehicle(cur, license_plate)
    if stolen:
        generate_alert(
            cur,
            "STOLEN_VEHICLE",
            f"Stolen vehicle detected: {license_plate}",
            "CRITICAL"
        )
        return {"status": "STOLEN", "details": stolen}

    # 2. Check blacklisted RFID
    blacklisted = is_blacklisted_rfid(cur, tag_id)
    if blacklisted:
        reason, severity = blacklisted
        generate_alert(
            cur,
            "BLACKLISTED_TAG",
            f"Blacklisted RFID {tag_id} used. Reason: {reason}",
            severity
        )
        return {"status": "BLACKLISTED", "reason": reason}

    return {"status": "CLEAR"}
