from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.hardware.gpio import GpioController
from app.models import Bed


class RelayService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.controller = GpioController(mock=settings.hardware_mock, active_low=settings.relay_active_low)

    def setup(self, db: Session) -> None:
        pins = [bed.relay_pin for bed in db.scalars(select(Bed)).all()]
        self.controller.setup(pins)
        self.turn_all_off()

    def turn_on(self, bed: Bed) -> None:
        self.controller.write(bed.relay_pin, True)

    def turn_off(self, bed: Bed) -> None:
        self.controller.write(bed.relay_pin, False)

    def turn_all_off(self) -> None:
        for pin in list(self.controller._states):
            self.controller.write(pin, False)

    def get_state(self, bed: Bed) -> bool:
        return self.controller.get_state(bed.relay_pin)

    def cleanup(self) -> None:
        self.controller.cleanup()
