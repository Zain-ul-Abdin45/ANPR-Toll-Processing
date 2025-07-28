from fastapi import FastAPI
from api.vehicle_routes import router as vehicle_router
from api.rfid_routes import router as rfid_router
from api.notification_routes import router as notif_router
from api.security_routes import router as security_router
from api.toll_routes import router as toll_router



print("Starting ANPR API...")
app = FastAPI(title="ANPR Vehicle Toll API")

app.include_router(vehicle_router, prefix="/vehicle", tags=["Vehicle"])
app.include_router(rfid_router, prefix="/rfid", tags=["RFID"])
app.include_router(notif_router, prefix="/notifications", tags=["Notifications"])
app.include_router(security_router, prefix="/security", tags=["Security"])
app.include_router(toll_router, prefix="/toll", tags=["Toll"])

@app.get("/")
def root():
    return {"message": "ANPR API is running"}
