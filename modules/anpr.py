import simpy
import random
from sql import get_plates, get_number_plate


class ANPRCamera:
    def __init__(self, env, camera_id, location, interval=5):
        self.env = env
        self.camera_id = camera_id
        self.location = location
        self.interval = interval  # time between captures
        self.process = env.process(self.run())

    def run(self):
        while True:
            yield self.env.timeout(self.interval)  # Wait for next capture time
            image = self.capture_image()
            plate, confidence = self.recognize_plate(image)
            anomaly = self.detect_anomalies(image)

            if plate == "UNKNOWN" or confidence < 0.6 or anomaly:
                vehicle = UnidentifiedVehicle(
                    location=self.location,
                    captured_plate=plate,
                    image_url=image,
                    confidence_level=confidence
                )
                vehicle.flag_for_review()
            else:
                print(f"{self.env.now}: Camera-{self.camera_id} detected plate '{plate}' confidently at {self.location}.")

    def capture_image(self):
        print(f"{self.env.now}: Camera-{self.camera_id} capturing image at {self.location}...")
        return f"image_from_camera_{self.camera_id}"

    def recognize_plate(self, image):
        plate_number = get_number_plate(image)
        confidence_level = round(random.uniform(0, 1), 2)
        validated_plate, validated_confidence = get_plates(plate_number, confidence_level)
        print(f"{self.env.now}: Detected Plate: {plate_number}, Validated: {validated_plate} (Conf: {validated_confidence})")
        return validated_plate, validated_confidence or 0.0

    def detect_anomalies(self, image):
        anomaly = random.choice([True, False, False, False])
        if anomaly:
            print(f"{self.env.now}: Anomaly detected in image: {image}")
        return anomaly


class UnidentifiedVehicle:
    def __init__(self, location, captured_plate, image_url, confidence_level):
        self.location = location
        self.captured_plate = captured_plate
        self.image_url = image_url
        self.confidence_level = confidence_level
        self.flagged = False

    def flag_for_review(self):
        self.flagged = True
        print(f"Vehicle with plate '{self.captured_plate}' at {self.location} flagged for review (Confidence: {self.confidence_level})")


# --- SimPy Simulation Environment ---

if __name__ == "__main__":
    env = simpy.Environment()
    print("Starting ANPR Camera Simulation...")
    camera1 = ANPRCamera(env, camera_id=1, location="Main Gate", interval=4)
    camera2 = ANPRCamera(env, camera_id=2, location="Back Entrance", interval=6)
    env.run(until=30)  # Run simulation for 30 time units
    print("Simulation completed.")