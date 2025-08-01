import psycopg2
import random
from faker import Faker
import uuid
from datetime import datetime, timedelta
import json

# Load flat JSON config
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
fake = Faker()

# ---- Clear tables respecting FK order ----
cur.execute("DELETE FROM toll_transactions")
cur.execute("DELETE FROM blacklisted_rfid")
cur.execute("DELETE FROM stolen_vehicle_registry")
cur.execute("DELETE FROM rfid_tags")
cur.execute("DELETE FROM vehicles")
cur.execute("DELETE FROM accounts")
cur.execute("DELETE FROM owners")
cur.execute("DELETE FROM lov_fines")
cur.execute("DELETE FROM lov_vehicle_types")
cur.execute("DELETE FROM toll_plazas")

# ---- Helper functions ----
def rand_bool(prob=0.7):
    return random.random() < prob

# ---- Seed LOV tables ----
vehicle_types = [
    ("SEDAN", "Standard Sedan", 5.00),
    ("SUV", "Sport Utility Vehicle", 6.50),
    ("TRUCK", "Heavy Truck", 8.75),
]
cur.executemany("""
    INSERT INTO lov_vehicle_types (type_code, description, base_cost)
    VALUES (%s, %s, %s)
""", vehicle_types)

fines = [
    ("EXPIRED_TAG", "RFID tag expired", 100.00),
    ("BLACKLISTED_TAG", "Blacklisted RFID tag used", 250.00),
    ("SKIPPED_TOLL", "Toll bypassed without payment", 75.00),
]
cur.executemany("""
    INSERT INTO lov_fines (fine_code, description, fine_amount)
    VALUES (%s, %s, %s)
""", fines)

# ---- Toll plazas ----
toll_plazas = []
for i in range(3):
    plaza_id = f"PLZ00{i+1}"
    location = fake.city()
    highway = f"A{random.randint(1, 99)}"
    security_level = random.choice(["LOW", "MEDIUM", "HIGH"])
    toll_plazas.append((plaza_id, location, highway, True, security_level))

cur.executemany("""
    INSERT INTO toll_plazas (plaza_id, location, highway, is_operational, security_level)
    VALUES (%s, %s, %s, %s, %s)
""", toll_plazas)

# ---- Owners ----
owners = []
for i in range(100):
    owner_id = f"OWN{i+1:03d}"
    name = fake.name()
    phone = fake.phone_number()
    email = fake.email()
    address = fake.address().replace("\n", ", ")
    owners.append((owner_id, name, phone, email, address))

cur.executemany("""
    INSERT INTO owners (owner_id, name, phone_number, email, address)
    VALUES (%s, %s, %s, %s, %s)
""", owners)

# ---- Accounts ----
accounts = []
for owner in owners:
    account_id = str(uuid.uuid4())
    balance = round(random.uniform(0, 150), 2)
    account_type = random.choice(["PERSONAL", "CORPORATE"])
    risk_level = random.choice(["LOW", "MEDIUM", "HIGH"])
    accounts.append((account_id, owner[0], balance, account_type, True, risk_level))

cur.executemany("""
    INSERT INTO accounts (account_id, owner_id, balance, account_type, is_active, risk_level)
    VALUES (%s, %s, %s, %s, %s, %s)
""", accounts)

# ---- Vehicles ----
vehicles = []
used_plates = set()
while len(vehicles) < 100:
    license_plate = f"EU-{random.randint(1000,9999)}-{random.choice(['AA','BB','CC','DD'])}"
    if license_plate in used_plates:
        continue
    used_plates.add(license_plate)
    vtype = random.choice(vehicle_types)[0]
    model = random.choice(["Volkswagen", "BMW", "Audi", "Ford", "Toyota"])
    color = fake.safe_color_name()
    reg_date = fake.date_between(start_date='-2y', end_date='today')
    owner_id = random.choice(owners)[0]
    vehicles.append((license_plate, vtype, model, color, reg_date, owner_id))

cur.executemany("""
    INSERT INTO vehicles (license_plate, vehicle_type, model, color, registration_date, owner_id)
    VALUES (%s, %s, %s, %s, %s, %s)
""", vehicles)

# ---- RFID Tags ----
rfid_tags = []
used_tag_ids = set()
for vehicle in vehicles:
    if rand_bool(0.75):
        while True:
            tag_id = f"TAG{random.randint(100,999)}"
            if tag_id not in used_tag_ids:
                used_tag_ids.add(tag_id)
                break
        is_active = rand_bool(0.9)
        issue_date = datetime.now() - timedelta(days=random.randint(50, 300))
        expiry_date = issue_date + timedelta(days=365*3)
        rfid_tags.append((tag_id, is_active, issue_date, expiry_date, vehicle[0]))

cur.executemany("""
    INSERT INTO rfid_tags (tag_id, is_active, issue_date, expiry_date, vehicle_plate)
    VALUES (%s, %s, %s, %s, %s)
""", rfid_tags)

# ---- Blacklisted Tags ----
blacklisted_tags = random.sample(rfid_tags, min(2, len(rfid_tags)))
for tag in blacklisted_tags:
    cur.execute("""
        INSERT INTO blacklisted_rfid (tag_id, reason, blacklistedDate, reportedBy, severity)
        VALUES (%s, %s, %s, %s, %s)
    """, (tag[0], "Cloned tag", datetime.now(), "System", "HIGH"))

# ---- Stolen Vehicles ----
stolen_vehicles = random.sample(vehicles, min(2, len(vehicles)))
for vehicle in stolen_vehicles:
    cur.execute("""
        INSERT INTO stolen_vehicle_registry (licensePlate, vehicleID, reportedDate, reportingAgency, status)
        VALUES (%s, %s, %s, %s, TRUE)
    """, (vehicle[0], vehicle[0], datetime.now() - timedelta(days=15), fake.company()))

cur.close()
conn.close()
print("Database seeded with test data.")
