from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Bed, SystemEvent


class SystemService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def log_event(self, db: Session, level: str, component: str, message: str) -> SystemEvent:
        event = SystemEvent(level=level, component=component, message=message)
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    def get_status(self, db: Session, irrigation_running: bool, mqtt_connected: bool) -> dict[str, object]:
        bed_count = len(db.scalars(select(Bed)).all())
        return {
            "backend_reachable": True,
            "hardware_mock": self.settings.hardware_mock,
            "mqtt_enabled": self.settings.mqtt_enabled,
            "mqtt_connected": mqtt_connected,
            "bed_count": bed_count,
            "irrigation_running": irrigation_running,
            "max_watering_seconds": self.settings.max_watering_seconds,
            "dht21_enabled": self.settings.dht21_enabled,
            "dht21_gpio_pin": self.settings.dht21_gpio_pin,
        }
