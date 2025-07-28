import uuid
from datetime import datetime, timedelta
from modules.rfid import assign_rfid_to_vehicle

def get_vehicle(cur, plate):
    cur.execute("""
        SELECT vehicle_id, vehicle_type, owner_id
        FROM vehicles
        WHERE license_plate = %s
    """, (plate,))
    return cur.fetchone()




def get_active_rfid(cur, license_plate):
    cur.execute("""
        SELECT tag_id FROM rfid_tags
        WHERE vehicle_plate = %s AND is_active = TRUE
    """, (license_plate,))
    return cur.fetchone()

def assign_rfid_to_vehicle(cur, tag_id, vehicle_id, issue_date=None, expiry_date=None):
    issue_date = issue_date or datetime.now()
    expiry_date = expiry_date or (issue_date + timedelta(days=3 * 365))

    cur.execute("""
        INSERT INTO rfid_tags (tag_id, is_active, issue_date, expiry_date, vehicle_id)
        VALUES (%s, TRUE, %s, %s, %s)
    """, (tag_id, issue_date, expiry_date, vehicle_id))

    return tag_id


def is_blacklisted(cur, tag_id):
    cur.execute("""
        SELECT reason, severity, blacklistedDate FROM blacklisted_rfid
        WHERE tag_id = %s
    """, (tag_id,))
    return cur.fetchone()

def blacklist_tag(cur, tag_id, reason, severity, reporter="System"):
    cur.execute("""
        INSERT INTO blacklisted_rfid (tag_id, reason, blacklistedDate, reportedBy, severity)
        VALUES (%s, %s, %s, %s, %s)
    """, (tag_id, reason, datetime.now(), reporter, severity))


def get_toll_rate(cur, vehicle_type):
    cur.execute("""
        SELECT base_cost FROM lov_vehicle_types
        WHERE type_code = %s
    """, (vehicle_type,))
    return cur.fetchone()


def get_account(cur, owner_id):
    cur.execute("""
        SELECT account_id, balance FROM accounts
        WHERE owner_id = %s AND is_active = TRUE
    """, (owner_id,))
    return cur.fetchone()



def register_vehicle_with_rfid(cur, payload):
    license_plate = payload["license_plate"]
    vehicle_type = payload["vehicle_type"]
    model = payload.get("model", "Unknown")
    color = payload.get("color", "Unpainted")
    owner_id = payload["owner_id"]
    tag_id = payload["tag_id"]

    # ✅ Check if tag already exists
    cur.execute("SELECT tag_id FROM rfid_tags WHERE tag_id = %s", (tag_id,))
    tag_exists = cur.fetchone()

    if tag_exists:
        raise ValueError(f"RFID tag '{tag_id}' is already assigned.")

    # Insert vehicle
    cur.execute("""
        INSERT INTO vehicles (license_plate, vehicle_type, model, color, registration_date, owner_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING vehicle_id
    """, (license_plate, vehicle_type, model, color, datetime.now(), owner_id))

    vehicle_id = cur.fetchone()[0]

    # Assign RFID tag
    issue_date = datetime.now()
    expiry_date = issue_date + timedelta(days=3 * 365)

    cur.execute("""
        INSERT INTO rfid_tags (tag_id, is_active, issue_date, expiry_date, vehicle_id)
        VALUES (%s, TRUE, %s, %s, %s)
    """, (tag_id, issue_date, expiry_date, vehicle_id))

    return {
        "vehicle_id": vehicle_id,
        "tag_id": tag_id,
        "license_plate": license_plate
    }

def get_vehicle_by_tag(cur, tag_id):
    cur.execute("""
        SELECT v.vehicle_id, v.vehicle_type, v.owner_id
        FROM vehicles v
        JOIN rfid_tags r ON v.vehicle_id = r.vehicle_id
        WHERE r.tag_id = %s AND r.is_active = TRUE
    """, (tag_id,))
    return cur.fetchone()

def check_tag_status(cur, tag_id):
    cur.execute("""
        SELECT 1 FROM blacklisted_rfid WHERE tag_id = %s
    """, (tag_id,))
    return "BLACKLISTED" if cur.fetchone() else "OK"
