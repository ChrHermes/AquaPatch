# AquaPatch

AquaPatch is a local garden irrigation dashboard for a Raspberry Pi 4. It controls one relay-driven 24 V pump per bed, reads capacitive soil moisture sensors through an ADS1115 ADC, and stays fully usable without cloud services, Home Assistant, user accounts or Docker.

The current implementation includes a FastAPI backend, SQLite database, Vue 3 frontend, mock hardware mode and optional MQTT publishing for future Home Assistant integration.

## Current Features

- FastAPI REST API with SQLite and SQLAlchemy 2.x.
- Default beds on first startup: `Tomaten`, `Hortensien 1`, `Hortensien 2`.
- CRUD API for beds and calibration values.
- Mock ADS1115 readings and mock relay actions for local development.
- Moisture percentage calculation from per-bed dry/wet raw calibration.
- Manual watering endpoint with maximum duration, visible remaining runtime and manual cancellation.
- Global irrigation lock: only one pump runs at a time.
- Automatic watering pause after manual cancellation, configurable per bed.
- Relay cleanup on shutdown and `finally` pump-off behavior after watering.
- Optional MQTT publishing for moisture, pump and system state.
- Vue dashboard with clean bed cards, Material Design SVG icons, compact app controls, manual watering, moisture reads and modal settings for beds and app status.

Planned:
- Automatic watering schedules.
- Water tank level sensor support.
- Rain or weather lockout.
- Home Assistant MQTT Discovery.
- Charts for moisture history.

## Hardware Overview

Initial target hardware:

- Raspberry Pi 4.
- ADS1115 connected by I2C.
- Capacitive Soil Moisture Sensor v1.2 on ADS1115 channels A0, A1 and A2.
- Relay channels on GPIO17, GPIO27 and GPIO22.
- Three 24 V DC pumps switched in the external load circuit.

Important safety notes:

- Raspberry Pi GPIO pins are not 5 V tolerant.
- Do not power pumps from GPIO pins.
- Use relay or MOSFET modules rated for the pump current and 24 V load.
- Keep the 24 V pump circuit and Raspberry Pi wiring cleanly separated and correctly grounded for the chosen relay module.
- Relays may be active-low; configure this with `RELAY_ACTIVE_LOW`.

## Project Structure

```text
backend/
  app/
    api/
    core/
    hardware/
    integrations/
    models/
    schemas/
    services/
  systemd/
frontend/
  src/
README.md
CHANGELOG.md
```

## Backend Setup

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

For local development, keep `HARDWARE_MOCK=true`. This logs relay actions and simulates sensor values, so no Raspberry Pi hardware is needed.

API docs are available at:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Quick Mock Start

From the project root, start the backend in mock mode and the Vite frontend together:

```bash
./mock-dev.sh
```

This starts:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`

Use this for normal local development. Starting only `npm run dev` inside `frontend/` launches the UI without the FastAPI API, so the dashboard cannot load bed data.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`. Build production assets with:

```bash
npm run build
```

Dashboard usage:

