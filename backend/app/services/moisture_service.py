from sqlalchemy.orm import Session

from app.hardware.ads1115 import Ads1115Reader
from app.integrations.mqtt_service import MqttService
from app.models import Bed, MoistureReading


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

    def read_and_store(self, db: Session, bed: Bed) -> MoistureReading:
        raw = self.read_raw(bed)
        voltage = self.read_voltage(bed)
        percent = self.read_percent(bed, raw)
        reading = MoistureReading(bed_id=bed.id, raw_value=raw, voltage=voltage, moisture_percent=percent)
        db.add(reading)
        db.commit()
        db.refresh(reading)
        if self.mqtt:
            self.mqtt.publish_moisture(bed, reading)
        return reading
