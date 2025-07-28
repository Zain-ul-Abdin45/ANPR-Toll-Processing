from datetime import datetime
from modules.logger import alert_logger

def escalate_security_incident(cur, incident_type, location, severity, reporter="System"):
    timestamp = datetime.now()
    status = "Open"

    cur.execute("""
        INSERT INTO security_incidents (incident_type, timestamp, location, severity, reported_by, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (incident_type, timestamp, location, severity, reporter, status))

    alert_logger.warning(f"[SECURITY INCIDENT] {incident_type} | Severity: {severity} | Location: {location}")

def trigger_security_alert(cur, alert_type, priority, status="ACTIVE"):
    timestamp = datetime.now()

    cur.execute("""
        INSERT INTO security_alerts (alert_type, priority, timestamp, status)
        VALUES (%s, %s, %s, %s)
    """, (alert_type, priority, timestamp, status))

    alert_logger.warning(f"[SECURITY ALERT] Type: {alert_type} | Priority: {priority} | Status: {status}")

def start_camera_recording(camera_id, location, camera_type="AUTO", motion_detector=True):
    msg = f"[CAMERA] {camera_id} at {location} ({camera_type}) started recording. Motion detection: {motion_detector}"
    alert_logger.info(msg)
    return msg

def fetch_security_incidents(cur):
    cur.execute("""
        SELECT incident_id, incident_type, timestamp, location, severity, reported_by, status
        FROM security_incidents
        ORDER BY timestamp DESC
        LIMIT 50
    """)
    return [dict(zip(
        ['incident_id', 'type', 'timestamp', 'location', 'severity', 'reported_by', 'status'],
        row
    )) for row in cur.fetchall()]
