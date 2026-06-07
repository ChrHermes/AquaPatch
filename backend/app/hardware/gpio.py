import logging


logger = logging.getLogger(__name__)


class GpioController:
    def __init__(self, mock: bool, active_low: bool) -> None:
        self.mock = mock
        self.active_low = active_low
        self._states: dict[int, bool] = {}
        self._gpio = None

    def setup(self, pins: list[int]) -> None:
        if self.mock:
            logger.info("GPIO mock setup for pins %s", pins)
            for pin in pins:
                self._states[pin] = False
            return

        try:
            import RPi.GPIO as GPIO  # type: ignore[import-not-found]

            self._gpio = GPIO
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            for pin in pins:
                GPIO.setup(pin, GPIO.OUT)
                self.write(pin, False)
        except Exception:
            logger.exception("GPIO setup failed")
            raise

    def write(self, pin: int, enabled: bool) -> None:
        self._states[pin] = enabled
        if self.mock:
            logger.info("GPIO mock pin %s -> %s", pin, "on" if enabled else "off")
            return
        if self._gpio is None:
            raise RuntimeError("GPIO is not initialized")
        level = self._gpio.LOW if enabled and self.active_low else self._gpio.HIGH if enabled else self._gpio.HIGH if self.active_low else self._gpio.LOW
        self._gpio.output(pin, level)

    def cleanup(self) -> None:
        for pin in list(self._states):
            try:
                self.write(pin, False)
            except Exception:
                logger.exception("Failed to turn off GPIO pin %s during cleanup", pin)
        if not self.mock and self._gpio is not None:
            self._gpio.cleanup()

    def get_state(self, pin: int) -> bool:
        return self._states.get(pin, False)
