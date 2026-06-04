import type {
  Bed,
  BedPayload,
  ClimateReading,
  DailySummary,
  IrrigationCurrent,
  IrrigationInterval,
  IrrigationRun,
  MoistureReading,
  MoistureSeriesPoint,
  SystemStatus
} from '../types/api'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
    ...options
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail ?? `API-Fehler ${response.status}`)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

export const api = {
  beds: () => request<Bed[]>('/api/beds'),
  createBed: (payload: BedPayload) => request<Bed>('/api/beds', { method: 'POST', body: JSON.stringify(payload) }),
  updateBed: (id: number, payload: Partial<BedPayload>) =>
    request<Bed>(`/api/beds/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteBed: (id: number) => request<void>(`/api/beds/${id}`, { method: 'DELETE' }),
  readMoisture: (id: number) => request<MoistureReading>(`/api/beds/${id}/moisture`),
  moistureSeries: (id: number) => request<MoistureSeriesPoint[]>(`/api/beds/${id}/moisture/series?range=24h&bucket=5m`),
  irrigationIntervals: (id: number) => request<IrrigationInterval[]>(`/api/beds/${id}/irrigation/intervals?range=24h`),
  latestReadings: () => request<MoistureReading[]>('/api/readings/latest'),
  waterBed: (id: number, duration_seconds?: number) =>
    request<IrrigationRun>(`/api/beds/${id}/water`, {
      method: 'POST',
      body: JSON.stringify({ duration_seconds, trigger: 'manual' })
    }),
  stopWater: (id: number) => request<{ stopped: boolean; message: string }>(`/api/beds/${id}/water/stop`, { method: 'POST' }),
  currentIrrigation: () => request<IrrigationCurrent>('/api/irrigation/current'),
  climateLatest: () => request<ClimateReading>('/api/climate/latest'),
  climateRead: () => request<ClimateReading>('/api/climate/read', { method: 'POST' }),
  summaryToday: () => request<DailySummary>('/api/summary/today'),
  status: () => request<SystemStatus>('/api/system/status')
}
