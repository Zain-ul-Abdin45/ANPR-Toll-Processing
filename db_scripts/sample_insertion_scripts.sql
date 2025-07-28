INSERT INTO owners (owner_id, name, phone_number, email, address) VALUES
('OWN001', 'Alice Smith', '1234567890', 'alice@example.com', '123 Elm Street'),
('OWN002', 'Bob Johnson', '2345678901', 'bob@example.com', '456 Oak Avenue'),
('OWN003', 'Charlie Brown', '3456789012', 'charlie@example.com', '789 Pine Lane');


INSERT INTO vehicles (license_plate, vehicle_type, model, color, registration_date, owner_id) VALUES
('EU-1234-AA', 'Sedan', 'Volkswagen Passat', 'Blue', '2023-01-15', 'OWN001'),
('EU-5678-BB', 'SUV', 'Audi Q5', 'Black', '2022-06-30', 'OWN002'),
('EU-9876-CC', 'Truck', 'Mercedes Actros', 'White', '2021-12-20', 'OWN003');


INSERT INTO rfid_tags (tag_id, is_active, issue_date, expiry_date, vehicle_plate) VALUES
('TAG001', TRUE, '2023-01-15', '2026-01-15', 'EU-1234-AA'),
('TAG002', TRUE, '2022-06-30', '2025-06-30', 'EU-5678-BB'),
('TAG003', FALSE, '2021-12-20', '2024-12-20', 'EU-9876-CC');

INSERT INTO toll_plazas (plaza_id, location, highway, is_operational, security_level) VALUES
('PLZ001', 'Berlin North', 'A10', TRUE, 'High'),
('PLZ002', 'Munich West', 'A9', TRUE, 'Medium');



INSERT INTO toll_transactions (transaction_id, timestamp, amount, distance, status, security_flag, rfid_tag_id, plaza_id) VALUES
('TXN001', NOW(), 5.50, 15.2, 'SUCCESS', FALSE, 'TAG001', 'PLZ001'),
('TXN002', NOW(), 7.20, 20.5, 'SUCCESS', FALSE, 'TAG002', 'PLZ002'),
('TXN003', NOW(), 0.00, 0.0, 'FAILED', TRUE, 'TAG003', 'PLZ001');



INSERT INTO anpr_captures (camera_id, captured_plate, timestamp, confidence_level, image_url) VALUES
('CAM001', 'EU-1234-AA', NOW(), 0.98, 'http://example.com/img/plate1.jpg'),
('CAM002', 'EU-5678-BB', NOW(), 0.95, 'http://example.com/img/plate2.jpg'),
('CAM003', 'EU-9876-CC', NOW(), 0.80, 'http://example.com/img/plate3.jpg');



INSERT INTO lov_vehicle_types (type_code, description, base_cost) VALUES
('SEDAN', 'Standard Sedan', 5.00),
('SUV', 'Sport Utility Vehicle', 6.50),
('TRUCK', 'Heavy Truck', 8.75);


INSERT INTO lov_fines (fine_code, description, fine_amount) VALUES
('EXPIRED_TAG', 'Tag expired', 100.00),
('BLACKLISTED', 'Blacklisted tag used', 250.00),
('STOLEN', 'Stolen vehicle detected', 500.00);


INSERT INTO accounts (account_id, owner_id, balance, account_type, is_active, risk_level) VALUES
('ACC001', 'OWN001', 25.00, 'PERSONAL', TRUE, 'LOW'),
('ACC002', 'OWN002', 5.50, 'PERSONAL', TRUE, 'MEDIUM'),
('ACC003', 'OWN003', 0.00, 'CORPORATE', TRUE, 'HIGH');