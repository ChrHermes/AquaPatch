export interface Bed {
  id: number
  name: string
  relay_pin: number
  ads_channel: number
  moisture_dry_raw: number
  moisture_wet_raw: number
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
  watering_seconds: number
  auto_watering_block_after_cancel_seconds: number
  enabled: boolean
}

export interface MoistureReading {
  id: number
  bed_id: number
  raw_value: number
  voltage: number
  moisture_percent: number
  created_at: string
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
}

export interface SystemStatus {
  backend_reachable: boolean
  hardware_mock: boolean
  mqtt_enabled: boolean
  mqtt_connected: boolean
  bed_count: number
  irrigation_running: boolean
  max_watering_seconds: number
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
