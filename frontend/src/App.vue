<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from './api/client'
import type { Bed, BedPayload, MoistureReading, SystemStatus } from './types/api'

const beds = ref<Bed[]>([])
const readings = ref<Record<number, MoistureReading>>({})
const status = ref<SystemStatus | null>(null)
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const wateringIds = ref<Set<number>>(new Set())
const editingId = ref<number | null>(null)

const emptyForm = (): BedPayload => ({
  name: '',
  relay_pin: 0,
  ads_channel: 0,
  moisture_dry_raw: 26000,
  moisture_wet_raw: 12000,
  watering_seconds: 120,
  enabled: true
})

const form = reactive<BedPayload>(emptyForm())

const isEditing = computed(() => editingId.value !== null)

function assignForm(values: BedPayload) {
  Object.assign(form, values)
}

function resetForm() {
  editingId.value = null
  assignForm(emptyForm())
}

function moistureStatus(percent?: number) {
  if (percent === undefined) return { label: 'keine Messung', color: 'bg-slate-100 text-slate-700' }
  if (percent < 35) return { label: 'trocken', color: 'bg-amber-100 text-amber-800' }
  if (percent > 75) return { label: 'nass', color: 'bg-blue-100 text-blue-800' }
  return { label: 'okay', color: 'bg-emerald-100 text-emerald-800' }
}

