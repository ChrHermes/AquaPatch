export interface Bed {
  id: number
  name: string
  relay_pin: number
  ads_channel: number
  moisture_dry_raw: number
  moisture_wet_raw: number
  watering_seconds: number
  enabled: boolean
  created_at: string
  updated_at: string
  pump_running: boolean
}

export type BedPayload = Omit<Bed, 'id' | 'created_at' | 'updated_at' | 'pump_running'>

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
