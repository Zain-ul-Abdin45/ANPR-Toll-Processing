import json
import psycopg2
from modules.logger import plate_logger, rfid_logger, txn_logger, alert_logger, log_config, general_logger
from modules.alerts import run_security_checks
from modules.rfid import get_active_rfid
from modules.vehicle import get_vehicle, get_toll_rate, get_account, get_vehicle_by_tag, check_tag_status
from modules.toll_transaction import deduct_toll
from modules.notification import create_notification
from modules.security import trigger_security_alert, escalate_security_incident
general_logger.info("Test general logger working")
# Load DB config
with open("configs/config.json") as f:
    db_config = json.load(f)

# logger = get_logger("general_logs", "general.log")
def get_connection():
    return psycopg2.connect(
        dbname=db_config["database"],
        user=db_config["username"],
        password=db_config["password"],
        host=db_config["host"],
        port=db_config["port"]
    )


def get_vehicle_id_by_plate(cur, plate):
    cur.execute("""
        SELECT vehicle_id FROM vehicles
        WHERE license_plate = %s
    """, (plate,))
    row = cur.fetchone()
    general_logger.info(f"Vehicle ID for plate {plate}: {row[0] if row else 'Not Found'}")
    return row[0] if row else None

def get_vehicle_id_by_tag(cur, tag_id: str):
#    logger.info(f"Looking up vehicle by TAG_ID: {tag_id}")
    cur.execute("""
        SELECT v.vehicle_id
        FROM vehicles v
        JOIN rfid_tags r ON r.vehicle_id = v.vehicle_id
        WHERE r.tag_id = %s AND r.is_active = TRUE
    """, (tag_id,))
    row = cur.fetchone()
    general_logger.info(f"Vehicle ID for tag {tag_id}: {row[0] if row else 'Not Found'}")
    return row[0] if row else None




# def process_vehicle_entry(license_plate: str, plaza_id: str = "PLZ001"):
#     try:
#         conn = get_connection()
#         conn.autocommit = True

#         with conn.cursor() as cur:
#             # Step 1: Get vehicle details (license_plate → vehicle_id)
#             cur.execute("""
#                 SELECT vehicle_id, vehicle_type, owner_id FROM vehicles
#                 WHERE license_plate = %s
#             """, (license_plate,))
#             vehicle = cur.fetchone()

#             if not vehicle:
#                 plate_logger.warning(f"Unknown vehicle: {license_plate}")
#                 create_notification(cur, "UNMATCHED_PLATE", f"Unknown vehicle {license_plate}", "HIGH", vehicle_id=None, plaza_id=plaza_id)
#                 return {"status": "UNMATCHED"}

#             vehicle_id, vehicle_type, owner_id = vehicle
#             plate_logger.info(f"Vehicle verified: {license_plate} | Type={vehicle_type}")

#             # Step 2: Get RFID tag for vehicle_id
#             cur.execute("""
#                 SELECT tag_id FROM rfid_tags
#                 WHERE vehicle_id = %s AND is_active = TRUE
#             """, (vehicle_id,))
#             rfid = cur.fetchone()

#             if not rfid:
#                 rfid_logger.warning(f"No active RFID for: {license_plate}")
#                 create_notification(cur, "TAG_MISSING", f"Missing or inactive RFID on {license_plate}", "MEDIUM", vehicle_id=vehicle_id, plaza_id=plaza_id)
#                 return {"status": "TAG_MISSING"}

#             tag_id = rfid[0]
#             rfid_logger.info(f"RFID tag verified: {tag_id}")

#             # Step 3: Security checks
#             security = run_security_checks(cur, license_plate, tag_id)
#             if security["status"] != "CLEAR":
#                 reason = security.get("reason", "N/A")
#                 alert_logger.warning(f"Security flagged {license_plate} → {security['status']}")
#                 create_notification(cur, security["status"], f"{license_plate} flagged: {reason}", "CRITICAL", vehicle_id=vehicle_id, plaza_id=plaza_id)
#                 trigger_security_alert(cur, security["status"], "HIGH")
#                 escalate_security_incident(cur, f"{security['status']} Detected", plaza_id, "HIGH")
#                 return {"status": security["status"], "details": reason}

#             # Step 4: Toll cost
#             toll_row = get_toll_rate(cur, vehicle_type)
#             if not toll_row:
#                 alert_logger.error(f"No toll rate for vehicle type: {vehicle_type}")
#                 return {"status": "NO_RATE"}

#             toll = toll_row[0]

#             # Step 5: Owner account balance
#             account = get_account(cur, owner_id)
#             if not account:
#                 alert_logger.warning(f"No account for owner: {owner_id}")
#                 return {"status": "ACCOUNT_MISSING"}

#             account_id, balance = account