async function refresh() {
  error.value = ''
  try {
    const [bedData, latest, systemStatus] = await Promise.all([api.beds(), api.latestReadings(), api.status()])
    beds.value = bedData
    readings.value = Object.fromEntries(latest.map((reading) => [reading.bed_id, reading]))
    status.value = systemStatus
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
  wateringIds.value = new Set(wateringIds.value).add(bed.id)
  try {
    await api.waterBed(bed.id, bed.watering_seconds)
    await refresh()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Bewässerung fehlgeschlagen'
  } finally {
    const next = new Set(wateringIds.value)
    next.delete(bed.id)
    wateringIds.value = next
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
    enabled: bed.enabled
  })
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
    resetForm()
    await refresh()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Speichern fehlgeschlagen'
  } finally {
    saving.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
    <header class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-sm font-semibold uppercase tracking-wide text-leaf">AquaPatch</p>
        <h1 class="text-3xl font-bold text-slate-950">Gartenbewässerung</h1>
      </div>
      <button class="rounded-md bg-leaf px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-800" @click="refresh">
        Aktualisieren
      </button>
    </header>

    <div v-if="error" class="mb-5 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      {{ error }}
    </div>

    <section class="mb-6 grid gap-4 md:grid-cols-4">
      <div class="rounded-lg bg-white p-4 shadow-sm">
        <p class="text-sm text-slate-500">Backend</p>
        <p class="mt-1 text-lg font-semibold">{{ status?.backend_reachable ? 'erreichbar' : 'unbekannt' }}</p>
      </div>
      <div class="rounded-lg bg-white p-4 shadow-sm">
        <p class="text-sm text-slate-500">Hardware-Mock</p>
        <p class="mt-1 text-lg font-semibold">{{ status?.hardware_mock ? 'aktiv' : 'inaktiv' }}</p>
      </div>
      <div class="rounded-lg bg-white p-4 shadow-sm">
        <p class="text-sm text-slate-500">MQTT</p>
        <p class="mt-1 text-lg font-semibold">{{ status?.mqtt_enabled ? (status.mqtt_connected ? 'verbunden' : 'aktiv') : 'aus' }}</p>
      </div>
      <div class="rounded-lg bg-white p-4 shadow-sm">
        <p class="text-sm text-slate-500">Beete</p>
        <p class="mt-1 text-lg font-semibold">{{ status?.bed_count ?? beds.length }}</p>
      </div>
    </section>

    <section class="mb-6 rounded-lg bg-white p-5 shadow-sm">
      <h2 class="mb-4 text-lg font-semibold">{{ isEditing ? 'Beet bearbeiten' : 'Neues Beet anlegen' }}</h2>
      <form class="grid gap-4 md:grid-cols-4" @submit.prevent="saveBed">
        <label class="text-sm font-medium">Name<input v-model="form.name" required class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
        <label class="text-sm font-medium">GPIO<input v-model.number="form.relay_pin" required type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
        <label class="text-sm font-medium">ADS-Kanal<input v-model.number="form.ads_channel" required min="0" max="3" type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
        <label class="text-sm font-medium">Sekunden<input v-model.number="form.watering_seconds" required min="1" type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
        <label class="text-sm font-medium">Trocken raw<input v-model.number="form.moisture_dry_raw" required type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
        <label class="text-sm font-medium">Nass raw<input v-model.number="form.moisture_wet_raw" required type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
        <label class="flex items-center gap-2 pt-6 text-sm font-medium"><input v-model="form.enabled" type="checkbox" class="h-4 w-4 rounded" /> Aktiv</label>
        <div class="flex items-end gap-2">
          <button class="rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white" :disabled="saving">{{ saving ? 'Speichert...' : 'Speichern' }}</button>
          <button v-if="isEditing" type="button" class="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold" @click="resetForm">Abbrechen</button>
        </div>
      </form>
    </section>

    <p v-if="loading" class="py-10 text-center text-slate-600">Lade Beete...</p>
    <section v-else class="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      <article v-for="bed in beds" :key="bed.id" class="rounded-lg bg-white p-5 shadow-sm">
        <div class="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 class="text-xl font-semibold">{{ bed.name }}</h2>
            <p class="text-sm text-slate-500">GPIO {{ bed.relay_pin }} · ADS A{{ bed.ads_channel }}</p>
          </div>
          <span class="rounded-full px-3 py-1 text-xs font-semibold" :class="moistureStatus(readings[bed.id]?.moisture_percent).color">
            {{ moistureStatus(readings[bed.id]?.moisture_percent).label }}
          </span>
        </div>
        <div class="mb-4">
          <p class="text-4xl font-bold">{{ readings[bed.id]?.moisture_percent ?? '–' }}<span class="text-lg">%</span></p>
          <p class="text-sm text-slate-500">
            Rohwert {{ readings[bed.id]?.raw_value ?? '–' }} · {{ readings[bed.id]?.voltage?.toFixed(2) ?? '–' }} V
          </p>
          <p class="mt-1 text-sm text-slate-500">Letzte Messung {{ readings[bed.id]?.created_at ? new Date(readings[bed.id].created_at).toLocaleString() : 'ausstehend' }}</p>
        </div>
        <dl class="mb-5 grid grid-cols-2 gap-3 text-sm">
          <div class="rounded-md bg-slate-50 p-3"><dt class="text-slate-500">Pumpe</dt><dd class="font-semibold">{{ bed.pump_running || wateringIds.has(bed.id) ? 'läuft' : 'aus' }}</dd></div>
          <div class="rounded-md bg-slate-50 p-3"><dt class="text-slate-500">Dauer</dt><dd class="font-semibold">{{ bed.watering_seconds }} s</dd></div>
          <div class="rounded-md bg-slate-50 p-3"><dt class="text-slate-500">Kalibrierung</dt><dd class="font-semibold">{{ bed.moisture_dry_raw }} / {{ bed.moisture_wet_raw }}</dd></div>
          <div class="rounded-md bg-slate-50 p-3"><dt class="text-slate-500">Status</dt><dd class="font-semibold">{{ bed.enabled ? 'aktiv' : 'deaktiviert' }}</dd></div>
        </dl>
        <div class="flex flex-wrap gap-2">
          <button class="rounded-md bg-water px-3 py-2 text-sm font-semibold text-white" :disabled="wateringIds.has(bed.id) || !bed.enabled" @click="water(bed)">
            {{ wateringIds.has(bed.id) ? 'Bewässert...' : 'Jetzt bewässern' }}
          </button>
          <button class="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold" @click="readMoisture(bed)">Messen</button>
          <button class="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold" @click="editBed(bed)">Bearbeiten</button>
        </div>
      </article>
    </section>
  </main>
</template>
