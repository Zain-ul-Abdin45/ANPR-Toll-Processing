CREATE TABLE stolen_vehicle_registry (
    registerID SERIAL PRIMARY KEY,
    licensePlate VARCHAR NOT NULL,
    vehicleID VARCHAR,
    reportedDate DATE,
    reportingAgency VARCHAR,
    status BOOLEAN
);


CREATE TABLE blacklisted_rfid (
    blacklistID SERIAL PRIMARY KEY,
    tagID VARCHAR NOT NULL,
    reason TEXT NOT NULL,
    blacklistedDate DATE DEFAULT CURRENT_DATE,
    reportedBy VARCHAR,
    severity VARCHAR
);


INSERT INTO blacklisted_rfid (tagID, reason, reportedBy, severity)
VALUES ('TAG002', 'Cloned tag detected', 'System', 'HIGH');

ALTER TABLE blacklisted_rfid RENAME COLUMN tagid TO tag_id;


CREATE TABLE notification (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    type VARCHAR NOT NULL,
    priority VARCHAR NOT NULL
);

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

notification_id SERIAL PRIMARY KEY


SELECT * FROM notification LIMIT 1



CREATE INDEX idx_notification_type ON notification(type);
CREATE INDEX idx_notification_priority ON notification(priority);



select * from toll_transactions
select * from stolen_vehicle_registry

select vc.license_plate, rt.tag_id
from vehicles vc
inner join rfid_tags rt on vc.vehicle_id = rt.vehicle_id

select * from rfid_tags

-- TAG999 no license plate found -- use case
where vehicle_plate = 'EU-4567-ZZ'
where owner_id = 'OWN082'
order by balance 
; -- OWN082

select * from public.notification --where owner_id = 'OWN082'

select * from owners

CREATE TABLE security_alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_type TEXT NOT NULL,
    priority TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL
);


CREATE TABLE security_incidents (
    incident_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_type TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    location TEXT,
    severity TEXT,
    reported_by TEXT,
    status TEXT NOT NULL DEFAULT 'Open'
);

select * from vehicles;

ALTER TABLE vehicles
ADD COLUMN vehicle_id UUID DEFAULT gen_random_uuid();

ALTER TABLE vehicles
ADD PRIMARY KEY (vehicle_id);


ALTER TABLE vehicles
ALTER COLUMN license_plate DROP NOT NULL;

CREATE UNIQUE INDEX unique_plate_non_null
ON vehicles(license_plate)
WHERE license_plate IS NOT NULL;

ALTER TABLE rfid_tags ADD COLUMN vehicle_id UUID;


UPDATE rfid_tags rt
SET vehicle_id = v.vehicle_id
FROM vehicles v
WHERE rt.vehicle_plate = v.license_plate;

ALTER TABLE rfid_tags DROP COLUMN vehicle_plate;

ALTER TABLE rfid_tags
ADD CONSTRAINT rfid_tags_vehicle_id_fkey
FOREIGN KEY (vehicle_id)
REFERENCES vehicles(vehicle_id);






ALTER TABLE vehicles DROP CONSTRAINT vehicles_pkey CASCADE;


ALTER TABLE vehicles
ADD COLUMN vehicle_id UUID DEFAULT gen_random_uuid() PRIMARY KEY;


ALTER TABLE vehicles
ALTER COLUMN license_plate DROP NOT NULL;



ALTER TABLE notification
ADD COLUMN vehicle_id UUID;

ALTER TABLE notification
ADD COLUMN plaza_id VARCHAR;


select * from notification order by timestamp desc


CREATE TABLE pending_toll_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL REFERENCES vehicles(vehicle_id),
    plaza_id VARCHAR(20) NOT NULL REFERENCES toll_plazas(plaza_id),
    amount NUMERIC NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE
);

-- Optional: Find current primary key constraint
ALTER TABLE pending_toll_ledger
DROP CONSTRAINT pending_toll_ledger_pkey;



ALTER TABLE pending_toll_ledger
ADD COLUMN ledger_id UUID DEFAULT gen_random_uuid();

ALTER TABLE pending_toll_ledger
ADD PRIMARY KEY (ledger_id);


CREATE TABLE pending_toll_ledger (
    ledger_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID REFERENCES vehicles(vehicle_id),
    tag_id VARCHAR(50) REFERENCES rfid_tags(tag_id),
    plaza_id VARCHAR(10) REFERENCES toll_plazas(plaza_id),
    amount NUMERIC(10,2),
    timestamp TIMESTAMP DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE
);

ALTER TABLE pending_toll_ledger
ADD COLUMN amount_due NUMERIC(10, 2);


ALTER TABLE pending_toll_ledger
ADD COLUMN created_at TIMESTAMP DEFAULT NOW();






SELECT * FROM vehicles WHERE license_plate = 'EU-3416-CC';

select rt.*, v.*
from vehicles v
left join rfid_tags rt on rt.vehicle_id = v.vehicle_id
where v.license_plate = 'EU-3416-CC'


-- Testing level 2 :
-- Correct Plaza
-- Mismatched Tag and license plates --> goes to deduct amount

--PLZ008
-- EU-3756-AA


select * from vehicles;

select * from toll_plazas


select * from blacklisted_rfid -- TAG211 duplicate blacklisted a unique should exist only -- 342 blacklisted through server but not available in DB


select * from rfid_tags --where tag_id= 'TAG112'
order by tag_id desc;


select * from vehicles
where license_plate = 'EU-4567-ZZ'



ALTER TABLE vehicles ADD CONSTRAINT unique_plate UNIQUE (license_plate);


select * from toll_plazas


ALTER TABLE notification ADD COLUMN status VARCHAR DEFAULT 'unread';



        SELECT v.*, r.*
        FROM vehicles v
        LEFT JOIN rfid_tags r ON r.vehicle_id = v.vehicle_id
		
		--where license_plate is NULL
		
		where license_plate = 'EU-4101-BB'
--        WHERE r.tag_id = 'TAG211' AND r.is_active = TRUE



		SELECT license_plate, vehicle_type, owner_id FROM vehicles WHERE license_plate = 'EU-3497-CC'


select * from notification order by timestamp desc;


select * from vehicles r
inner join ;


select * 
from lov_fines;

select *
from lov_vehicle_types
