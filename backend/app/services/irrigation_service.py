import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.integrations.mqtt_service import MqttService
from app.models import Bed, IrrigationRun, MoistureReading
from app.services.moisture_service import MoistureService
from app.services.relay_service import RelayService


@dataclass
class CurrentIrrigation:
    bed_id: int
    bed_name: str
    started_at: datetime
    planned_duration_seconds: int
    trigger: str
    cancel_event: asyncio.Event


class IrrigationService:
    def __init__(
        self,
        settings: Settings,
        relay_service: RelayService,
        moisture_service: MoistureService,
        mqtt: MqttService | None = None,
    ) -> None:
        self.settings = settings
        self.relay_service = relay_service
        self.moisture_service = moisture_service
        self.mqtt = mqtt
        self._lock = asyncio.Lock()
        self._current: CurrentIrrigation | None = None

    def is_any_irrigation_running(self) -> bool:
        return self._current is not None

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
        block_remaining = self.auto_watering_block_remaining_seconds(bed)
        if trigger != "manual" and block_remaining is not None:
            raise RuntimeError(f"Automatik ist nach Abbruch noch {block_remaining} Sekunden pausiert")
        moisture_before = self._try_read_moisture(db, bed)
        if trigger != "manual" and moisture_before is not None and not moisture_before.is_valid:
            raise RuntimeError("Automatische Bewässerung wegen ungültigem Sensorwert blockiert")

        requested_duration = duration_seconds or bed.watering_seconds
        duration = min(requested_duration, self.settings.max_watering_seconds)
        started_at = datetime.utcnow()
        cancel_event = asyncio.Event()
        run = IrrigationRun(
            bed_id=bed.id,
            duration_seconds=duration,
            started_at=started_at,
            trigger=trigger,
            success=False,
            status="failed",
            message="Bewässerung gestartet",
            moisture_before_percent=moisture_before.moisture_percent if moisture_before else None,
            moisture_before_raw=moisture_before.raw_value if moisture_before else None,
        )

        if self._lock.locked():
            raise RuntimeError("Es läuft bereits eine Bewässerung")

        async with self._lock:
            self._current = CurrentIrrigation(
                bed_id=bed.id,
                bed_name=bed.name,
                started_at=started_at,
                planned_duration_seconds=duration,
                trigger=trigger,
                cancel_event=cancel_event,
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            try:
                self.relay_service.turn_on(bed)
                if self.mqtt:
                    self.mqtt.publish_pump_state(bed, "ON")
                    self.mqtt.publish_irrigation_status(bed, self.get_current_status())
                for _ in range(duration):
                    try:
                        await asyncio.wait_for(cancel_event.wait(), timeout=1)
                        break
                    except asyncio.TimeoutError:
                        if self.mqtt:
                            self.mqtt.publish_irrigation_status(bed, self.get_current_status())

                if cancel_event.is_set():
                    run.success = False
                    run.status = "cancelled"
                    run.message = "Cancelled manually"
                    if trigger == "manual":
                        bed.last_cancelled_at = datetime.utcnow()
                else:
                    run.success = True
                    run.status = "completed"
                    run.message = "Bewässerung abgeschlossen"
            except Exception as exc:
                run.success = False
                run.status = "failed"
                run.message = f"Bewässerung fehlgeschlagen: {exc}"
                raise
            finally:
                self.relay_service.turn_off(bed)
                moisture_after = self._try_read_moisture(db, bed)
                if moisture_after is not None:
                    run.moisture_after_percent = moisture_after.moisture_percent
                    run.moisture_after_raw = moisture_after.raw_value
                self._current = None
                if self.mqtt:
                    self.mqtt.publish_pump_state(bed, "OFF")
                    self.mqtt.publish_irrigation_run(bed, run)
                    self.mqtt.publish_irrigation_status(bed, self.get_current_status())
                    if run.status == "cancelled":
                        self.mqtt.publish_cancelled(bed)
                    self.mqtt.publish_auto_watering_block(bed)
                run.finished_at = datetime.utcnow()
                db.add(bed)
                db.add(run)
                db.commit()
                db.refresh(run)
        return run

    def _try_read_moisture(self, db: Session, bed: Bed) -> MoistureReading | None:
        try:
            return self.moisture_service.read_and_store(db, bed)
        except Exception:
            return None

    def stop_bed(self, bed_id: int) -> bool:
        if self._current is None or self._current.bed_id != bed_id:
            return False
        self._current.cancel_event.set()
        return True

    def stop_current(self) -> bool:
        if self._current is None:
            return False
        self._current.cancel_event.set()
        return True

    def get_current_status(self) -> dict[str, object]:
        if self._current is None:
            return {
                "running": False,
                "bed_id": None,
                "bed_name": None,
                "started_at": None,
                "planned_duration_seconds": None,
                "elapsed_seconds": None,
                "remaining_seconds": None,
                "trigger": None,
                "can_cancel": False,
            }
        elapsed = min(
            self._current.planned_duration_seconds,
            max(0, int((datetime.utcnow() - self._current.started_at).total_seconds())),
        )
        remaining = max(0, self._current.planned_duration_seconds - elapsed)
        return {
            "running": True,
            "bed_id": self._current.bed_id,
            "bed_name": self._current.bed_name,
            "started_at": self._current.started_at,
            "planned_duration_seconds": self._current.planned_duration_seconds,
            "elapsed_seconds": elapsed,
            "remaining_seconds": remaining,
            "trigger": self._current.trigger,
            "can_cancel": True,
        }

    @staticmethod
    def auto_watering_blocked_until(bed: Bed) -> datetime | None:
        if bed.last_cancelled_at is None or bed.auto_watering_block_after_cancel_seconds <= 0:
            return None
        return bed.last_cancelled_at + timedelta(seconds=bed.auto_watering_block_after_cancel_seconds)

    @classmethod
    def auto_watering_block_remaining_seconds(cls, bed: Bed) -> int | None:
        blocked_until = cls.auto_watering_blocked_until(bed)
        if blocked_until is None:
            return None
        remaining = int((blocked_until - datetime.utcnow()).total_seconds())
        return remaining if remaining > 0 else None

    def ensure_all_pumps_off(self) -> None:
        self.stop_current()
        self.relay_service.turn_all_off()

    def is_bed_running(self, bed: Bed) -> bool:
        return self._current is not None and self._current.bed_id == bed.id