- Use the `+` button in the header to add a new bed.
- Use the gear in a bed card to edit relay pin, ADS channel, watering duration, enabled state and moisture calibration.
- Set `Automatik-Pause nach Abbruch` in minutes inside each bed's settings dialog.
- Use the delete action inside a bed's settings dialog to remove a bed after confirmation.
- Use the app gear in the header to view backend, mock, MQTT and maximum watering status.
- Bed and app settings open as overlays, keeping the main dashboard focused on current bed state.
- During watering, the active bed card shows remaining time, total planned duration, a progress bar and an `Abbrechen` button.

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./aquapatch.db` | SQLite database URL. |
| `HARDWARE_MOCK` | `true` | Enables simulated ADS1115 and relay logging. |
| `RELAY_ACTIVE_LOW` | `true` | Uses active-low relay logic when true. |
| `MAX_WATERING_SECONDS` | `300` | Upper limit for any watering run. |
| `MQTT_ENABLED` | `false` | Enables optional MQTT integration. |
| `MQTT_HOST` | `localhost` | MQTT broker host. |
| `MQTT_PORT` | `1883` | MQTT broker port. |
| `MQTT_USERNAME` | empty | Optional MQTT username. |
| `MQTT_PASSWORD` | empty | Optional MQTT password. |
| `MQTT_BASE_TOPIC` | `garden_irrigation` | Base topic for MQTT publishing. |

## API Overview

Beds:

- `GET /api/beds`
- `POST /api/beds`
- `GET /api/beds/{bed_id}`
- `PUT /api/beds/{bed_id}`
- `DELETE /api/beds/{bed_id}`

Moisture:

- `GET /api/beds/{bed_id}/moisture`
- `GET /api/readings/latest`
- `GET /api/readings?bed_id=1&limit=100`

Irrigation:

- `POST /api/beds/{bed_id}/water`
- `POST /api/beds/{bed_id}/water/stop`
- `GET /api/irrigation/current`
- `POST /api/irrigation/current/stop`
- `GET /api/irrigation/runs`
- `GET /api/irrigation/runs?bed_id=1&limit=50`

System:

- `GET /api/system/status`
- `GET /api/system/events`

## Raspberry Pi Setup Notes

Enable I2C:

```bash
sudo raspi-config
```

Use `Interface Options` -> `I2C` -> enable. After reboot, verify the ADS1115:

```bash
sudo apt install -y i2c-tools
i2cdetect -y 1
```

Typical wiring:

- ADS1115 `VDD` to Pi `3.3 V`.
- ADS1115 `GND` to Pi `GND`.
- ADS1115 `SCL` to Pi `GPIO3/SCL`.
- ADS1115 `SDA` to Pi `GPIO2/SDA`.
- Moisture sensor analog outputs to ADS1115 `A0`, `A1`, `A2`.
- Relay inputs to Pi `GPIO17`, `GPIO27`, `GPIO22`.
- Pumps in the separate 24 V relay load circuit.

## systemd Backend Deployment

Copy the project to `/opt/aquapatch`, create `backend/.env`, install dependencies into `/opt/aquapatch/backend/.venv`, then install the unit:

```bash
sudo cp backend/systemd/aquapatch-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aquapatch-backend
sudo systemctl status aquapatch-backend
```

For the frontend, build with `npm run build` and serve `frontend/dist` with nginx or another local static file server.

## MQTT and Home Assistant Readiness

MQTT is optional and disabled by default. When enabled, AquaPatch publishes under `garden_irrigation` unless `MQTT_BASE_TOPIC` is changed.

Topics include:

```text
garden_irrigation/bed/{bed_id}/name
garden_irrigation/bed/{bed_id}/moisture_percent
garden_irrigation/bed/{bed_id}/moisture_raw
garden_irrigation/bed/{bed_id}/moisture_voltage
garden_irrigation/bed/{bed_id}/pump/state
garden_irrigation/bed/{bed_id}/irrigation/last_run
garden_irrigation/bed/{bed_id}/irrigation/remaining_seconds
garden_irrigation/bed/{bed_id}/irrigation/elapsed_seconds
garden_irrigation/bed/{bed_id}/irrigation/status
garden_irrigation/bed/{bed_id}/irrigation/cancelled
garden_irrigation/bed/{bed_id}/auto_watering/blocked_until
garden_irrigation/bed/{bed_id}/auto_watering/block_remaining_seconds
garden_irrigation/bed/{bed_id}/status
garden_irrigation/system/status
garden_irrigation/system/hardware_mock
garden_irrigation/system/mqtt/status
```

MQTT command topics:

```text
garden_irrigation/bed/{bed_id}/water/set
garden_irrigation/bed/{bed_id}/water/stop/set
```

Example Home Assistant YAML sensor:

```yaml
mqtt:
  sensor:
    - name: "AquaPatch Hochbeet Feuchte"
      state_topic: "garden_irrigation/bed/1/moisture_percent"
      unit_of_measurement: "%"
```

Home Assistant MQTT Discovery is not implemented yet.

## Manual Hardware Test Checklist

```text
[ ] Raspberry Pi boots and application starts
[ ] I2C is enabled
[ ] ADS1115 is detected
[ ] moisture values can be read from all configured channels
[ ] each relay can be switched individually
[ ] relay active-low setting is correct
[ ] each pump starts only for its assigned bed
[ ] only one pump can run at a time
[ ] active watering shows remaining runtime in the frontend
[ ] active watering can be cancelled from the frontend
[ ] pump stops after configured duration
[ ] pump stops after API error or interruption
[ ] pump stops after manual cancellation
[ ] automatic watering is blocked for a bed after manual cancellation
[ ] frontend shows current bed states
[ ] manual watering works from frontend
[ ] README matches the actual setup
```

## Known Limitations

- MQTT command handling is prepared at the service layer, but REST is the primary supported control path in this first implementation.
- Hardware behavior still needs validation on the Raspberry Pi with the actual relay board and ADS1115.
- The frontend does not include charts yet.
