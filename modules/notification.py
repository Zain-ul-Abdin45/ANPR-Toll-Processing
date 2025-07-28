from datetime import datetime
import uuid
from modules.logger import alert_logger

def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

def create_notification(cur, notif_type, message, priority, vehicle_id=None, plaza_id=None):
    vehicle_info = ""

    # Step 1: Append vehicle details if vehicle_id is a valid UUID
    if vehicle_id and is_valid_uuid(vehicle_id):
        try:
            cur.execute("""
                SELECT license_plate, vehicle_type, model, color
                FROM vehicles
                WHERE vehicle_id = %s
            """, (vehicle_id,))
            vehicle = cur.fetchone()
            if vehicle:
                plate, vtype, model, color = vehicle
                vehicle_info = f" (Vehicle: {plate}, {color} {model} [{vtype}])"
        except Exception as ve:
            alert_logger.warning(f"[VEHICLE_LOOKUP_FAIL] vehicle_id={vehicle_id} | {ve}")
    elif vehicle_id:
        # Vehicle ID exists but is not a valid UUID
        alert_logger.warning(f"[SKIPPED_LOOKUP] Expected UUID for vehicle_id, got '{vehicle_id}'")

    # Step 2: Add contextual message additions
    if notif_type == "LOW_BALANCE":
        payment_url = f"https://smart-toll.local/pay?vehicle={vehicle_id}"
        message += f"\nPlease top up here: {payment_url}"
    elif notif_type in ["TAG_MISSING", "LICENSE_MISSING", "UNMATCHED_PLATE"]:
        message += vehicle_info

    # Step 3: Prevent duplicate entries
    cur.execute("""
        SELECT 1 FROM notification
        WHERE message = %s AND type = %s AND priority = %s
        AND timestamp >= NOW() - INTERVAL '1 day'
    """, (message, notif_type, priority))
    if cur.fetchone():
        return

    # Step 4: Insert new notification
    cur.execute("""
        INSERT INTO notification (
            notification_id, message, timestamp, type, priority, status, vehicle_id, plaza_id
        ) VALUES (
            gen_random_uuid(), %s, NOW(), %s, %s, 'unread', %s, %s
        )
    """, (
        message, notif_type, priority,
        vehicle_id if is_valid_uuid(vehicle_id) else None,
        plaza_id
    ))
    alert_logger.info(f"NOTIFICATION [{notif_type}] | {message}")

def get_notifications_by_plate(cur, license_plate, only_unread=False):
    base_query = """
        SELECT n.notification_id, n.message, n.timestamp, n.type, n.priority, n.status
        FROM notification n
        JOIN vehicles v ON v.vehicle_id = n.vehicle_id
        WHERE v.license_plate = %s
    """
    if only_unread:
        base_query += " AND n.status = 'unread'"
    base_query += " ORDER BY n.timestamp DESC"

    cur.execute(base_query, (license_plate,))
    return cur.fetchall()

def get_notifications_by_plate_and_tag(cur, license_plate, tag_id):
    cur.execute("""
        SELECT n.notification_id, n.message, n.timestamp, n.type, n.priority
        FROM notification n
        JOIN vehicles v ON v.vehicle_id = n.vehicle_id
        JOIN rfid_tags t ON t.vehicle_id = v.vehicle_id
        WHERE v.license_plate = %s AND t.tag_id = %s
        ORDER BY n.timestamp DESC
    """, (license_plate, tag_id))
    return cur.fetchall()

def send_sms(phone_number, message):
    alert_logger.info(f"[SMS] To: {phone_number} | Message: {message}")

def send_email(email, subject, message):
    alert_logger.info(f"[EMAIL] To: {email} | Subject: {subject} | Message: {message}")

def send_security_alert(channel, message):
    alert_logger.info(f"[SECURITY ALERT] Channel: {channel} | Message: {message}")
