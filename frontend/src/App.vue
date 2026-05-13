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
const activeModal = ref<'bed' | 'app' | null>(null)

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
const modalTitle = computed(() => (isEditing.value ? 'Beet bearbeiten' : 'Neues Beet anlegen'))

function assignForm(values: BedPayload) {
  Object.assign(form, values)
}

function resetForm() {
  editingId.value = null
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

onMounted(refresh)
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
    <header class="mb-6 flex items-start justify-between gap-4">
      <div>
        <p class="text-sm font-semibold uppercase tracking-wide text-leaf">AquaPatch</p>
        <h1 class="text-3xl font-bold text-slate-950">Gartenbewässerung</h1>
        <p class="mt-1 text-sm text-slate-500">
          {{ status?.bed_count ?? beds.length }} Beete · Mock {{ status?.hardware_mock ? 'aktiv' : 'aus' }} · MQTT
          {{ status?.mqtt_enabled ? (status.mqtt_connected ? 'verbunden' : 'aktiv') : 'aus' }}
        </p>
      </div>
      <div class="flex shrink-0 gap-2">
        <button
          class="grid h-10 w-10 place-items-center rounded-full border border-slate-200 bg-white text-xl font-semibold text-slate-800 shadow-sm hover:border-leaf hover:text-leaf"
          title="Neues Beet"
          aria-label="Neues Beet"
          @click="newBed"
        >
          +
        </button>
        <button
          class="grid h-10 w-10 place-items-center rounded-full border border-slate-200 bg-white text-lg text-slate-800 shadow-sm hover:border-leaf hover:text-leaf"
          title="App-Einstellungen"
          aria-label="App-Einstellungen"
          @click="activeModal = 'app'"
        >
          ⚙
        </button>
        <button
          class="grid h-10 w-10 place-items-center rounded-full border border-slate-200 bg-white text-lg text-slate-800 shadow-sm hover:border-leaf hover:text-leaf"
          title="Aktualisieren"
          aria-label="Aktualisieren"
          @click="refresh"
        >
          ↻
        </button>
      </div>
    </header>

    <div v-if="error" class="mb-5 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      {{ error }}
    </div>

    <p v-if="loading" class="py-10 text-center text-slate-600">Lade Beete...</p>
    <section v-else class="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      <article v-for="bed in beds" :key="bed.id" class="rounded-lg bg-white p-5 shadow-sm">
        <div class="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 class="text-xl font-semibold">{{ bed.name }}</h2>
            <p class="text-sm text-slate-500">GPIO {{ bed.relay_pin }} · ADS A{{ bed.ads_channel }}</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="rounded-full px-3 py-1 text-xs font-semibold" :class="moistureStatus(readings[bed.id]?.moisture_percent).color">
              {{ moistureStatus(readings[bed.id]?.moisture_percent).label }}
            </span>
            <button
              class="grid h-8 w-8 place-items-center rounded-full text-slate-500 hover:bg-slate-100 hover:text-slate-950"
              title="Beet-Einstellungen"
              aria-label="Beet-Einstellungen"
              @click="editBed(bed)"
            >
              ⚙
            </button>
          </div>
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
        </div>
      </article>
    </section>

    <div v-if="activeModal" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 py-6" @click.self="closeModal">
      <section class="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-5 shadow-xl">
        <div class="mb-5 flex items-center justify-between gap-4">
          <div>
            <p class="text-xs font-semibold uppercase tracking-wide text-leaf">{{ activeModal === 'bed' ? 'Beet' : 'System' }}</p>
            <h2 class="text-xl font-semibold">{{ activeModal === 'bed' ? modalTitle : 'App-Einstellungen' }}</h2>
          </div>
          <button
            class="grid h-9 w-9 place-items-center rounded-full border border-slate-200 text-xl text-slate-700 hover:bg-slate-100"
            title="Schliessen"
            aria-label="Schliessen"
            @click="closeModal"
          >
            ×
          </button>
        </div>

        <form v-if="activeModal === 'bed'" class="grid gap-4 sm:grid-cols-2" @submit.prevent="saveBed">
          <label class="text-sm font-medium">Name<input v-model="form.name" required class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
          <label class="text-sm font-medium">GPIO<input v-model.number="form.relay_pin" required type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
          <label class="text-sm font-medium">ADS-Kanal<input v-model.number="form.ads_channel" required min="0" max="3" type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
          <label class="text-sm font-medium">Bewässerungsdauer<input v-model.number="form.watering_seconds" required min="1" type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
          <label class="text-sm font-medium">Trocken raw<input v-model.number="form.moisture_dry_raw" required type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
          <label class="text-sm font-medium">Nass raw<input v-model.number="form.moisture_wet_raw" required type="number" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" /></label>
          <label class="flex items-center gap-2 text-sm font-medium sm:col-span-2">
            <input v-model="form.enabled" type="checkbox" class="h-4 w-4 rounded" /> Aktiv
          </label>
          <div class="flex justify-end gap-2 sm:col-span-2">
            <button type="button" class="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold" @click="closeModal">Abbrechen</button>
            <button class="rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white" :disabled="saving">{{ saving ? 'Speichert...' : 'Speichern' }}</button>
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
