import logging
import random


logger = logging.getLogger(__name__)


class Dht21Reader:
    def __init__(self, mock: bool, enabled: bool, gpio_pin: int) -> None:
        self.mock = mock
        self.enabled = enabled
        self.gpio_pin = gpio_pin
        self._device: object | None = None

    def setup(self) -> None:
        if not self.enabled:
            logger.info("DHT21 disabled")
            return
        if self.mock:
            logger.info("DHT21 mock setup on GPIO %s", self.gpio_pin)
            return
        try:
            import adafruit_dht  # type: ignore[import-not-found]
            import board  # type: ignore[import-not-found]

            pin_name = f"D{self.gpio_pin}"
            pin = getattr(board, pin_name)
            self._device = adafruit_dht.DHT21(pin)
        except Exception:
            logger.exception("DHT21 setup failed")
            raise

    def read(self) -> tuple[float | None, float | None, str | None]:
        if not self.enabled:
            return None, None, "DHT21 ist deaktiviert"
        if self.mock:
            return round(random.uniform(21.0, 30.0), 1), round(random.uniform(45.0, 85.0), 1), None
        if self._device is None:
            return None, None, "DHT21 ist nicht initialisiert"
        try:
            temperature = getattr(self._device, "temperature")
            humidity = getattr(self._device, "humidity")
            if temperature is None or humidity is None:
                return None, None, "DHT21 hat keinen Messwert geliefert"
            return round(float(temperature), 1), round(float(humidity), 1), None
        except Exception as exc:
            logger.exception("DHT21 read failed")
            return None, None, str(exc)
