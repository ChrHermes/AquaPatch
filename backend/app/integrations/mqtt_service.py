import json
import logging
from typing import Any, Callable

from app.core.config import Settings


logger = logging.getLogger(__name__)


class MqttService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client: Any = None
        self.connected = False
        self.water_command_handler: Callable[[int, int | None], None] | None = None

    def start(self) -> None:
        if not self.settings.mqtt_enabled:
            return
        try:
            import paho.mqtt.client as mqtt  # type: ignore[import-not-found]

            self.client = mqtt.Client()
            if self.settings.mqtt_username:
                self.client.username_pw_set(self.settings.mqtt_username, self.settings.mqtt_password)
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.connect_async(self.settings.mqtt_host, self.settings.mqtt_port)
            self.client.loop_start()
        except Exception:
            logger.exception("MQTT startup failed")
            self.connected = False

    def stop(self) -> None:
        if self.client is None:
            return
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            logger.exception("MQTT shutdown failed")
        finally:
            self.connected = False

    def publish(self, topic: str, payload: object, retain: bool = False) -> None:
        if not self.settings.mqtt_enabled or self.client is None:
            return
        try:
            value = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
            self.client.publish(topic, value, retain=retain)
        except Exception:
            logger.exception("MQTT publish failed for topic %s", topic)

    def publish_bed_state(self, bed: Any) -> None:
        base = self._bed_topic(bed.id)
        self.publish(f"{base}/name", bed.name, retain=True)
        self.publish(f"{base}/status", "enabled" if bed.enabled else "disabled", retain=True)

    def publish_moisture(self, bed: Any, reading: Any) -> None:
        base = self._bed_topic(bed.id)
        self.publish(f"{base}/moisture_percent", reading.moisture_percent)
        self.publish(f"{base}/moisture_raw", reading.raw_value)
        self.publish(f"{base}/moisture_voltage", reading.voltage)

    def publish_pump_state(self, bed: Any, state: str) -> None:
        self.publish(f"{self._bed_topic(bed.id)}/pump/state", state)

    def publish_irrigation_run(self, bed: Any, run: Any) -> None:
        self.publish(
            f"{self._bed_topic(bed.id)}/irrigation/last_run",
            {"duration_seconds": run.duration_seconds, "success": run.success, "message": run.message},
        )

    def publish_system_status(self) -> None:
        base = self.settings.mqtt_base_topic
        self.publish(f"{base}/system/status", "online", retain=True)
        self.publish(f"{base}/system/hardware_mock", self.settings.hardware_mock, retain=True)
        self.publish(f"{base}/system/mqtt/status", "connected" if self.connected else "disconnected", retain=True)

    def _on_connect(self, client: Any, _userdata: Any, _flags: Any, rc: int) -> None:
        self.connected = rc == 0
        if self.connected:
            topic = f"{self.settings.mqtt_base_topic}/bed/+/water/set"
            client.subscribe(topic)
            self.publish_system_status()
        else:
            logger.warning("MQTT connection returned code %s", rc)

    def _on_message(self, _client: Any, _userdata: Any, message: Any) -> None:
        try:
            parts = message.topic.split("/")
            bed_id = int(parts[2])
            payload = message.payload.decode("utf-8").strip()
            duration = int(payload) if payload.isdigit() else json.loads(payload).get("duration_seconds")
            if self.water_command_handler:
                self.water_command_handler(bed_id, duration)
        except Exception:
            logger.exception("Invalid MQTT water command")

    def _bed_topic(self, bed_id: int) -> str:
        return f"{self.settings.mqtt_base_topic}/bed/{bed_id}"
