<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { api } from './api/client'
import type { Bed, BedPayload, IrrigationCurrent, MoistureReading, SystemStatus } from './types/api'

const beds = ref<Bed[]>([])
const readings = ref<Record<number, MoistureReading>>({})
const status = ref<SystemStatus | null>(null)
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const statusMessage = ref('')
const wateringIds = ref<Set<number>>(new Set())
const editingId = ref<number | null>(null)
const activeModal = ref<'bed' | 'app' | null>(null)
const confirmingDelete = ref(false)
const currentIrrigation = ref<IrrigationCurrent | null>(null)
let currentTimer: number | undefined

const emptyForm = (): BedPayload => ({
  name: '',
  relay_pin: 0,
  ads_channel: 0,
  moisture_dry_raw: 26000,
  moisture_wet_raw: 12000,
  watering_seconds: 120,
  auto_watering_block_after_cancel_seconds: 3600,
  enabled: true
})

const form = reactive<BedPayload>(emptyForm())

const isEditing = computed(() => editingId.value !== null)
const modalTitle = computed(() => (isEditing.value ? 'Beet bearbeiten' : 'Neues Beet anlegen'))
const autoBlockMinutes = computed({
  get: () => Math.round(form.auto_watering_block_after_cancel_seconds / 60),
  set: (value: number) => {
    form.auto_watering_block_after_cancel_seconds = Math.max(0, Math.round(value * 60))
  }
})
const lastUpdated = computed(() => {
  const latest = Object.values(readings.value)
    .map((reading) => new Date(reading.created_at).getTime())
    .filter((time) => Number.isFinite(time))
    .sort((a, b) => b - a)[0]
  return latest ? new Date(latest).toLocaleString() : new Date().toLocaleString()
})

function assignForm(values: BedPayload) {
  Object.assign(form, values)
}

function resetForm() {
  editingId.value = null
  confirmingDelete.value = false
  assignForm(emptyForm())
}

function closeModal() {
  activeModal.value = null
  resetForm()
}

function moistureStatus(percent?: number) {
  if (percent === undefined) return { label: 'keine Messung', color: 'bg-slate-100 text-slate-700' }
  if (percent < 35) return { label: 'trocken', color: 'bg-amber-100 text-amber-800' }
  if (percent > 75) return { label: 'nass', color: 'bg-blue-100 text-blue-800' }
  return { label: 'okay', color: 'bg-emerald-100 text-emerald-800' }
}

function moistureTone(percent?: number) {
  if (percent === undefined) return { bar: 'bg-slate-400', icon: 'bg-slate-100 text-slate-500', accent: 'text-slate-700' }
  if (percent < 35) return { bar: 'bg-emerald-600', icon: 'bg-emerald-50 text-emerald-700', accent: 'text-emerald-700' }
  if (percent > 75) return { bar: 'bg-blue-600', icon: 'bg-blue-50 text-blue-700', accent: 'text-blue-700' }
  return { bar: 'bg-emerald-600', icon: 'bg-emerald-50 text-emerald-700', accent: 'text-emerald-700' }
}

function isBedWatering(bed: Bed) {
  return currentIrrigation.value?.running && currentIrrigation.value.bed_id === bed.id
}

