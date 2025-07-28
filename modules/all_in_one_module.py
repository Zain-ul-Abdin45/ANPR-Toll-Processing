# =============================================
# TOLL GANTRY SYSTEM - APPLICATION MODULES
# =============================================

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import cv2
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import redis

# =============================================
# CONFIGURATION AND CONSTANTS
# =============================================

@dataclass
class SystemConfig:
    """System configuration parameters"""
    IMAGE_PROCESSING_INTERVAL = 30  # seconds
    RFID_SYNC_INTERVAL = 60  # seconds
    LOW_BALANCE_THRESHOLD = 50.00
    VIOLATION_GRACE_PERIOD = 7  # days
    MAX_TRANSACTION_RETRY = 3
    ANPR_CONFIDENCE_THRESHOLD = 85.0
    DEFAULT_TOLL_RATE = 5.50

class ImageQuality(Enum):
    HQ = "HQ"
    LQ = "LQ"
    POOR = "poor"

class TransactionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    DISPUTED = "disputed"

class PaymentMethod(Enum):
    RFID = "rfid"
    ANPR = "anpr"
    MANUAL = "manual"
    VIOLATION = "violation"

# =============================================
# DATABASE CONNECTION MANAGER
# =============================================

class DatabaseManager:
    """Manages database connections and transactions"""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def get_session(self):
        return self.SessionLocal()
    
    def execute_query(self, query: str, params: dict = None):
        with self.get_session() as session:
            return session.execute(text(query), params or {})

# =============================================
# IMAGE PROCESSING MODULE
# =============================================

