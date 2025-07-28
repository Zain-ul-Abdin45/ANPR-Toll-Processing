from datetime import datetime, timedelta

def get_active_rfid(cur, license_plate):
    cur.execute("""
        SELECT r.tag_id
        FROM rfid_tags r
        JOIN vehicles v ON r.vehicle_id = v.vehicle_id
        WHERE v.license_plate = %s AND r.is_active = TRUE
    """, (license_plate,))
    return cur.fetchone()




def assign_rfid_to_vehicle(cur, tag_id, license_plate, issue_date=None, expiry_date=None):
    issue_date = issue_date or datetime.now()
    expiry_date = expiry_date or (issue_date + timedelta(days=3 * 365))

    # ✅ Fetch vehicle_id using license_plate
    cur.execute("SELECT vehicle_id FROM vehicles WHERE license_plate = %s", (license_plate,))
    result = cur.fetchone()
    if not result:
        raise ValueError(f"No vehicle found with plate: {license_plate}")

    vehicle_id = result[0]

    # ✅ Insert using vehicle_id
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
