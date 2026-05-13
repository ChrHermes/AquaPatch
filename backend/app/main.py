import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import beds, irrigation, moisture, system
from app.core.database import Base, SessionLocal, engine
from app.models import Bed
from app.services.registry import irrigation_service, moisture_service, mqtt_service, relay_service, system_service


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

DEFAULT_BEDS = [
    {"name": "Hochbeet 1", "relay_pin": 17, "ads_channel": 0, "watering_seconds": 120},
    {"name": "Tomaten", "relay_pin": 27, "ads_channel": 1, "watering_seconds": 120},
    {"name": "Blumen", "relay_pin": 22, "ads_channel": 2, "watering_seconds": 90},
]


def create_tables_and_seed() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        has_beds = db.scalars(select(Bed).limit(1)).first()
        if not has_beds:
            for item in DEFAULT_BEDS:
                db.add(Bed(**item))
            db.commit()
            system_service.log_event(db, "info", "startup", "Default-Beete wurden angelegt")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_tables_and_seed()
    with SessionLocal() as db:
        relay_service.setup(db)
    moisture_service.setup()
    mqtt_service.start()
    mqtt_service.publish_system_status()
    try:
        yield
    finally:
        irrigation_service.ensure_all_pumps_off()
        mqtt_service.publish_system_status()
        mqtt_service.stop()
        relay_service.cleanup()


app = FastAPI(title="AquaPatch API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(beds.router)
app.include_router(moisture.router)
app.include_router(irrigation.router)
app.include_router(system.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "AquaPatch", "status": "ok"}