#             if balance >= toll:
#                 deduct_toll(cur, account_id, tag_id, toll, plaza_id)
#                 txn_logger.info(f"Toll of {toll} deducted from account {account_id}")
#                 return {"status": "TOLL_PAID", "amount": toll}
#             else:
#                 # Check for unresolved dues
#                 cur.execute("""
#                     SELECT 1 FROM pending_toll_ledger
#                     WHERE vehicle_id = %s AND plaza_id = %s AND resolved = FALSE
#                 """, (vehicle_id, plaza_id))
#                 if cur.fetchone():
#                     return {
#                         "status": "PENDING_TOLL",
#                         "message": f"Unresolved toll for {license_plate} at {plaza_id}",
#                         "vehicle": license_plate,
#                         "plaza": plaza_id
#                     }

#                 # Record new pending toll
#                 create_notification(cur, "LOW_BALANCE", f"Insufficient balance ({balance}) for toll {toll} - Vehicle: {license_plate}", "HIGH", vehicle_id=vehicle_id, plaza_id=plaza_id)

#                 cur.execute("""
#                     INSERT INTO pending_toll_ledger (ledger_id, vehicle_id, tag_id, plaza_id, amount_due, created_at)
#                     VALUES (gen_random_uuid(), %s, %s, %s, %s, NOW())
#                 """, (vehicle_id, tag_id, plaza_id, toll))

#                 return {"status": "INSUFFICIENT_FUNDS", "required": toll, "balance": balance}

#     except Exception as e:
#         alert_logger.error(f"Fatal error during processing: {str(e)}")
#         return {"status": "ERROR", "message": str(e)}




def process_vehicle_entry(license_plate: str, plaza_id: str = "PLZ001"):
    try:
        conn = get_connection()
        conn.autocommit = True
        # Step 1: Validate plaza_id
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM toll_plazas WHERE plaza_id = %s", (plaza_id,))
            if not cur.fetchone():
                alert_logger.warning(f"Unknown toll plaza: {plaza_id}")
                return {
                    "status": "INVALID_PLAZA",
                    "message": f"Toll plaza {plaza_id} does not exist."
                }
            vehicle = get_vehicle(cur, license_plate)
            general_logger.info(f"Processing vehicle entry for {license_plate} at {plaza_id}")
            if not vehicle:
                plate_logger.warning(f"Unknown vehicle: {license_plate}")
                create_notification(
                    cur, "UNMATCHED_PLATE", f"Unknown vehicle {license_plate}", "HIGH",
                    vehicle_id=None, plaza_id=plaza_id
                )
                return {"status": "UNMATCHED"}

            vehicle_id, vehicle_type, owner_id = vehicle
            plate_logger.info(f"Vehicle verified: {license_plate} | Type={vehicle_type}")

            # Step 2: RFID
            rfid = get_active_rfid(cur, license_plate)
            if not rfid:
                rfid_logger.warning(f"No active RFID for: {license_plate}")
                create_notification(
                    cur, "TAG_MISSING", f"Missing or inactive RFID on {license_plate}", "MEDIUM",
                    vehicle_id=vehicle_id, plaza_id=plaza_id
                )
                return {"status": "TAG_MISSING"}

            tag_id = rfid[0]
            rfid_logger.info(f"RFID tag verified: {tag_id}")

            # Step 3: Security
            security = run_security_checks(cur, license_plate, tag_id)
            if security["status"] != "CLEAR":
                reason = security.get("reason", "N/A")
                alert_logger.warning(f"Security flagged {license_plate} → {security['status']}")
                create_notification(
                    cur, security["status"], f"{license_plate} flagged: {reason}", "CRITICAL",
                    vehicle_id=vehicle_id, plaza_id=plaza_id
                )
                trigger_security_alert(cur, security["status"], "HIGH")
                escalate_security_incident(cur, f"{security['status']} Detected", plaza_id, "HIGH")
                return {"status": security["status"], "details": reason}

            # 💰 Step 4: Toll cost
            toll_row = get_toll_rate(cur, vehicle_type)
            if not toll_row:
                alert_logger.error(f"No toll rate for vehicle type: {vehicle_type}")
                return {"status": "NO_RATE"}

            toll = toll_row[0]

            #  Step 5: Account
            account = get_account(cur, owner_id)
            if not account:
                alert_logger.warning(f"No active account for owner {owner_id}")
                return {"status": "ACCOUNT_MISSING"}
            account_id, balance = account
            general_logger.info(f"Account verified: ID={account_id}, Balance={balance}")
            if balance >= toll:
                deduct_toll(cur, account_id, tag_id, toll, plaza_id)
                txn_logger.info(f"Toll of {toll} deducted from account {account_id}")
                return {"status": "TOLL_PAID", "amount": toll}
            else:
                msg = f"Insufficient balance ({balance}) for toll {toll} - Vehicle: {license_plate}"
                alert_logger.warning(msg)
                # Step 6: Check pending dues
                cur.execute("""
                    SELECT 1 FROM pending_toll_ledger
                    WHERE vehicle_id = %s AND plaza_id = %s AND resolved = FALSE
                """, (vehicle_id, plaza_id))
                general_logger.info(f"Checking pending dues for {license_plate} at {plaza_id}")
                if cur.fetchone():
                    return {
                        "status": "PENDING_TOLL",
                        "message": f"Vehicle has unresolved toll at {plaza_id}",
                        "vehicle": license_plate,
                        "plaza": plaza_id
                    }
                general_logger.info(f"Recording new pending toll for {license_plate} at {plaza_id}")
                # Step 7: Record notification + ledger
                create_notification(
                    cur, "LOW_BALANCE", msg, "HIGH",
                    vehicle_id=vehicle_id, plaza_id=plaza_id
                )

                cur.execute("""
                    INSERT INTO pending_toll_ledger (
                        ledger_id, vehicle_id, tag_id, plaza_id, amount_due, created_at
                    ) VALUES (
                        gen_random_uuid(), %s, %s, %s, %s, NOW()
                    )
                """, (vehicle_id, tag_id, plaza_id, toll))

                return {"status": "INSUFFICIENT_FUNDS", "required": toll, "balance": balance}
    except Exception as e:
        alert_logger.error(f"Fatal error during processing: {str(e)}")
        general_logger.error(f"Error processing vehicle entry: {str(e)}")
        return {"status": "ERROR", "message": str(e)}


