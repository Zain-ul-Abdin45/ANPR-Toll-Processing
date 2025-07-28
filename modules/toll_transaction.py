from datetime import datetime, timedelta

def get_active_rfid(cur, license_plate):
    cur.execute("""
        SELECT tag_id FROM rfid_tags
        WHERE vehicle_plate = %s AND is_active = TRUE
    """, (license_plate,))
    return cur.fetchone()

def assign_rfid_to_vehicle(cur, tag_id, license_plate, issue_date=None, expiry_date=None):
    issue_date = issue_date or datetime.now()
    expiry_date = expiry_date or (issue_date + timedelta(days=3 * 365))

    cur.execute("""
        INSERT INTO rfid_tags (tag_id, is_active, issue_date, expiry_date, vehicle_plate)
        VALUES (%s, TRUE, %s, %s, %s)
    """, (tag_id, issue_date, expiry_date, license_plate))

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


def deduct_toll(cur, account_id, tag_id, toll_amount, plaza_id="PLZ001"):
    # Step 1: Deduct balance
    cur.execute("""
        UPDATE accounts
        SET balance = balance - %s
        WHERE account_id = %s
    """, (toll_amount, account_id))

    # Step 2: Record the transaction
    cur.execute("""
        INSERT INTO toll_transactions (
            transaction_id, timestamp, amount, distance, status, security_flag, rfid_tag_id, plaza_id
        ) VALUES (
            gen_random_uuid(), NOW(), %s, %s, %s, %s, %s, %s
        )
    """, (toll_amount, 15.0, 'SUCCESS', False, tag_id, plaza_id))
