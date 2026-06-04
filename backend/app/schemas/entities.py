from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BedBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    relay_pin: int = Field(ge=0, le=27)
    ads_channel: int = Field(ge=0, le=3)
    moisture_dry_raw: int = Field(default=17750, ge=0)
    moisture_wet_raw: int = Field(default=7700, ge=0)
    sensor_disconnected_raw_threshold: int = Field(default=5000, ge=0)
    watering_seconds: int = Field(default=120, gt=0)
    auto_watering_block_after_cancel_seconds: int = Field(default=3600, ge=0)
    enabled: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name darf nicht leer sein")
        return value


class BedCreate(BedBase):
    pass


class BedUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    relay_pin: int | None = Field(default=None, ge=0, le=27)
    ads_channel: int | None = Field(default=None, ge=0, le=3)
    moisture_dry_raw: int | None = Field(default=None, ge=0)
    moisture_wet_raw: int | None = Field(default=None, ge=0)
    sensor_disconnected_raw_threshold: int | None = Field(default=None, ge=0)
    watering_seconds: int | None = Field(default=None, gt=0)
    auto_watering_block_after_cancel_seconds: int | None = Field(default=None, ge=0)
    enabled: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Name darf nicht leer sein")
        return value


class BedRead(BedBase):
    id: int
    created_at: datetime
    updated_at: datetime
    last_cancelled_at: datetime | None = None
    auto_watering_blocked_until: datetime | None = None
    auto_watering_block_remaining_seconds: int | None = None
    pump_running: bool = False

    model_config = ConfigDict(from_attributes=True)


class MoistureReadingRead(BaseModel):
    id: int
    bed_id: int
    raw_value: int
    voltage: float
    moisture_percent: float | None
    is_valid: bool = True
    warning_code: str | None = None
    warning_message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WaterRequest(BaseModel):
    duration_seconds: int | None = Field(default=None, gt=0)
    trigger: str = Field(default="manual", min_length=1, max_length=40)


class IrrigationRunRead(BaseModel):
    id: int
    bed_id: int
    duration_seconds: int
    started_at: datetime
    finished_at: datetime | None
    trigger: str
    success: bool
    status: str
    message: str
    moisture_before_percent: float | None = None
    moisture_after_percent: float | None = None
    moisture_before_raw: int | None = None
    moisture_after_raw: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ClimateReadingRead(BaseModel):
    id: int
    temperature_c: float | None
    humidity_percent: float | None
    source: str
    is_valid: bool
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SystemEventRead(BaseModel):
    id: int
    level: str
    component: str
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SystemStatus(BaseModel):
    backend_reachable: bool
    hardware_mock: bool
    mqtt_enabled: bool
    mqtt_connected: bool
    bed_count: int
    irrigation_running: bool
    max_watering_seconds: int
    dht21_enabled: bool
    dht21_gpio_pin: int


class IrrigationCurrent(BaseModel):
    running: bool
    bed_id: int | None = None
    bed_name: str | None = None
    started_at: datetime | None = None
    planned_duration_seconds: int | None = None
    elapsed_seconds: int | None = None
    remaining_seconds: int | None = None
    trigger: str | None = None
    can_cancel: bool = False


class MoistureSeriesPoint(BaseModel):
    timestamp: datetime
    avg_moisture_percent: float | None
    avg_raw_value: float | None


class IrrigationInterval(BaseModel):
    started_at: datetime
    finished_at: datetime | None
    duration_seconds: int
    status: str
    trigger: str


class BedDailySummary(BaseModel):
    bed_id: int
    bed_name: str
    irrigation_count: int
    total_duration_seconds: int
    last_irrigation_at: datetime | None
    moisture_min: float | None
    moisture_max: float | None
    moisture_avg: float | None
    sensor_warning_count: int


class DailySummary(BaseModel):
    date: str
    irrigation_count: int
    total_duration_seconds: int
    beds: list[BedDailySummary]
    climate_avg_temperature_c: float | None = None
    climate_avg_humidity_percent: float | None = None
    climate_min_temperature_c: float | None = None
    climate_max_temperature_c: float | None = None
    climate_min_humidity_percent: float | None = None
    climate_max_humidity_percent: float | None = None
