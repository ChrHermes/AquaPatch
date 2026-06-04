from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./aquapatch.db", alias="DATABASE_URL")
    hardware_mock: bool = Field(default=True, alias="HARDWARE_MOCK")
    relay_active_low: bool = Field(default=True, alias="RELAY_ACTIVE_LOW")
    max_watering_seconds: int = Field(default=300, alias="MAX_WATERING_SECONDS")
    mqtt_enabled: bool = Field(default=False, alias="MQTT_ENABLED")
    mqtt_host: str = Field(default="localhost", alias="MQTT_HOST")
    mqtt_port: int = Field(default=1883, alias="MQTT_PORT")
    mqtt_username: str | None = Field(default=None, alias="MQTT_USERNAME")
    mqtt_password: str | None = Field(default=None, alias="MQTT_PASSWORD")
    mqtt_base_topic: str = Field(default="garden_irrigation", alias="MQTT_BASE_TOPIC")
    dht21_enabled: bool = Field(default=False, alias="DHT21_ENABLED")
    dht21_gpio_pin: int = Field(default=4, alias="DHT21_GPIO_PIN")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
