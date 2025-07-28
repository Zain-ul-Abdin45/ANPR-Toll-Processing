-- ========================
-- SCHEMA: ANPR Database
-- ========================

-- 1. OWNERS TABLE
CREATE TABLE owners (
    owner_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    phone_number VARCHAR,
    email VARCHAR,
    address VARCHAR
);

CREATE INDEX idx_owners_email ON owners(email);

-- 2. VEHICLES TABLE
CREATE TABLE vehicles (
    license_plate VARCHAR PRIMARY KEY,
    vehicle_type VARCHAR,
    model VARCHAR,
    color VARCHAR,
    registration_date DATE,
    owner_id VARCHAR REFERENCES owners(owner_id) ON DELETE SET NULL
);

CREATE INDEX idx_vehicles_owner_id ON vehicles(owner_id);
CREATE INDEX idx_vehicles_license_plate ON vehicles(license_plate);

-- 3. RFID TAGS TABLE
CREATE TABLE rfid_tags (
    tag_id VARCHAR PRIMARY KEY,
    is_active BOOLEAN DEFAULT TRUE,
    issue_date DATE,
    expiry_date DATE,
    vehicle_plate VARCHAR REFERENCES vehicles(license_plate) ON DELETE CASCADE
);

CREATE INDEX idx_rfid_vehicle_plate ON rfid_tags(vehicle_plate);

-- 4. TOLL PLAZAS TABLE
CREATE TABLE toll_plazas (
    plaza_id VARCHAR PRIMARY KEY,
    location VARCHAR,
    highway VARCHAR,
    is_operational BOOLEAN DEFAULT TRUE,
    security_level VARCHAR
);

-- 5. TOLL TRANSACTIONS TABLE
CREATE TABLE toll_transactions (
    transaction_id VARCHAR PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    amount DOUBLE PRECISION,
    distance DOUBLE PRECISION,
    status VARCHAR,
    security_flag BOOLEAN DEFAULT FALSE,
    rfid_tag_id VARCHAR REFERENCES rfid_tags(tag_id),
    plaza_id VARCHAR REFERENCES toll_plazas(plaza_id)
);

CREATE INDEX idx_transaction_tag_id ON toll_transactions(rfid_tag_id);
CREATE INDEX idx_transaction_plaza_id ON toll_transactions(plaza_id);
CREATE INDEX idx_transaction_timestamp ON toll_transactions(timestamp);

-- 6. ANPR CAPTURES TABLE
CREATE TABLE anpr_captures (
    capture_id SERIAL PRIMARY KEY,
    camera_id VARCHAR,
    captured_plate VARCHAR,
    timestamp TIMESTAMPTZ,
    confidence_level DOUBLE PRECISION,
    image_url TEXT
);

CREATE INDEX idx_anpr_plate ON anpr_captures(captured_plate);
CREATE INDEX idx_anpr_timestamp ON anpr_captures(timestamp);


CREATE TABLE accounts (
    account_id VARCHAR PRIMARY KEY,
    owner_id VARCHAR UNIQUE REFERENCES owners(owner_id) ON DELETE CASCADE,
    balance DOUBLE PRECISION DEFAULT 0.0,
    account_type VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    risk_level VARCHAR
);

CREATE INDEX idx_accounts_owner_id ON accounts(owner_id);


CREATE TABLE lov_vehicle_types (
    type_code VARCHAR PRIMARY KEY,
    description VARCHAR,
    base_cost DOUBLE PRECISION NOT NULL
);



CREATE TABLE lov_fines (
    fine_code VARCHAR PRIMARY KEY,
    description VARCHAR,
    fine_amount DOUBLE PRECISION NOT NULL
);