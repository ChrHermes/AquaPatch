from sqlalchemy.orm import Session

from app.hardware.ads1115 import Ads1115Reader
from app.integrations.mqtt_service import MqttService
from app.models import Bed, MoistureReading

SENSOR_DISCONNECTED_MESSAGE = "Sensor scheint nicht angeschlossen zu sein oder liefert einen unrealistisch niedrigen Rohwert."


class MoistureService:
    def __init__(self, reader: Ads1115Reader, mqtt: MqttService | None = None) -> None:
        self.reader = reader
        self.mqtt = mqtt

    def setup(self) -> None:
        self.reader.setup()

    def read_raw(self, bed: Bed) -> int:
        return self.reader.read_raw(bed.ads_channel)

    def read_voltage(self, bed: Bed) -> float:
        return self.reader.read_voltage(bed.ads_channel)

    def read_percent(self, bed: Bed, raw_value: int | None = None) -> float:
        raw = self.read_raw(bed) if raw_value is None else raw_value
        dry = bed.moisture_dry_raw
        wet = bed.moisture_wet_raw
        if dry == wet:
            return 0.0

        # Works for normal and inverted sensors: dry maps to 0, wet maps to 100.
        percent = (raw - dry) / (wet - dry) * 100
        return round(max(0.0, min(100.0, percent)), 1)

    def warning_for_raw(self, bed: Bed, raw_value: int) -> tuple[bool, str | None, str | None]:
        if raw_value < bed.sensor_disconnected_raw_threshold:
            return False, "sensor_disconnected", SENSOR_DISCONNECTED_MESSAGE
        return True, None, None

    def read_and_store(self, db: Session, bed: Bed) -> MoistureReading:
        raw = self.read_raw(bed)
        voltage = self.read_voltage(bed)
        is_valid, warning_code, warning_message = self.warning_for_raw(bed, raw)
        percent = self.read_percent(bed, raw) if is_valid else None
        reading = MoistureReading(
            bed_id=bed.id,
            raw_value=raw,
            voltage=voltage,
            moisture_percent=percent,
            is_valid=is_valid,
            warning_code=warning_code,
            warning_message=warning_message,
        )
        db.add(reading)
        db.commit()
        db.refresh(reading)
        if self.mqtt:
            self.mqtt.publish_moisture(bed, reading)
        return reading