class ImageProcessor:
    """Handles image capture, processing, and ANPR"""
    
    def __init__(self, db_manager: DatabaseManager, redis_client):
        self.db_manager = db_manager
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
        
    async def process_image_queue(self):
        """Continuously process images from queue"""
        while True:
            try:
                # Get pending images from database
                pending_images = await self.get_pending_images()
                
                for image_data in pending_images:
                    await self.process_single_image(image_data)
                    
                await asyncio.sleep(SystemConfig.IMAGE_PROCESSING_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Image processing error: {e}")
                await asyncio.sleep(10)
    
    async def get_pending_images(self) -> List[Dict]:
        """Get images pending processing"""
        query = """
        SELECT image_id, transaction_id, camera_id, image_path, capture_timestamp
        FROM captured_images 
        WHERE processing_status = 'pending'
        ORDER BY capture_timestamp ASC
        LIMIT 50
        """
        result = self.db_manager.execute_query(query)
        return [dict(row) for row in result]
    
    async def process_single_image(self, image_data: Dict):
        """Process a single image for license plate detection"""
        try:
            image_path = image_data['image_path']
            image_id = image_data['image_id']
            
            # Load and analyze image
            image = cv2.imread(image_path)
            if image is None:
                await self.update_image_status(image_id, 'failed', 0.0, None)
                return
            
            # Determine image quality
            quality = self.assess_image_quality(image)
            
            # Perform ANPR
            detected_plate, confidence = await self.perform_anpr(image, quality)
            
            # Update database with results
            await self.update_image_processing_result(
                image_id, detected_plate, confidence, quality
            )
            
            # If plate detected with high confidence, trigger transaction processing
            if detected_plate and confidence >= SystemConfig.ANPR_CONFIDENCE_THRESHOLD:
                await self.trigger_transaction_processing(image_data, detected_plate, confidence)
                
        except Exception as e:
            self.logger.error(f"Error processing image {image_data['image_id']}: {e}")
            await self.update_image_status(image_data['image_id'], 'failed', 0.0, None)
    
    def assess_image_quality(self, image) -> ImageQuality:
        """Assess image quality based on various metrics"""
        # Calculate image sharpness using Laplacian variance
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Calculate brightness
        brightness = np.mean(gray)
        
        # Determine quality based on metrics
        if laplacian_var > 500 and 50 <= brightness <= 200:
            return ImageQuality.HQ
        elif laplacian_var > 100:
            return ImageQuality.LQ
        else:
            return ImageQuality.POOR
    
    async def perform_anpr(self, image, quality: ImageQuality) -> Tuple[Optional[str], float]:
        """Perform Automatic Number Plate Recognition"""
        # Placeholder for ANPR implementation
        # In production, integrate with OpenALPR, EasyOCR, or custom ML model
        
        # Simulate ANPR processing based on image quality
        if quality == ImageQuality.HQ:
            # High quality images have better detection rates
            confidence = np.random.uniform(85, 98)
            # Simulate detected plate (in production, this would be actual ANPR)
            detected_plate = f"ABC{np.random.randint(1000, 9999)}"
        elif quality == ImageQuality.LQ:
            confidence = np.random.uniform(70, 85)
            detected_plate = f"XYZ{np.random.randint(1000, 9999)}" if confidence > 75 else None
        else:
            confidence = np.random.uniform(0, 40)
            detected_plate = None
            
        return detected_plate, confidence
    
    async def update_image_processing_result(self, image_id: str, detected_plate: str, 
                                           confidence: float, quality: ImageQuality):
        """Update image processing results in database"""
        status = 'processed' if detected_plate else 'manual_review'
        
        query = """
        UPDATE captured_images 
        SET processing_status = :status,
            confidence_score = :confidence,
            detected_plate = :detected_plate,
            image_quality = :quality
        WHERE image_id = :image_id
        """
        
        self.db_manager.execute_query(query, {
            'status': status,
            'confidence': confidence,
            'detected_plate': detected_plate,
            'quality': quality.value,
            'image_id': image_id
        })

# =============================================
# RFID PROCESSING MODULE
# =============================================

class RFIDProcessor:
    """Handles RFID tag detection and synchronization"""
    
    def __init__(self, db_manager: DatabaseManager, redis_client):
        self.db_manager = db_manager
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
    
    async def sync_rfid_data(self):
        """Continuously sync RFID data and check for stolen/blacklisted tags"""
        while True:
            try:
                await self.update_rfid_status()
                await self.sync_stolen_vehicle_registry()
                await self.process_rfid_detections()
                
                await asyncio.sleep(SystemConfig.RFID_SYNC_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"RFID sync error: {e}")
                await asyncio.sleep(30)
    
    async def update_rfid_status(self):
        """Update RFID tag statuses based on various criteria"""
        # Check for expired tags
        query = """
        UPDATE rfid_tags 
        SET status = 'inactive' 
        WHERE expiry_date < CURDATE() AND status = 'active'
        """
        self.db_manager.execute_query(query)
        
        # Check for tags with negative balance (for postpaid accounts)
        query = """
        UPDATE rfid_tags rt
        JOIN payment_accounts pa ON rt.license_plate IN (
            SELECT license_plate FROM vehicles WHERE owner_id = pa.owner_id
        )
        SET rt.status = 'inactive'
        WHERE pa.balance < -pa.credit_limit AND rt.status = 'active'
        """
        self.db_manager.execute_query(query)
    
    async def sync_stolen_vehicle_registry(self):
        """Sync with stolen vehicle registry and update blacklist"""
        query = """
        UPDATE rfid_tags rt
        JOIN stolen_vehicles sv ON rt.license_plate = sv.license_plate
        SET rt.is_blacklisted = TRUE
        WHERE sv.status = 'active'
        """
        self.db_manager.execute_query(query)
    
    async def process_rfid_detections(self):
        """Process recent RFID detections"""
        # Get recent unprocessed RFID detections
        query = """
        SELECT rd.detection_id, rd.tag_id, rd.reader_id, rd.detection_timestamp,
               rt.license_plate, rt.status, rt.is_blacklisted, rt.balance
        FROM rfid_detections rd
        JOIN rfid_tags rt ON rd.tag_id = rt.tag_id
        WHERE rd.transaction_id IS NULL
        AND rd.detection_timestamp > DATE_SUB(NOW(), INTERVAL 1 HOUR)
        ORDER BY rd.detection_timestamp ASC
        """
        
        detections = self.db_manager.execute_query(query)
        
        for detection in detections:
            await self.process_single_rfid_detection(dict(detection))
    
    async def process_single_rfid_detection(self, detection: Dict):
        """Process a single RFID detection"""
        try:
            # Check if tag is blacklisted or inactive
            if detection['is_blacklisted'] or detection['status'] != 'active':
                await self.handle_blacklisted_detection(detection)
                return
            
            # Get gantry info from reader
            gantry_info = await self.get_gantry_from_reader(detection['reader_id'])
            if not gantry_info:
                return
            
            # Create transaction
            transaction_id = await self.create_toll_transaction(
                detection, gantry_info, PaymentMethod.RFID
            )
            
            # Update detection with transaction ID
            await self.link_detection_to_transaction(
                detection['detection_id'], transaction_id
            )
            
        except Exception as e:
            self.logger.error(f"Error processing RFID detection: {e}")

# =============================================
# TRANSACTION PROCESSING MODULE
# =============================================

class TransactionProcessor:
    """Handles toll transaction processing and payment"""
    
    def __init__(self, db_manager: DatabaseManager, redis_client):
        self.db_manager = db_manager
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
    
    async def create_toll_transaction(self, detection_data: Dict, gantry_info: Dict, 
                                    payment_method: PaymentMethod) -> str:
        """Create a new toll transaction"""
        try:
            transaction_id = f"TXN_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{gantry_info['gantry_id']}"
            
            # Calculate toll amount based on gantry and vehicle type
            toll_amount = await self.calculate_toll_amount(
                detection_data.get('license_plate'), gantry_info['gantry_id']
            )
            
            # Insert transaction
            query = """
            INSERT INTO toll_transactions (
                transaction_id, gantry_id, license_plate, rfid_tag, timestamp,
                amount, payment_method, transaction_status, confidence_level
            ) VALUES (
                :transaction_id, :gantry_id, :license_plate, :rfid_tag, :timestamp,
                :amount, :payment_method, :status, :confidence_level
            )
            """
            
            self.db_manager.execute_query(query, {
                'transaction_id': transaction_id,
                'gantry_id': gantry_info['gantry_id'],
                'license_plate': detection_data.get('license_plate'),
                'rfid_tag': detection_data.get('tag_id'),
                'timestamp': detection_data.get('detection_timestamp', datetime.now()),
                'amount': toll_amount,
                'payment_method': payment_method.value,
                'status': TransactionStatus.PENDING.value,
                'confidence_level': detection_data.get('confidence', 100.0)
            })
            
            # Process payment
            await self.process_payment(transaction_id, detection_data, toll_amount)
            
            return transaction_id
            
        except Exception as e:
            self.logger.error(f"Error creating transaction: {e}")
            raise
    
    async def process_payment(self, transaction_id: str, detection_data: Dict, amount: float):
        """Process payment for toll transaction"""
        try:
            license_plate = detection_data.get('license_plate')
            tag_id = detection_data.get('tag_id')
            
            # Get payment account information
            account_info = await self.get_payment_account_info(license_plate)
            
            if not account_info:
                await self.handle_no_payment_account(transaction_id, license_plate)
                return
            
            # Check if sufficient balance
            if account_info['balance'] >= amount:
                # Process successful payment
                await self.process_successful_payment(transaction_id, account_info, amount)
            else:
                # Handle insufficient balance
                await self.handle_insufficient_balance(transaction_id, account_info, amount)
                
        except Exception as e:
            self.logger.error(f"Error processing payment for transaction {transaction_id}: {e}")
            await self.update_transaction_status(transaction_id, TransactionStatus.FAILED)
    
    async def process_successful_payment(self, transaction_id: str, account_info: Dict, amount: float):
        """Process successful payment and update balances"""
        try:
            # Deduct amount from account
            query = """
            UPDATE payment_accounts 
            SET balance = balance - :amount,
                updated_at = NOW()
            WHERE account_id = :account_id
            """
            self.db_manager.execute_query(query, {
                'amount': amount,
                'account_id': account_info['account_id']
            })
            
            # Update RFID tag balance if applicable
            if account_info.get('rfid_tag'):
                query = """
                UPDATE rfid_tags 
                SET balance = balance - :amount,
                    updated_at = NOW()
                WHERE tag_id = :tag_id
                """
                self.db_manager.execute_query(query, {
                    'amount': amount,
                    'tag_id': account_info['rfid_tag']
                })
            
            # Update transaction status
            await self.update_transaction_status(transaction_id, TransactionStatus.SUCCESS)
            
            # Check if balance is below threshold for notification
            if (account_info['balance'] - amount) < SystemConfig.LOW_BALANCE_THRESHOLD:
                await self.send_low_balance_notification(account_info)
                
        except Exception as e:
            self.logger.error(f"Error processing successful payment: {e}")
            await self.update_transaction_status(transaction_id, TransactionStatus.FAILED)
    
    async def handle_insufficient_balance(self, transaction_id: str, account_info: Dict, amount: float):
        """Handle insufficient balance scenario"""
        # Check if account has credit limit
        if account_info['account_type'] == 'credit' and account_info['credit_limit'] > 0:
            available_credit = account_info['credit_limit'] + account_info['balance']
            if available_credit >= amount:
                # Use credit
                await self.process_successful_payment(transaction_id, account_info, amount)
                await self.send_credit_usage_notification(account_info)
                return
        
        # Insufficient funds - create violation
        await self.create_payment_violation(transaction_id, account_info, amount)
        await self.send_payment_due_notification(account_info, amount)
    
    async def calculate_toll_amount(self, license_plate: str, gantry_id: str) -> float:
        """Calculate toll amount based on vehicle type and gantry"""
        # Get vehicle type and gantry toll rate
        query = """
        SELECT v.vehicle_type, tg.toll_rate
        FROM vehicles v
        CROSS JOIN toll_gantries tg
        WHERE v.license_plate = :license_plate 
        AND tg.gantry_id = :gantry_id
        """
        
        result = self.db_manager.execute_query(query, {
            'license_plate': license_plate,
            'gantry_id': gantry_id
        }).fetchone()
        
        if not result:
            return SystemConfig.DEFAULT_TOLL_RATE
        
        base_rate = result['toll_rate']
        vehicle_type = result['vehicle_type']
        
        # Apply vehicle type multipliers
        multipliers = {
            'car': 1.0,
            'motorcycle': 0.5,
            'truck': 2.0,
            'bus': 1.5,
            'commercial': 2.5
        }
        
        return base_rate * multipliers.get(vehicle_type, 1.0)

# =============================================
# NOTIFICATION MODULE
# =============================================

class NotificationManager:
    """Handles all system notifications"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    async def send_notification(self, recipient_type: str, recipient_id: str, 
                              message: str, notification_type: str, priority: str = 'medium'):
        """Send notification to user"""
        try:
            notification_id = f"NOT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{recipient_id}"
            
            query = """
            INSERT INTO notifications (
                notification_id, recipient_type, recipient_id, message,
                notification_type, priority, status, created_at
            ) VALUES (
                :notification_id, :recipient_type, :recipient_id, :message,
                :notification_type, :priority, 'pending', NOW()
            )
            """
            
            self.db_manager.execute_query(query, {
                'notification_id': notification_id,
                'recipient_type': recipient_type,
                'recipient_id': recipient_id,
                'message': message,
                'notification_type': notification_type,
                'priority': priority
            })
            
            # Queue for actual delivery (email, SMS, etc.)
            await self.queue_notification_delivery(notification_id)
            
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
    
    async def send_low_balance_notification(self, account_info: Dict):
        """Send low balance notification"""
        message = f"Your toll account balance is low: ${account_info['balance']:.2f}. Please top up to avoid service interruption."
        
        await self.send_notification(
            'owner', account_info['owner_id'], message, 'low_balance', 'high'
        )
    
    async def send_payment_due_notification(self, account_info: Dict, amount: float):
        """Send payment due notification"""
        grace_period = SystemConfig.VIOLATION_GRACE_PERIOD
        message = f"Payment due: ${amount:.2f} for toll usage. Please pay within {grace_period} days to avoid penalties."
        
        await self.send_notification(
            'owner', account_info['owner_id'], message, 'payment_due', 'high'
        )

# =============================================
# VIOLATION MANAGEMENT MODULE
# =============================================

class ViolationManager:
    """Handles traffic violations and enforcement"""
    
    def __init__(self, db_manager: DatabaseManager, notification_manager: NotificationManager):
        self.db_manager = db_manager
        self.notification_manager = notification_manager
        self.logger = logging.getLogger(__name__)
    
    async def create_payment_violation(self, transaction_id: str, account_info: Dict, amount: float):
        """Create a payment violation record"""
        try:
            violation_id = f"VIO_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{transaction_id}"
            
            # Calculate penalty based on amount and grace period
            penalty_amount = amount * 0.5  # 50% penalty
            
            query = """
            INSERT INTO violations (
                violation_id, transaction_id, license_plate, violation_type,
                gantry_id, timestamp, amount_due, penalty_amount, status
            )
            SELECT 
                :violation_id, :transaction_id, tt.license_plate, 'no_payment',
                tt.gantry_id, tt.timestamp, :amount_due, :penalty_amount, 'open'
            FROM toll_transactions tt
            WHERE tt.transaction_id = :transaction_id
            """
            
            self.db_manager.execute_query(query, {
                'violation_id': violation_id,
                'transaction_id': transaction_id,
                'amount_due': amount,
                'penalty_amount': penalty_amount
            })
            
            # Send violation notification
            await self.send_violation_notification(violation_id, account_info, amount, penalty_amount)
            
        except Exception as e:
            self.logger.error(f"Error creating violation: {e}")
    
    async def check_stolen_vehicle_violations(self):
        """Check for stolen vehicle violations"""
        query = """
        SELECT DISTINCT tt.transaction_id, tt.license_plate, tt.gantry_id, tt.timestamp
        FROM toll_transactions tt
        JOIN stolen_vehicles sv ON tt.license_plate = sv.license_plate
        WHERE sv.status = 'active'
        AND NOT EXISTS (
            SELECT 1 FROM violations v 
            WHERE v.transaction_id = tt.transaction_id 
            AND v.violation_type = 'stolen_vehicle'
        )
        AND tt.timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """
        
        results = self.db_manager.execute_query(query)
        
        for result in results:
            await self.create_stolen_vehicle_alert(dict(result))

# =============================================
# SECURITY MODULE
# =============================================

class SecurityManager:
    """Handles security monitoring and alerts"""
    
    def __init__(self, db_manager: DatabaseManager, notification_manager: NotificationManager):
        self.db_manager = db_manager
        self.notification_manager = notification_manager
        self.logger = logging.getLogger(__name__)
    
    async def monitor_security_events(self):
        """Continuously monitor for security events"""
        while True:
            try:
                await self.check_equipment_tampering()
                await self.monitor_system_health()
                await self.detect_anomalous_patterns()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Security monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def check_equipment_tampering(self):
        """Check for equipment tampering indicators"""
        # Check for cameras going offline unexpectedly
        query = """
        SELECT camera_id, gantry_id, last_heartbeat
        FROM anpr_cameras
        WHERE status = 'offline'
        AND last_heartbeat < DATE_SUB(NOW(), INTERVAL 5 MINUTE)
        AND is_active = TRUE
        """
        
        offline_cameras = self.db_manager.execute_query(query)
        
        for camera in offline_cameras:
            await self.create_security_incident(
                dict(camera), 'equipment_tampering', 'Camera unexpectedly offline'
            )
    
    async def create_security_incident(self, equipment_data: Dict, incident_type: str, description: str):
        """Create a security incident record"""
        try:
            incident_id = f"SEC_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{equipment_data.get('gantry_id', 'UNK')}"
            
            query = """
            INSERT INTO security_incidents (
                incident_id, gantry_id, incident_type, severity, timestamp,
                description, investigation_status
            ) VALUES (
                :incident_id, :gantry_id, :incident_type, 'medium', NOW(),
                :description, 'open'
            )
            """
            
            self.db_manager.execute_query(query, {
                'incident_id': incident_id,
                'gantry_id': equipment_data.get('gantry_id'),
                'incident_type': incident_type,
                'description': description
            })
            
            # Send security alert
            await self.notification_manager.send_notification(
                'security', 'security_team', 
                f"Security incident: {description} at gantry {equipment_data.get('gantry_id')}",
                'security_alert', 'high'
            )
            
        except Exception as e:
            self.logger.error(f"Error creating security incident: {e}")

# =============================================
# MAIN ORCHESTRATOR
# =============================================

class TollSystemOrchestrator:
    """Main orchestrator that coordinates all modules"""
    
    def __init__(self, database_url: str, redis_url: str):
        self.db_manager = DatabaseManager(database_url)
        self.redis_client = redis.from_url(redis_url)
        
        # Initialize modules
        self.notification_manager = NotificationManager(self.db_manager)
        self.image_processor = ImageProcessor(self.db_manager, self.redis_client)
        self.rfid_processor = RFIDProcessor(self.db_manager, self.redis_client)
        self.transaction_processor = TransactionProcessor(self.db_manager, self.redis_client)
        self.violation_manager = ViolationManager(self.db_manager, self.notification_manager)
        self.security_manager = SecurityManager(self.db_manager, self.notification_manager)
        
        self.logger = logging.getLogger(__name__)
    
    async def start_system(self):
        """Start all system processes"""
        self.logger.info("Starting Toll Gantry System...")
        
        # Create tasks for all continuous processes
        tasks = [
            asyncio.create_task(self.image_processor.process_image_queue()),
            asyncio.create_task(self.rfid_processor.sync_rfid_data()),
            asyncio.create_task(self.security_manager.monitor_security_events()),
            asyncio.create_task(self.process_violation_checks()),
            asyncio.create_task(self.system_maintenance_tasks())
        ]
        
        # Wait for all tasks to complete (they run indefinitely)
        await asyncio.gather(*tasks)
    
    async def process_violation_checks(self):
        """Periodic violation checks"""
        while True:
            try:
                await self.violation_manager.check_stolen_vehicle_violations()
                await self.check_overdue_payments()
                
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                self.logger.error(f"Violation check error: {e}")
                await asyncio.sleep(300)
    
    async def system_maintenance_tasks(self):
        """System maintenance and cleanup tasks"""
        while True:
            try:
                await self.cleanup_old_images()
                await self.update_system_health_metrics()
                await self.generate_daily_reports()
                
                await asyncio.sleep(86400)  # Daily maintenance
                
            except Exception as e:
                self.logger.error(f"Maintenance task error: {e}")
                await asyncio.sleep(3600)
    
    async def cleanup_old_images(self):
        """Clean up old processed images"""
        retention_days = 90  # Keep images for 90 days
        
        query = """
        DELETE FROM captured_images 
        WHERE capture_timestamp < DATE_SUB(NOW(), INTERVAL :retention_days DAY)
        AND processing_status IN ('processed', 'failed')
        """
        
        self.db_manager.execute_query(query, {'retention_days': retention_days})
        self.logger.info(f"Cleaned up images older than {retention_days} days")

# =============================================
# SYSTEM STARTUP
# =============================================

async def main():
    """Main entry point for the toll system"""
    # Configuration
    DATABASE_URL = "mysql://user:password@localhost/toll_system"
    REDIS_URL = "redis://localhost:6379"
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start system
    system = TollSystemOrchestrator(DATABASE_URL, REDIS_URL)
    await system.start_system()

if __name__ == "__main__":
    asyncio.run(main())