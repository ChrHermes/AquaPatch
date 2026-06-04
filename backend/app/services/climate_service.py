from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.hardware.dht21 import Dht21Reader
from app.integrations.mqtt_service import MqttService
from app.models import ClimateReading


class ClimateService:
    def __init__(self, reader: Dht21Reader, mqtt: MqttService | None = None) -> None:
        self.reader = reader
        self.mqtt = mqtt

    def setup(self) -> None:
        self.reader.setup()

    def read_and_store(self, db: Session) -> ClimateReading:
        temperature, humidity, error = self.reader.read()
        reading = ClimateReading(
            temperature_c=temperature,
            humidity_percent=humidity,
            source="mock" if self.reader.mock else "dht21",
            is_valid=error is None,
            error_message=error,
        )
        db.add(reading)
        db.commit()
        db.refresh(reading)
        if self.mqtt:
            self.mqtt.publish_climate(reading)
        return reading

    def latest_or_read(self, db: Session) -> ClimateReading:
        reading = db.scalars(select(ClimateReading).order_by(desc(ClimateReading.created_at)).limit(1)).first()
        if not self.reader.enabled:
            if reading is not None and not reading.is_valid and reading.error_message == "DHT21 ist deaktiviert":
                return reading
            return self.read_and_store(db)
        if reading is not None:
            return reading
        return self.read_and_store(db)
