from app.core.config import get_settings
from app.hardware.ads1115 import Ads1115Reader
from app.hardware.dht21 import Dht21Reader
from app.integrations.mqtt_service import MqttService
from app.services.climate_service import ClimateService
from app.services.irrigation_service import IrrigationService
from app.services.moisture_service import MoistureService
from app.services.relay_service import RelayService
from app.services.system_service import SystemService


settings = get_settings()
mqtt_service = MqttService(settings)
relay_service = RelayService(settings)
moisture_service = MoistureService(Ads1115Reader(settings.hardware_mock), mqtt_service)
climate_service = ClimateService(Dht21Reader(settings.hardware_mock, settings.dht21_enabled, settings.dht21_gpio_pin), mqtt_service)
irrigation_service = IrrigationService(settings, relay_service, moisture_service, mqtt_service)
system_service = SystemService(settings)
mqtt_service.stop_command_handler = irrigation_service.stop_bed
