import time
import random
from datetime import datetime
from modules.sql import process_vehicle_entry
from modules.logger import plate_logger
import psycopg2
import json

# Load config for optional direct DB reads (plazas)
with open("configs/config.json") as f:
    db_config = json.load(f)

conn = psycopg2.connect(
    dbname=db_config["database"],
    user=db_config["username"],
    password=db_config["password"],
    host=db_config["host"],
    port=db_config["port"]
)
conn.autocommit = True
cur = conn.cursor()

# Fetch all valid license plates
cur.execute("SELECT license_plate FROM vehicles")
vehicles = [row[0] for row in cur.fetchall()]

# Fetch toll plazas
cur.execute("SELECT plaza_id FROM toll_plazas")
toll_plazas = [row[0] for row in cur.fetchall()]

cur.close()
conn.close()

plate_logger.info("🚦 Starting real-time vehicle toll simulation...")

try:
    while True:
        time.sleep(random.randint(0, 30))

        plate = random.choice(vehicles)
        plaza = random.choice(toll_plazas)
        plate_logger.info(f"Vehicle approaching toll: {plate} @ {plaza}")

        result = process_vehicle_entry(plate)

        if result["status"] == "TOLL_PAID":
            plate_logger.info(f"Toll paid: {result['amount']} | Remaining balance updated.")
        elif result["status"] == "INSUFFICIENT_FUNDS":
            plate_logger.warning(f"Insufficient balance for {plate} (Needs: {result['required']})")
        elif result["status"] == "BLACKLISTED":
            plate_logger.warning(f"Blacklisted tag detected: {result['details']}")
        elif result["status"] == "STOLEN":
            plate_logger.warning(f"Stolen vehicle detected: {plate}")
        elif result["status"] == "TAG_MISSING":
            plate_logger.warning(f"No RFID tag assigned or active.")
        elif result["status"] == "OWNER_MISSING":
            plate_logger.warning(f"Vehicle not linked to a registered owner.")
        else:
            plate_logger.error(f"Failed to process: {result['message'] if 'message' in result else result['status']}")

except KeyboardInterrupt:
    plate_logger.info("Simulation stopped by user.")
