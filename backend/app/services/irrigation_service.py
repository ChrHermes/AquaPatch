import asyncio
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.integrations.mqtt_service import MqttService
from app.models import Bed, IrrigationRun
from app.services.relay_service import RelayService


class IrrigationService:
    def __init__(self, settings: Settings, relay_service: RelayService, mqtt: MqttService | None = None) -> None:
        self.settings = settings
        self.relay_service = relay_service
        self.mqtt = mqtt
        self._state_lock = asyncio.Lock()
        self._running_bed_ids: set[int] = set()

    def is_any_irrigation_running(self) -> bool:
        return bool(self._running_bed_ids)

    async def water_bed(
        self,
        db: Session,
        bed_id: int,
        duration_seconds: int | None = None,
        trigger: str = "manual",
    ) -> IrrigationRun:
        bed = db.get(Bed, bed_id)
        if bed is None:
            raise ValueError("Beet wurde nicht gefunden")
        if not bed.enabled:
            raise ValueError("Beet ist deaktiviert")

        async with self._state_lock:
            if bed.id in self._running_bed_ids:
                raise RuntimeError("Dieses Beet wird bereits bewässert")
            self._running_bed_ids.add(bed.id)

        requested_duration = duration_seconds or bed.watering_seconds
        duration = min(requested_duration, self.settings.max_watering_seconds)
        started_at = datetime.utcnow()
        run = IrrigationRun(
            bed_id=bed.id,
            duration_seconds=duration,
            started_at=started_at,
            trigger=trigger,
            success=False,
            message="Bewässerung gestartet",
        )
        run_persisted = False

        try:
            db.add(run)
            db.commit()
            db.refresh(run)
            run_persisted = True
            self.relay_service.turn_on(bed)
            if self.mqtt:
                self.mqtt.publish_pump_state(bed, "ON")
            await asyncio.sleep(duration)
            run.success = True
            run.message = "Bewässerung abgeschlossen"
        except Exception as exc:
            run.success = False
            run.message = f"Bewässerung fehlgeschlagen: {exc}"
            raise
        finally:
            self.relay_service.turn_off(bed)
            async with self._state_lock:
                self._running_bed_ids.discard(bed.id)
            if self.mqtt:
                self.mqtt.publish_pump_state(bed, "OFF")
                self.mqtt.publish_irrigation_run(bed, run)
            if run_persisted:
                run.finished_at = datetime.utcnow()
                db.add(run)
                db.commit()
                db.refresh(run)
            else:
                db.rollback()
        return run

    def ensure_all_pumps_off(self) -> None:
        self.relay_service.turn_all_off()

    def is_bed_running(self, bed: Bed) -> bool:
        return bed.id in self._running_bed_ids
