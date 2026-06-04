export interface Bed {
  id: number
  name: string
  relay_pin: number
  ads_channel: number
  moisture_dry_raw: number
  moisture_wet_raw: number
  sensor_disconnected_raw_threshold: number
  watering_seconds: number
  auto_watering_block_after_cancel_seconds: number
  enabled: boolean
  created_at: string
  updated_at: string
  last_cancelled_at: string | null
  auto_watering_blocked_until: string | null
  auto_watering_block_remaining_seconds: number | null
  pump_running: boolean
}

export interface BedPayload {
  name: string
  relay_pin: number
  ads_channel: number
  moisture_dry_raw: number
  moisture_wet_raw: number
  sensor_disconnected_raw_threshold: number
  watering_seconds: number
  auto_watering_block_after_cancel_seconds: number
  enabled: boolean
}

export interface MoistureReading {
  id: number
  bed_id: number
  raw_value: number
  voltage: number
  moisture_percent: number | null
  is_valid: boolean
  warning_code: string | null
  warning_message: string | null
  created_at: string
}

export interface MoistureSeriesPoint {
  timestamp: string
  avg_moisture_percent: number | null
  avg_raw_value: number | null
}

export interface IrrigationRun {
  id: number
  bed_id: number
  duration_seconds: number
  started_at: string
  finished_at: string | null
  trigger: string
  success: boolean
  status: 'completed' | 'cancelled' | 'failed'
  message: string
  moisture_before_percent: number | null
  moisture_after_percent: number | null
  moisture_before_raw: number | null
  moisture_after_raw: number | null
}

export interface IrrigationInterval {
  started_at: string
  finished_at: string | null
  duration_seconds: number
  status: 'completed' | 'cancelled' | 'failed'
  trigger: string
}

export interface SystemStatus {
  backend_reachable: boolean
  hardware_mock: boolean
  mqtt_enabled: boolean
  mqtt_connected: boolean
  bed_count: number
  irrigation_running: boolean
  max_watering_seconds: number
  dht21_enabled: boolean
  dht21_gpio_pin: number
}

export interface ClimateReading {
  id: number
  temperature_c: number | null
  humidity_percent: number | null
  source: string
  is_valid: boolean
  error_message: string | null
  created_at: string
}

export interface BedDailySummary {
  bed_id: number
  bed_name: string
  irrigation_count: number
  total_duration_seconds: number
  last_irrigation_at: string | null
  moisture_min: number | null
  moisture_max: number | null
  moisture_avg: number | null
  sensor_warning_count: number
}

export interface DailySummary {
  date: string
  irrigation_count: number
  total_duration_seconds: number
  beds: BedDailySummary[]
  climate_avg_temperature_c: number | null
  climate_avg_humidity_percent: number | null
  climate_min_temperature_c: number | null
  climate_max_temperature_c: number | null
  climate_min_humidity_percent: number | null
  climate_max_humidity_percent: number | null
}

export interface IrrigationCurrent {
  running: boolean
  bed_id: number | null
  bed_name: string | null
  started_at: string | null
  planned_duration_seconds: number | null
  elapsed_seconds: number | null
  remaining_seconds: number | null
  trigger: string | null
  can_cancel: boolean
}