def process_toll_flexible(plaza_id, license_plate=None, tag_id=None):
    conn = get_connection()
    conn.autocommit = True
    general_logger.info(f"Processing toll for Plaza={plaza_id}, Plate={license_plate}, Tag={tag_id}")
    with conn.cursor() as cur:
        vehicle = None
        if license_plate:
            vehicle = get_vehicle(cur, license_plate)
            general_logger.info(f"Vehicle lookup by plate {license_plate}: {vehicle}")
        elif tag_id:
            vehicle = get_vehicle_by_tag(cur, tag_id)
            general_logger.info(f"Vehicle lookup by tag {tag_id}: {vehicle}")
        if not vehicle:
            msg = f"Unregistered vehicle detected at plaza {plaza_id}"
            create_notification(cur, "UNMATCHED_PLATE", msg, "HIGH", vehicle_id=None, plaza_id=plaza_id)
            trigger_security_alert(cur, "UNMATCHED_PLATE", "HIGH")
            general_logger.warning(msg)
            return {"status": "UNMATCHED", "message": msg}

        vehicle_id, v_type, owner_id = vehicle
        general_logger.info(f"Vehicle verified: ID={vehicle_id}, Type={v_type}, Owner={owner_id}")
        # Validate RFID if available
        if tag_id:
            tag_status = check_tag_status(cur, tag_id)
            if tag_status == "BLACKLISTED":
                msg = f"Blacklisted tag {tag_id} detected on vehicle {vehicle_id}"
                create_notification(cur, "BLACKLISTED_TAG", msg, "CRITICAL", vehicle_id=vehicle_id, plaza_id=plaza_id)
                trigger_security_alert(cur, "BLACKLISTED_TAG", "CRITICAL")
                general_logger.warning(msg)
                return {"status": "BLACKLISTED", "message": msg}
        else:
            # If no tag_id provided, check if vehicle has an active tag
            msg = f"Missing tag on vehicle {vehicle_id} at {plaza_id}"
            create_notification(cur, "TAG_MISSING", msg, "HIGH", vehicle_id=vehicle_id, plaza_id=plaza_id)
            general_logger.warning(msg)
        # Proceed with toll deduction if all is well
        toll_info = get_toll_rate(cur, v_type)
        if not toll_info:
            return {"status": "NO_RATE", "message": f"No toll rate for type {v_type}"}
        toll_amount = toll_info[0]
        general_logger.info(f"Toll amount for {v_type}: {toll_amount}")
        account = get_account(cur, owner_id)
        if not account:
            return {"status": "ACCOUNT_MISSING"}

        acc_id, balance = account
        if balance >= toll_amount:
            deduct_toll(cur, acc_id, tag_id, toll_amount, plaza_id)
            return {"status": "TOLL_PAID", "amount": toll_amount}
        else:
            cur.execute("""SELECT 1 FROM pending_toll_ledger
                           WHERE vehicle_id = %s AND plaza_id = %s AND resolved = FALSE""",
                        (vehicle_id, plaza_id))
            if not cur.fetchone():
                cur.execute("""INSERT INTO pending_toll_ledger (
                                ledger_id, vehicle_id, tag_id, plaza_id, amount_due, created_at)
                                VALUES (gen_random_uuid(), %s, %s, %s, %s, NOW())""",
                            (vehicle_id, tag_id, plaza_id, toll_amount))
                general_logger.info(f"Pending toll recorded for {license_plate} at {plaza_id}")
                create_notification(cur, "LOW_BALANCE",
                                    f"Insufficient balance ({balance}) for toll {toll_amount}",
                                    "HIGH", vehicle_id=vehicle_id, plaza_id=plaza_id)
                general_logger.warning(f"Insufficient funds for {license_plate} at {plaza_id}")
            return {"status": "INSUFFICIENT_FUNDS", "required": toll_amount, "balance": balance}
