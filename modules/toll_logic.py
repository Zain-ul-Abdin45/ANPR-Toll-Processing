from modules.sql import (
    get_vehicle,
    get_active_rfid,
    run_security_checks,
    get_toll_rate,
    get_account,
    deduct_toll,
    get_vehicle_id_by_plate,
    get_vehicle_id_by_tag,
    create_notification,
    escalate_security_incident,
    trigger_security_alert,
    get_connection
)
from modules.logger import alert_logger, txn_logger, general_logger
from modules.notification import is_valid_uuid


def process_toll_flexible(plaza_id: str, license_plate: str = None, tag_id: str = None):
    """ 
        Process toll payment based on either license plate or RFID tag.
        Returns a dictionary with status and details.
    """
    general_logger.info("Toll Process Started...")
    try:
        if not plaza_id:
            return {"status": "ERROR", "message": "Toll plaza ID is required"}
        general_logger.info("Processing toll for Plaza ID:", plaza_id)

        conn = get_connection()
        conn.autocommit = True
        with conn.cursor() as cur:
            # 🔍 Validate plaza_id first
            cur.execute("SELECT 1 FROM toll_plazas WHERE plaza_id = %s", (plaza_id,))
            if not cur.fetchone():
                general_logger.warning(f"Invalid toll plaza: {plaza_id}")
                return {
                    "status": "INVALID_PLAZA",
                    "message": f"Toll plaza {plaza_id} does not exist."
                }

            vehicle_id = None
            vehicle_type = None
            owner_id = None

            # Case A: Tag provided
            if tag_id:
                general_logger.info(f"Processing toll for TAG_ID: {tag_id}")
                vehicle_id = get_vehicle_id_by_tag(cur, tag_id)
                general_logger.info(f"Resolved vehicle_id from tag: {vehicle_id}")

                if not vehicle_id:
                    create_notification(cur, "UNKNOWN_TAG", f"Unknown or inactive tag {tag_id}", "HIGH", plaza_id=plaza_id)
                    return {"status": "UNKNOWN_TAG"}

                cur.execute("SELECT license_plate, vehicle_type, owner_id FROM vehicles WHERE vehicle_id = %s", (vehicle_id,))
                result = cur.fetchone()
                if not result:
                    return {"status": "ERROR", "message": "Vehicle not found for tag"}
                
                license_plate, vehicle_type, owner_id = result
                general_logger.info(f"Resolved vehicle from tag: Plate={license_plate}, Type={vehicle_type}, Owner={owner_id}")

                # License plate missing in DB after tag resolution (data inconsistency)
                if not license_plate:
                    create_notification(cur, "LICENSE_MISSING", f"Missing license plate for tag {tag_id}", "HIGH", vehicle_id=vehicle_id, plaza_id=plaza_id)
                    return {"status": "LICENSE_MISSING"}

            # Case B: Only license plate
            elif license_plate:
                general_logger.info(f"Processing toll for LICENSE_PLATE: {license_plate}")
                vehicle = get_vehicle(cur, license_plate)
                if not vehicle:
                    create_notification(cur, "UNMATCHED_PLATE", f"Unknown vehicle {license_plate}", "HIGH", plaza_id=plaza_id)
                    return {"status": "UNMATCHED_PLATE"}

                vehicle_id, vehicle_type, owner_id = vehicle
                general_logger.info(f"Resolved vehicle from plate: ID={vehicle_id}, Type={vehicle_type}, Owner={owner_id}")
                if not tag_id:
                    tag = get_active_rfid(cur, license_plate)
                    if not tag:
                        general_logger.warning(f"No active RFID tag found for {license_plate} at plaza {plaza_id}")
                        create_notification(
                            cur, "TAG_MISSING", f"Missing or inactive RFID on {license_plate}", "MEDIUM",
                            vehicle_id=vehicle_id, plaza_id=plaza_id
                        )
                        return {"status": "TAG_MISSING"}
                    tag_id = tag[0]
                    general_logger.info(f"Active tag_id found: {tag_id} for plate {license_plate}")

            # Defensive check: UUID validity
            if not is_valid_uuid(vehicle_id):
                general_logger.error(f"Invalid vehicle_id: {vehicle_id} for plate {license_plate} at plaza {plaza_id}")
                print(f"vehicle_id is not a valid UUID → {vehicle_id}")
                return {"status": "ERROR", "message": f"vehicle_id not a UUID: {vehicle_id}"}

            # Step 3: Security
            general_logger.info(f"Running security checks for Plate={license_plate}, Tag={tag_id}")
            security = run_security_checks(cur, license_plate, tag_id)
            if security["status"] != "CLEAR":
                reason = security.get("reason", "N/A")
                alert_logger.warning(f"Security flagged {license_plate} → {security['status']}")
                create_notification(cur, security["status"], f"{license_plate} flagged: {reason}", "CRITICAL", vehicle_id=vehicle_id, plaza_id=plaza_id)
                trigger_security_alert(cur, security["status"], "HIGH")
                escalate_security_incident(cur, f"{security['status']} Detected", plaza_id, "HIGH")
                return {"status": security["status"], "details": reason}

            # Step 4: Toll rate
            general_logger.info(f"Fetching vehicle type for {license_plate} (ID: {vehicle_id})")
            toll_row = get_toll_rate(cur, vehicle_type)
            if not toll_row:
                return {"status": "NO_RATE", "message": f"No toll rate for vehicle type {vehicle_type}"}
            toll = toll_row[0]
            general_logger.info(f"Toll amount for {vehicle_type}: {toll}")

            # Step 5: Balance check
            general_logger.info(f"Checking account for owner_id: {owner_id}")
            account = get_account(cur, owner_id)
            if not account:
                return {"status": "ACCOUNT_MISSING"}
            account_id, balance = account
            general_logger.info(f"Account found: ID={account_id}, Balance={balance}")

            if balance >= toll:
                deduct_toll(cur, account_id, tag_id, toll, plaza_id)
                txn_logger.info(f"Toll of {toll} deducted from account {account_id}")
                return {"status": "TOLL_PAID", "amount": toll}

            # Insufficient balance
            general_logger.warning(f"Insufficient balance for {license_plate} at plaza {plaza_id} (Balance: {balance}, Required: {toll})")
            create_notification(cur, "LOW_BALANCE", f"Insufficient balance for toll {toll} - Vehicle: {license_plate}", "HIGH", vehicle_id=vehicle_id, plaza_id=plaza_id)

            cur.execute("""
                SELECT 1 FROM pending_toll_ledger
                WHERE vehicle_id = %s AND plaza_id = %s AND resolved = FALSE
            """, (vehicle_id, plaza_id))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO pending_toll_ledger (
                        ledger_id, vehicle_id, tag_id, plaza_id, amount_due, created_at
                    ) VALUES (
                        gen_random_uuid(), %s, %s, %s, %s, NOW()
                    )
                """, (vehicle_id, tag_id, plaza_id, toll))
                general_logger.info(f"Pending toll recorded for {license_plate} at plaza {plaza_id}")

            return {"status": "INSUFFICIENT_FUNDS", "required": toll, "balance": balance}

    except Exception as e:
        alert_logger.error(f"EXCEPTION during toll processing: {str(e)}")
        return {"status": "ERROR", "message": str(e)}