function formatDuration(totalSeconds?: number | null) {
  const seconds = Math.max(0, totalSeconds ?? 0)
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`
}

function progressPercent(bed: Bed) {
  if (!isBedWatering(bed)) return readings.value[bed.id]?.moisture_percent ?? 0
  const planned = currentIrrigation.value?.planned_duration_seconds ?? bed.watering_seconds
  const remaining = currentIrrigation.value?.remaining_seconds ?? planned
  if (planned <= 0) return 0
  return Math.max(0, Math.min(100, ((planned - remaining) / planned) * 100))
}

function blockMessage(bed: Bed) {
  const remaining = bed.auto_watering_block_remaining_seconds
  if (!remaining || remaining <= 0) return ''
  const minutes = Math.ceil(remaining / 60)
  return `Automatik pausiert nach Abbruch · noch ${minutes} min`
}

async function refreshCurrent() {
  try {
    currentIrrigation.value = await api.currentIrrigation()
  } catch {
    currentIrrigation.value = null
  }
}

async function refresh() {
  error.value = ''
  try {
    const [bedData, latest, systemStatus] = await Promise.all([api.beds(), api.latestReadings(), api.status()])
    beds.value = bedData
    readings.value = Object.fromEntries(latest.map((reading) => [reading.bed_id, reading]))
    status.value = systemStatus
    await refreshCurrent()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unbekannter Fehler'
  } finally {
    loading.value = false
  }
}

async function readMoisture(bed: Bed) {
  error.value = ''
  try {
    readings.value[bed.id] = await api.readMoisture(bed.id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Messung fehlgeschlagen'
  }
}

async function water(bed: Bed) {
  error.value = ''
  statusMessage.value = ''
  wateringIds.value = new Set(wateringIds.value).add(bed.id)
  try {
    void refreshCurrent()
    const run = await api.waterBed(bed.id, bed.watering_seconds)
    statusMessage.value = run.status === 'cancelled' ? 'Bewässerung abgebrochen' : run.message || 'Bewässerung abgeschlossen'
    await refresh()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Bewässerung fehlgeschlagen'
  } finally {
    const next = new Set(wateringIds.value)
    next.delete(bed.id)
    wateringIds.value = next
    await refreshCurrent()
  }
}

async function stopWater(bed: Bed) {
  error.value = ''
  statusMessage.value = ''
  try {
    const response = await api.stopWater(bed.id)
    statusMessage.value = response.message || 'Bewässerung abgebrochen'
    await refreshCurrent()
    await refresh()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Abbruch fehlgeschlagen'
  }
}

function editBed(bed: Bed) {
  editingId.value = bed.id
  assignForm({
    name: bed.name,
    relay_pin: bed.relay_pin,
    ads_channel: bed.ads_channel,
    moisture_dry_raw: bed.moisture_dry_raw,
    moisture_wet_raw: bed.moisture_wet_raw,
    watering_seconds: bed.watering_seconds,
    auto_watering_block_after_cancel_seconds: bed.auto_watering_block_after_cancel_seconds,
    enabled: bed.enabled
  })
  activeModal.value = 'bed'
}

function newBed() {
  resetForm()
  const usedPins = new Set(beds.value.map((bed) => bed.relay_pin))
  const usedChannels = new Set(beds.value.map((bed) => bed.ads_channel))
  const nextPin = [17, 27, 22, 5, 6, 13, 19, 26].find((pin) => !usedPins.has(pin)) ?? 0
  const nextChannel = [0, 1, 2, 3].find((channel) => !usedChannels.has(channel)) ?? 0
  form.relay_pin = nextPin
  form.ads_channel = nextChannel
  activeModal.value = 'bed'
}

async function saveBed() {
  saving.value = true
  error.value = ''
  try {
    if (editingId.value) {
      await api.updateBed(editingId.value, form)
    } else {
      await api.createBed(form)
    }
    closeModal()
    await refresh()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Speichern fehlgeschlagen'
  } finally {
    saving.value = false
  }
}

async function deleteCurrentBed() {
  if (!editingId.value) return
  saving.value = true
  error.value = ''
  try {
    await api.deleteBed(editingId.value)
    closeModal()
    await refresh()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Löschen fehlgeschlagen'
  } finally {
    saving.value = false
  }
}

onMounted(refresh)
onMounted(() => {
  currentTimer = window.setInterval(() => {
    void refreshCurrent()
    if (currentIrrigation.value?.running) {
      void refresh()
    }
  }, 1000)
})

onUnmounted(() => {
  if (currentTimer) window.clearInterval(currentTimer)
})
</script>

<template>
  <main class="min-h-screen bg-[#fbfcfd] text-slate-950">
    <div class="mx-auto max-w-[1576px] px-8 py-8">
      <header class="mb-7 flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <div class="flex items-center gap-3">
            <svg class="h-8 w-8 text-emerald-700" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M17.75 3.03c-5.36.51-9.13 3.06-10.9 7.34C5.2 10.65 4 12.06 4 13.75 4 15.54 5.46 17 7.25 17c1.69 0 3.1-1.2 3.38-2.85 4.28-1.77 6.83-5.54 7.34-10.9l.22-.22h-.44ZM7.25 15A1.25 1.25 0 1 1 8.5 13.75 1.25 1.25 0 0 1 7.25 15Zm3.19-2.92-1.52-1.52c1.2-2.31 3.26-3.93 6.16-4.84-.91 2.9-2.53 4.96-4.64 6.36Z" />
            </svg>
            <span class="text-xl font-extrabold tracking-tight text-emerald-700">AquaPatch</span>
          </div>
          <h1 class="mt-7 text-4xl font-black tracking-tight text-slate-950 sm:text-5xl">Gartenbewässerung</h1>

          <div class="mt-8 flex flex-wrap gap-5">
            <span class="inline-flex items-center gap-3 rounded-full bg-emerald-50 px-5 py-2 text-base font-bold text-emerald-700">
              <span class="h-3 w-3 rounded-full bg-emerald-600" />
              {{ status?.bed_count ?? beds.length }} Beete
            </span>
            <span class="inline-flex items-center gap-3 rounded-full bg-blue-50 px-5 py-2 text-base font-bold text-blue-700">
              <span class="h-3 w-3 rounded-full border-4 border-blue-600 bg-white" />
              Mock {{ status?.hardware_mock ? 'aktiv' : 'aus' }}
            </span>
            <span class="inline-flex items-center gap-3 rounded-full bg-slate-100 px-5 py-2 text-base font-bold text-slate-600">
              <span class="h-3 w-3 rounded-full bg-slate-400" />
              MQTT {{ status?.mqtt_enabled ? (status.mqtt_connected ? 'verbunden' : 'aktiv') : 'aus' }}
            </span>
          </div>
        </div>

        <div class="flex flex-wrap gap-5">
          <button class="inline-flex h-14 items-center gap-4 rounded-lg border border-slate-200 bg-white px-7 text-base font-bold text-slate-900 shadow-sm transition hover:border-emerald-300 hover:text-emerald-700" @click="newBed">
            <svg class="h-7 w-7" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2Z" />
            </svg>
            Beet hinzufügen
          </button>
          <button class="inline-flex h-14 items-center gap-4 rounded-lg border border-slate-200 bg-white px-7 text-base font-bold text-slate-900 shadow-sm transition hover:border-emerald-300 hover:text-emerald-700" @click="activeModal = 'app'">
            <svg class="h-6 w-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="m19.43 12.98.04-.32.03-.66-.03-.66-.04-.32 2.11-1.65-2-3.46-2.49 1a7.3 7.3 0 0 0-1.14-.66L15.5 3h-4l-.41 3.25c-.4.17-.78.39-1.14.66l-2.49-1-2 3.46 2.11 1.65-.04.32-.03.66.03.66.04.32-2.11 1.65 2 3.46 2.49-1c.36.27.74.49 1.14.66l.41 3.25h4l.41-3.25c.4-.17.78-.39 1.14-.66l2.49 1 2-3.46-2.11-1.65ZM13.5 19h-2l-.31-2.48-.58-.24a5.42 5.42 0 0 1-1.44-.83l-.5-.38-1.9.76-1-1.74 1.62-1.27-.08-.62A6.25 6.25 0 0 1 7.25 12c0-.27.02-.54.06-.8l.08-.62-1.62-1.27 1-1.74 1.9.76.5-.38c.43-.33.91-.61 1.44-.83l.58-.24L11.5 5h2l.31 2.48.58.24c.53.22 1.01.5 1.44.83l.5.38 1.9-.76 1 1.74-1.62 1.27.08.62c.04.26.06.53.06.8s-.02.54-.06.8l-.08.62 1.62 1.27-1 1.74-1.9-.76-.5.38c-.43.33-.91.61-1.44.83l-.58.24L13.5 19Zm-1-10a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z" />
            </svg>
            Einstellungen
          </button>
          <button class="inline-flex h-14 items-center gap-4 rounded-lg border border-slate-200 bg-white px-7 text-base font-bold text-slate-900 shadow-sm transition hover:border-emerald-300 hover:text-emerald-700" @click="refresh">
            <svg class="h-6 w-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M17.65 6.35A7.95 7.95 0 0 0 12 4a8 8 0 1 0 7.45 5h-2.1A6 6 0 1 1 12 6c1.66 0 3.14.69 4.22 1.78L13 11h8V3l-3.35 3.35Z" />
            </svg>
            Aktualisieren
          </button>
        </div>
      </header>

      <div v-if="error" class="mb-5 rounded-lg border border-red-200 bg-red-50 px-5 py-4 text-sm font-semibold text-red-800">{{ error }}</div>
      <div v-if="statusMessage" class="mb-5 rounded-lg border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm font-semibold text-emerald-800">{{ statusMessage }}</div>

      <p v-if="loading" class="py-16 text-center text-slate-500">Lade Beete...</p>
      <section v-else class="grid gap-10 xl:grid-cols-2">
        <article
          v-for="bed in beds"
          :key="bed.id"
          class="rounded-2xl border border-slate-200 bg-white p-8 shadow-[0_12px_40px_rgba(15,23,42,0.06)] transition"
          :class="isBedWatering(bed) ? 'border-emerald-200 bg-emerald-50/30 shadow-[0_18px_48px_rgba(22,163,74,0.12)]' : ''"
        >
          <div class="mb-7 flex items-start justify-between gap-5">
            <div class="flex min-w-0 items-start gap-6">
              <span class="grid h-14 w-14 shrink-0 place-items-center rounded-full" :class="moistureTone(readings[bed.id]?.moisture_percent).icon">
                <svg class="h-8 w-8" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M17.75 3.03c-5.36.51-9.13 3.06-10.9 7.34C5.2 10.65 4 12.06 4 13.75 4 15.54 5.46 17 7.25 17c1.69 0 3.1-1.2 3.38-2.85 4.28-1.77 6.83-5.54 7.34-10.9l.22-.22h-.44ZM7.25 15A1.25 1.25 0 1 1 8.5 13.75 1.25 1.25 0 0 1 7.25 15Zm3.19-2.92-1.52-1.52c1.2-2.31 3.26-3.93 6.16-4.84-.91 2.9-2.53 4.96-4.64 6.36Z" />
                </svg>
              </span>
              <div>
                <h2 class="text-2xl font-extrabold tracking-tight text-slate-950">{{ bed.name }}</h2>
                <p class="mt-1 text-lg font-medium text-slate-500">GPIO {{ bed.relay_pin }} · ADS A{{ bed.ads_channel }}</p>
              </div>
            </div>
            <div class="flex items-center gap-5">
              <span class="rounded-full px-5 py-2 text-sm font-extrabold" :class="moistureStatus(readings[bed.id]?.moisture_percent).color">
                {{ moistureStatus(readings[bed.id]?.moisture_percent).label }}
              </span>
              <button class="grid h-10 w-10 place-items-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:border-emerald-200 hover:text-emerald-700" aria-label="Beet-Einstellungen" title="Beet-Einstellungen" @click="editBed(bed)">
                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M3 17.46V21h3.54L17.06 10.48l-3.54-3.54L3 17.46ZM19.71 7.83a1 1 0 0 0 0-1.41l-2.13-2.13a1 1 0 0 0-1.41 0L14.5 5.96l3.54 3.54 1.67-1.67Z" />
                </svg>
              </button>
            </div>
          </div>

          <section class="mb-7">
            <p class="text-5xl font-black tracking-tight text-slate-950">
              {{ readings[bed.id]?.moisture_percent ?? '–' }}<span class="text-2xl font-extrabold">%</span>
            </p>
            <p class="mt-4 text-lg font-medium text-slate-500">Bodenfeuchte</p>
            <div class="mt-3 h-2 rounded-full bg-slate-100">
              <div class="h-2 rounded-full transition-all" :class="moistureTone(readings[bed.id]?.moisture_percent).bar" :style="{ width: `${Math.min(100, Math.max(0, readings[bed.id]?.moisture_percent ?? 0))}%` }" />
            </div>
            <div class="mt-3 flex justify-between text-base font-medium text-slate-500">
              <span>0%</span>
              <span>50%</span>
              <span>100%</span>
            </div>
            <p class="mt-7 text-base font-medium text-slate-500">
              Rohwert {{ readings[bed.id]?.raw_value ?? '–' }} · {{ readings[bed.id]?.voltage?.toFixed(2) ?? '–' }} V · Letzte Messung
              {{ readings[bed.id]?.created_at ? new Date(readings[bed.id].created_at).toLocaleString() : 'ausstehend' }}
            </p>
            <p v-if="blockMessage(bed)" class="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-sm font-bold text-amber-800">{{ blockMessage(bed) }}</p>
          </section>

          <dl class="mb-7 grid gap-4 border-t border-slate-200 pt-7 sm:grid-cols-3">
            <div class="flex items-center gap-4">
              <dt class="flex items-center gap-3 text-base font-medium text-slate-500">
                <svg class="h-7 w-7" :class="isBedWatering(bed) ? 'text-emerald-700' : 'text-slate-500'" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M12 2.69 17.66 8.35a8 8 0 1 1-11.32 0L12 2.69ZM12 20a6 6 0 0 0 4.24-10.24L12 5.52 7.76 9.76A6 6 0 0 0 12 20Z" />
                </svg>
                Pumpe
              </dt>
              <dd class="mt-1 text-base font-extrabold" :class="isBedWatering(bed) ? 'text-emerald-700' : 'text-slate-950'">{{ isBedWatering(bed) || wateringIds.has(bed.id) ? 'läuft' : 'aus' }}</dd>
            </div>
            <div class="flex items-center gap-4">
              <dt class="flex items-center gap-3 text-base font-medium text-slate-500">
                <svg class="h-7 w-7 text-slate-500" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm0 2C6.48 22 2 17.52 2 12S6.48 2 12 2s10 4.48 10 10-4.48 10-10 10Zm.5-15H11v6l5.25 3.15.75-1.23-4.5-2.67V7Z" />
                </svg>
                Dauer
              </dt>
              <dd class="mt-1 text-base font-extrabold text-slate-950">{{ bed.watering_seconds }} s</dd>
            </div>
            <div class="flex items-center gap-4">
              <dt class="flex items-center gap-3 text-base font-medium text-slate-500">
                <svg class="h-7 w-7 text-slate-500" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M3 13h4l3 7 4-16 3 9h4v2h-5.44l-1.37-4.11-3.96 15.85L5.68 15H3v-2Z" />
                </svg>
                Status
              </dt>
              <dd class="mt-1 text-base font-extrabold text-emerald-700">{{ bed.enabled ? 'aktiv' : 'deaktiviert' }}</dd>
            </div>
          </dl>

          <div v-if="isBedWatering(bed)" class="mb-7 rounded-lg border border-emerald-100 bg-emerald-50/70 p-5">
            <div class="flex items-start justify-between gap-4">
              <div class="flex gap-4">
                <svg class="mt-1 h-6 w-6 text-emerald-700" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M12 2.69 17.66 8.35a8 8 0 1 1-11.32 0L12 2.69ZM12 20a6 6 0 0 0 4.24-10.24L12 5.52 7.76 9.76A6 6 0 0 0 12 20Z" />
                </svg>
                <div>
                  <p class="text-lg font-extrabold text-emerald-800">Bewässerung läuft</p>
                  <p class="mt-1 text-base font-medium text-slate-500">{{ currentIrrigation?.trigger === 'manual' ? 'Manuell gestartet' : 'Automatisch gestartet' }}</p>
                </div>
              </div>
              <div class="text-right">
                <p class="text-lg font-extrabold text-emerald-800">Noch {{ formatDuration(currentIrrigation?.remaining_seconds) }}</p>
                <p class="mt-1 text-base font-medium text-slate-500">von {{ formatDuration(currentIrrigation?.planned_duration_seconds) }}</p>
              </div>
            </div>
            <div class="mt-5 h-2 rounded-full bg-slate-100">
              <div class="h-2 rounded-full bg-emerald-600 transition-all" :style="{ width: `${progressPercent(bed)}%` }" />
            </div>
            <div class="mt-4 flex flex-wrap gap-4">
              <span class="inline-flex items-center gap-2 rounded-lg bg-white/80 px-4 py-2 text-sm font-bold text-emerald-800"><span class="h-2 w-2 rounded-full bg-emerald-600" />Pumpe aktiv</span>
              <span class="inline-flex items-center gap-2 rounded-lg bg-blue-50 px-4 py-2 text-sm font-bold text-blue-700"><span class="h-2 w-2 rounded-full bg-blue-600" />Dauer {{ bed.watering_seconds }} s</span>
              <span class="inline-flex items-center gap-2 rounded-lg bg-emerald-50 px-4 py-2 text-sm font-bold text-emerald-700"><span class="h-2 w-2 rounded-full bg-emerald-600" />Beet aktiv</span>
            </div>
          </div>
          <div class="grid gap-5 sm:grid-cols-2">
            <button v-if="isBedWatering(bed)" class="inline-flex h-14 items-center justify-center gap-3 rounded-lg border border-red-400 bg-white text-base font-extrabold text-red-600 transition hover:bg-red-50" @click="stopWater(bed)">
              <svg class="h-6 w-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M6 6h12v12H6V6Z" />
              </svg>
              Abbrechen
            </button>
            <button v-else class="inline-flex h-14 items-center justify-center gap-3 rounded-lg bg-blue-600 text-base font-extrabold text-white shadow-sm transition hover:bg-blue-700 disabled:bg-slate-300" :disabled="wateringIds.has(bed.id) || !bed.enabled || Boolean(currentIrrigation?.running)" @click="water(bed)">
              <svg class="h-6 w-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 2.69 17.66 8.35a8 8 0 1 1-11.32 0L12 2.69ZM12 20a6 6 0 0 0 4.24-10.24L12 5.52 7.76 9.76A6 6 0 0 0 12 20Z" />
              </svg>
              {{ currentIrrigation?.running ? 'Andere Bewässerung läuft' : 'Jetzt bewässern' }}
            </button>
            <button class="inline-flex h-14 items-center justify-center gap-3 rounded-lg border border-slate-200 bg-white text-base font-extrabold text-slate-900 transition hover:border-blue-300 hover:text-blue-700" @click="readMoisture(bed)">
              <svg class="h-6 w-6 text-slate-700" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm0 2C6.48 22 2 17.52 2 12S6.48 2 12 2s10 4.48 10 10-4.48 10-10 10Zm.5-15H11v6l5.25 3.15.75-1.23-4.5-2.67V7Z" />
              </svg>
              Messen
            </button>
          </div>
        </article>
      </section>

      <footer class="mt-8 flex flex-col gap-3 border-t border-slate-200 py-6 text-base font-medium text-slate-500 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex flex-wrap gap-5">
          <span><span class="mr-2 inline-block h-3 w-3 rounded-full bg-emerald-600" />Backend: <strong class="font-semibold text-emerald-700">{{ status?.backend_reachable ? 'Online' : 'Unbekannt' }}</strong></span>
          <span class="text-slate-300">|</span>
          <span>Hardware: {{ status?.hardware_mock ? 'Mock aktiv' : 'Realbetrieb' }}</span>
          <span class="text-slate-300">|</span>
          <span>MQTT: {{ status?.mqtt_enabled ? (status.mqtt_connected ? 'Verbunden' : 'Aktiv') : 'Aus' }}</span>
        </div>
        <p>Letzte Aktualisierung: {{ lastUpdated }}</p>
      </footer>
    </div>

    <div v-if="activeModal" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 py-6" @click.self="closeModal">
      <section class="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-5 shadow-xl">
        <div class="mb-5 flex items-center justify-between gap-4">
          <div>
            <p class="text-xs font-semibold uppercase tracking-wide text-leaf">{{ activeModal === 'bed' ? 'Beet' : 'System' }}</p>
            <h2 class="text-xl font-semibold">{{ activeModal === 'bed' ? modalTitle : 'App-Einstellungen' }}</h2>
          </div>
          <button
            class="grid h-9 w-9 place-items-center rounded-full border border-slate-200 text-slate-700 hover:bg-slate-100"
            title="Schliessen"
            aria-label="Schliessen"
            @click="closeModal"
          >
            <svg class="h-5 w-5" aria-hidden="true" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18.3 5.71 12 12l6.3 6.29-1.41 1.41L10.59 13.41 4.29 19.71 2.88 18.3 9.17 12 2.88 5.71 4.29 4.29l6.3 6.3 6.29-6.3 1.42 1.42Z" />
            </svg>
          </button>
        </div>

        <form v-if="activeModal === 'bed'" class="grid gap-4 sm:grid-cols-2" @submit.prevent="saveBed">
          <label class="text-sm font-medium">Name<input v-model="form.name" required class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
          <label class="text-sm font-medium">GPIO<input v-model.number="form.relay_pin" required type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
          <label class="text-sm font-medium">ADS-Kanal<input v-model.number="form.ads_channel" required min="0" max="3" type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
          <label class="text-sm font-medium">Bewässerungsdauer<input v-model.number="form.watering_seconds" required min="1" type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
          <label class="text-sm font-medium">
            Automatik-Pause nach Abbruch
            <input v-model.number="autoBlockMinutes" required min="0" type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
            <span class="mt-1 block text-xs text-slate-500">Minuten</span>
          </label>
          <div class="border-t border-slate-100 pt-4 sm:col-span-2">
            <h3 class="font-semibold text-slate-950">Kalibrierung</h3>
          </div>
          <label class="text-sm font-medium">Trocken raw<input v-model.number="form.moisture_dry_raw" required type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
          <label class="text-sm font-medium">Nass raw<input v-model.number="form.moisture_wet_raw" required type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
          <label class="flex items-center gap-2 text-sm font-medium sm:col-span-2">
            <input v-model="form.enabled" type="checkbox" class="h-4 w-4 rounded" /> Aktiv
          </label>

          <div v-if="isEditing" class="sm:col-span-2">
            <div v-if="confirmingDelete" class="rounded-md border border-red-200 bg-red-50 p-4">
              <p class="font-semibold text-red-900">Beet wirklich löschen?</p>
              <p class="mt-1 text-sm text-red-800">Messwerte und Bewässerungsläufe dieses Beets werden ebenfalls entfernt.</p>
              <div class="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  class="inline-flex items-center gap-2 rounded-md bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800"
                  :disabled="saving"
                  @click="deleteCurrentBed"
                >
                  <svg class="h-4 w-4" aria-hidden="true" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M6 19c0 1.1.9 2 2 2h8a2 2 0 0 0 2-2V7H6v12ZM8 9h8v10H8V9Zm7.5-5-1-1h-5l-1 1H5v2h14V4h-3.5Z" />
                  </svg>
                  Endgültig löschen
                </button>
                <button type="button" class="rounded-md border border-red-200 bg-white px-4 py-2 text-sm font-semibold text-red-800" @click="confirmingDelete = false">
                  Abbrechen
                </button>
              </div>
            </div>
            <button
              v-else
              type="button"
              class="inline-flex items-center gap-2 rounded-md border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-50"
              @click="confirmingDelete = true"
            >
              <svg class="h-4 w-4" aria-hidden="true" viewBox="0 0 24 24" fill="currentColor">
                <path d="M6 19c0 1.1.9 2 2 2h8a2 2 0 0 0 2-2V7H6v12ZM8 9h8v10H8V9Zm7.5-5-1-1h-5l-1 1H5v2h14V4h-3.5Z" />
              </svg>
              Beet löschen
            </button>
          </div>

          <div v-if="!confirmingDelete" class="flex justify-end gap-2 sm:col-span-2">
            <button type="button" class="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold" @click="closeModal">Abbrechen</button>
            <button class="rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white" :disabled="saving">
              {{ saving ? 'Speichert...' : 'Speichern' }}
            </button>
          </div>
        </form>

        <div v-else class="space-y-4">
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="rounded-md bg-slate-50 p-4">
              <p class="text-sm text-slate-500">Backend</p>
              <p class="mt-1 font-semibold">{{ status?.backend_reachable ? 'erreichbar' : 'unbekannt' }}</p>
            </div>
            <div class="rounded-md bg-slate-50 p-4">
              <p class="text-sm text-slate-500">Hardware-Mock</p>
              <p class="mt-1 font-semibold">{{ status?.hardware_mock ? 'aktiv' : 'inaktiv' }}</p>
            </div>
            <div class="rounded-md bg-slate-50 p-4">
              <p class="text-sm text-slate-500">MQTT</p>
              <p class="mt-1 font-semibold">{{ status?.mqtt_enabled ? (status.mqtt_connected ? 'verbunden' : 'aktiv') : 'aus' }}</p>
            </div>
            <div class="rounded-md bg-slate-50 p-4">
              <p class="text-sm text-slate-500">Max. Bewässerung</p>
              <p class="mt-1 font-semibold">{{ status?.max_watering_seconds ?? '–' }} s</p>
            </div>
          </div>
          <p class="text-sm text-slate-600">
            MQTT, Mock-Modus und Relay-Logik werden im Backend über die `.env` konfiguriert. Diese Ansicht zeigt den aktuellen Zustand.
          </p>
          <div class="flex justify-end">
            <button class="rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white" @click="closeModal">Schliessen</button>
          </div>
        </div>
      </section>
    </div>
  </main>
</template>
