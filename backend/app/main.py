import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, select, text

from app.api import beds, climate, irrigation, moisture, summary, system
from app.core.database import Base, SessionLocal, engine
from app.models import Bed
from app.services.registry import climate_service, irrigation_service, moisture_service, mqtt_service, relay_service, system_service


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

DEFAULT_BEDS = [
    {"name": "Tomaten", "relay_pin": 17, "ads_channel": 0, "watering_seconds": 120},
    {"name": "Hortensien 1", "relay_pin": 27, "ads_channel": 1, "watering_seconds": 90},
    {"name": "Hortensien 2", "relay_pin": 22, "ads_channel": 2, "watering_seconds": 90},
]


def create_tables_and_seed() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema_columns()
    with SessionLocal() as db:
        has_beds = db.scalars(select(Bed).limit(1)).first()
        if not has_beds:
            for item in DEFAULT_BEDS:
                db.add(Bed(**item))
            db.commit()
            system_service.log_event(db, "info", "startup", "Default-Beete wurden angelegt")


def ensure_schema_columns() -> None:
    inspector = inspect(engine)
    if "beds" in inspector.get_table_names():
        bed_columns = {column["name"] for column in inspector.get_columns("beds")}
        with engine.begin() as connection:
            if "auto_watering_block_after_cancel_seconds" not in bed_columns:
                connection.execute(
                    text("ALTER TABLE beds ADD COLUMN auto_watering_block_after_cancel_seconds INTEGER NOT NULL DEFAULT 3600")
                )
            if "last_cancelled_at" not in bed_columns:
                connection.execute(text("ALTER TABLE beds ADD COLUMN last_cancelled_at DATETIME"))
            if "sensor_disconnected_raw_threshold" not in bed_columns:
                connection.execute(text("ALTER TABLE beds ADD COLUMN sensor_disconnected_raw_threshold INTEGER NOT NULL DEFAULT 5000"))
            connection.execute(text("UPDATE beds SET sensor_disconnected_raw_threshold = 5000 WHERE sensor_disconnected_raw_threshold = 8000"))
            connection.execute(
                text(
                    "UPDATE beds "
                    "SET moisture_dry_raw = 17750, moisture_wet_raw = 7700 "
                    "WHERE moisture_dry_raw = 26000 AND moisture_wet_raw = 12000"
                )
            )
    if "moisture_readings" in inspector.get_table_names():
        reading_columns = {column["name"] for column in inspector.get_columns("moisture_readings")}
        with engine.begin() as connection:
            if "is_valid" not in reading_columns:
                connection.execute(text("ALTER TABLE moisture_readings ADD COLUMN is_valid BOOLEAN NOT NULL DEFAULT 1"))
            if "warning_code" not in reading_columns:
                connection.execute(text("ALTER TABLE moisture_readings ADD COLUMN warning_code VARCHAR(80)"))
            if "warning_message" not in reading_columns:
                connection.execute(text("ALTER TABLE moisture_readings ADD COLUMN warning_message TEXT"))
    if "irrigation_runs" in inspector.get_table_names():
        run_columns = {column["name"] for column in inspector.get_columns("irrigation_runs")}
        with engine.begin() as connection:
            if "status" not in run_columns:
                connection.execute(text("ALTER TABLE irrigation_runs ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'completed'"))
            if "moisture_before_percent" not in run_columns:
                connection.execute(text("ALTER TABLE irrigation_runs ADD COLUMN moisture_before_percent FLOAT"))
            if "moisture_after_percent" not in run_columns:
                connection.execute(text("ALTER TABLE irrigation_runs ADD COLUMN moisture_after_percent FLOAT"))
            if "moisture_before_raw" not in run_columns:
                connection.execute(text("ALTER TABLE irrigation_runs ADD COLUMN moisture_before_raw INTEGER"))
            if "moisture_after_raw" not in run_columns:
                connection.execute(text("ALTER TABLE irrigation_runs ADD COLUMN moisture_after_raw INTEGER"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_tables_and_seed()
    with SessionLocal() as db:
        relay_service.setup(db)
    moisture_service.setup()
    climate_service.setup()
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
app.include_router(climate.router)
app.include_router(moisture.router)
app.include_router(irrigation.router)
app.include_router(summary.router)
app.include_router(system.router)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
FRONTEND_ASSETS = FRONTEND_DIST / "assets"

if FRONTEND_ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS), name="assets")


@app.get("/", response_model=None)
def root() -> dict[str, str] | FileResponse:
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"name": "AquaPatch", "status": "ok"}
