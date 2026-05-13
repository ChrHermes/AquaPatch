import logging
import random


logger = logging.getLogger(__name__)


class Ads1115Reader:
    def __init__(self, mock: bool) -> None:
        self.mock = mock
        self._ads = None
        self._channels: dict[int, object] = {}

    def setup(self) -> None:
        if self.mock:
            logger.info("ADS1115 mock setup")
            return
        try:
            import board  # type: ignore[import-not-found]
            import busio  # type: ignore[import-not-found]
            import adafruit_ads1x15.ads1115 as ADS  # type: ignore[import-not-found]
            from adafruit_ads1x15.analog_in import AnalogIn  # type: ignore[import-not-found]

            i2c = busio.I2C(board.SCL, board.SDA)
            self._ads = ADS.ADS1115(i2c)
            pins = [ADS.P0, ADS.P1, ADS.P2, ADS.P3]
            self._channels = {index: AnalogIn(self._ads, pin) for index, pin in enumerate(pins)}
        except Exception:
            logger.exception("ADS1115 setup failed")
            raise

    def read_raw(self, channel: int) -> int:
        self._validate_channel(channel)
        if self.mock:
            return random.randint(10500, 27500)
        analog_channel = self._channels.get(channel)
        if analog_channel is None:
            raise RuntimeError("ADS1115 is not initialized")
        return int(getattr(analog_channel, "value"))

    def read_voltage(self, channel: int) -> float:
        self._validate_channel(channel)
        if self.mock:
            return round(random.uniform(0.8, 2.6), 3)
        analog_channel = self._channels.get(channel)
        if analog_channel is None:
            raise RuntimeError("ADS1115 is not initialized")
        return float(getattr(analog_channel, "voltage"))

    @staticmethod
    def _validate_channel(channel: int) -> None:
        if channel < 0 or channel > 3:
            raise ValueError("ADS1115 channel must be between 0 and 3")
