# AquaPatch

AquaPatch is a local garden irrigation dashboard for a Raspberry Pi 4. It controls one relay-driven 24 V pump per bed, reads capacitive soil moisture sensors through an ADS1115 ADC, and stays fully usable without cloud services, Home Assistant, user accounts or Docker.

The current implementation includes a FastAPI backend, SQLite database, Vue 3 frontend, mock hardware mode, optional DHT21 climate readings and optional MQTT publishing for future Home Assistant integration.

## Current Features

- FastAPI REST API with SQLite and SQLAlchemy 2.x.
- Default beds on first startup: `Hochbeet 1`, `Tomaten`, `Blumen`.
- CRUD API for beds, calibration values and sensor warning thresholds.
- Mock ADS1115/DHT21 readings and mock relay actions for local development.
- Moisture percentage calculation from per-bed dry/wet raw calibration.
- Sensor plausibility warnings for unrealistically low raw moisture values.
- Manual watering endpoint with maximum duration, visible remaining runtime and manual cancellation.
- Irrigation run log with trigger, status, error message and optional moisture values before/after watering.
- Global irrigation lock: only one pump runs at a time.
- Automatic watering pause after manual cancellation, configurable per bed.
- Relay cleanup on shutdown and `finally` pump-off behavior after watering.
- Tageszusammenfassung with per-bed watering duration, last watering, moisture min/max/average and sensor warning counts.
- 24h moisture mini charts using 5-minute averages and irrigation interval markers.
- Optional MQTT publishing for moisture, sensor, climate, pump and system state.
- Vue dashboard with clean bed cards, Material Design SVG icons, compact app controls, 10-second auto-refresh, manual watering, moisture reads, DHT21 climate display, daily summary and modal settings for beds and app status.
- Raspberry Pi deployment scripts for rsync-based deploy, preflight setup and systemd service installation.

Planned:
- Automatic watering schedules.
- Water tank level sensor support.
- Rain or weather lockout.
- Home Assistant MQTT Discovery.

## Hardware Overview

Initial target hardware:

- Raspberry Pi 4.
- ADS1115 connected by I2C.
- DHT21/AM2301 on GPIO4.
- Capacitive Soil Moisture Sensor v1.2 on ADS1115 channels A0, A1 and A2.
- Relay channels on GPIO27, GPIO21, GPIO13 and reserve relay GPIO26.
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
scripts/
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

The Vite dev server is configured for port `5173` and proxies `/api` to `http://localhost:8000`. Build production assets with:

```bash
npm run build
```

For local development the Vite frontend runs on `5173` and the API runs on `8000`. On the Raspberry Pi, Nginx serves the built frontend on standard HTTP port `80`, so `http://aquapatch/` works without a port suffix. The FastAPI backend continues to listen on `8000`; Nginx proxies `/api` to it.

Dashboard usage:

- Use the `+` button in the header to add a new bed.
- Use the gear in a bed card to edit relay pin, ADS channel, watering duration, enabled state and moisture calibration.
- Set `Automatik-Pause nach Abbruch` in minutes inside each bed's settings dialog.
- Set `Sensorwarnung unter raw` per bed to flag disconnected or implausible moisture sensors.
- Use the delete action inside a bed's settings dialog to remove a bed after confirmation.
- Use the app gear in the header to view backend, mock, MQTT, DHT21 and maximum watering status.
- Bed and app settings open as overlays, keeping the main dashboard focused on current bed state.
- During watering, the active bed card shows remaining time, total planned duration, a progress bar and an `Abbrechen` button.
- The dashboard refreshes bed data, latest readings, pump status, climate and the daily summary every 10 seconds. Manual refresh remains available.

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./aquapatch.db` | SQLite database URL. |
| `HARDWARE_MOCK` | `true` | Enables simulated ADS1115 and relay logging. |
| `RELAY_ACTIVE_LOW` | `true` | Uses active-low relay logic when true. |
| `RELAY_GPIO_PINS` | `27,21,13,26` | Comma-separated GPIO pins allowed for relay-controlled beds. |
| `RELAY_RESERVE_PINS` | `26` | Relay GPIOs initialized and switched off at startup even when no bed uses them yet. |
| `MAX_WATERING_SECONDS` | `300` | Upper limit for any watering run. |
| `MQTT_ENABLED` | `false` | Enables optional MQTT integration. |
| `MQTT_HOST` | `localhost` | MQTT broker host. |
| `MQTT_PORT` | `1883` | MQTT broker port. |
| `MQTT_USERNAME` | empty | Optional MQTT username. |
| `MQTT_PASSWORD` | empty | Optional MQTT password. |
| `MQTT_BASE_TOPIC` | `garden_irrigation` | Base topic for MQTT publishing. |
| `DHT21_ENABLED` | `true` | Enables DHT21 climate readings. |
| `DHT21_GPIO_PIN` | `4` | GPIO pin used for the DHT21 data line. |

## API Overview

Beds:

- `GET /api/beds`
- `POST /api/beds`
- `GET /api/beds/{bed_id}`
- `PUT /api/beds/{bed_id}`
- `DELETE /api/beds/{bed_id}`

Moisture:

- `GET /api/beds/{bed_id}/moisture`
- `GET /api/beds/{bed_id}/moisture/series?range=24h&bucket=5m`
- `GET /api/readings/latest`
- `GET /api/readings?bed_id=1&limit=100`

Irrigation:

- `POST /api/beds/{bed_id}/water`
- `POST /api/beds/{bed_id}/water/stop`
- `GET /api/irrigation/current`
- `POST /api/irrigation/current/stop`
- `GET /api/irrigation/runs`
- `GET /api/irrigation/runs?bed_id=1&limit=50`
- `GET /api/beds/{bed_id}/irrigation/intervals?range=24h`

Climate:

- `GET /api/climate/latest`
- `GET /api/climate/readings?limit=100`
- `POST /api/climate/read`

Summary:

- `GET /api/summary/today`
- `GET /api/summary/daily?date=YYYY-MM-DD`

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

Current wiring:

- ADS1115 `VDD` to Pi `3.3 V`.
- ADS1115 `GND` to Pi `GND`.
- ADS1115 `SCL` to Pi `GPIO3/SCL`.
- ADS1115 `SDA` to Pi `GPIO2/SDA`.
- Moisture sensor analog outputs to ADS1115 `A0`, `A1`, `A2`.
- DHT21 data pin to Pi `GPIO4`.
- Relay 1 / pump 1 input to Pi `GPIO27`.
- Relay 2 / pump 2 input to Pi `GPIO21`.
- Relay 3 / pump 3 input to Pi `GPIO13`.
- Relay 4 reserve input to Pi `GPIO26`.
- Pumps in the separate 24 V relay load circuit.

Default moisture calibration for new beds:

- Dry raw value: `17750`
- Wet/moist raw value: `7700`

Existing beds that still use the old default calibration pair `26000` / `12000` are migrated to these values during backend startup. Beds with custom calibration values are left unchanged.

Moisture sensor plausibility:

- Each bed has `sensor_disconnected_raw_threshold`, default `5000`.
- If a raw value is below the threshold, the reading is stored with `is_valid=false`, `warning_code="sensor_disconnected"` and no normal moisture percentage.
- Automatic watering is blocked for invalid sensor values. Manual watering remains possible, but the dashboard shows a visible warning.

Climate readings:

- `DHT21_ENABLED=true` enables the connected DHT21 on GPIO4.
- In mock mode, DHT21 readings are simulated between `21.0` and `30.0 °C` and `45.0` to `85.0 %` relative humidity.
- Real DHT21 reads retry short transient buffer failures before storing an invalid reading.
- Climate readings are stored in SQLite and included in the daily summary when available.

Relay pin assignment:

- Pump 1 / relay 1: `GPIO27`, ADS1115 `A0`.
- Pump 2 / relay 2: `GPIO21`, ADS1115 `A1`.
- Pump 3 / relay 3: `GPIO13`, ADS1115 `A2`.
- Reserve / relay 4: `GPIO26`, initialized off at startup.
- DHT21 data: `GPIO4`.

Existing installations with the previous default relay mapping are migrated on backend startup when ADS channels still use the old default pins. Custom bed assignments are left unchanged if a target pin is already occupied.

## Raspberry Pi Deployment

Target deployment configured for the current local Pi:

- Host: `aquapatch` (`192.168.178.97` in local hosts)
- SSH user: `christopher`
- SSH key: `/Users/christopher/.ssh/id_ed25519`
- Remote directory: `/home/christopher/aquapatch`
- Service: `aquapatch-backend`
- URL after deployment: `http://aquapatch/`

Deploy from this machine with rsync:

```bash
scripts/deploy-pi.sh
```

The deploy script syncs the repository to the Pi, excluding local virtualenvs, `node_modules`, built frontend files, local `.env` files and SQLite databases. It then runs the Pi setup script remotely:

```bash
scripts/setup-pi.sh
```

The setup script performs a small preflight, installs required apt packages, creates `backend/.venv`, installs Python dependencies, creates `backend/.env` if missing, builds the frontend, installs the systemd unit and configures Nginx. If `ufw` is installed and active, it allows `80/tcp` for the frontend and `8000/tcp` for the API.

For first hardware testing, deploy with real hardware mode:

```bash
scripts/deploy-pi.sh --real-hardware
```

Without `--real-hardware`, a newly created Pi `.env` keeps `HARDWARE_MOCK=true` for safety. This lets the service start and the dashboard load before any relay can switch a pump. If `backend/.env` already exists on the Pi, the setup script preserves unrelated values, but always ensures the current relay pin mapping and DHT21 GPIO settings are present. With `--real-hardware`, it also sets `HARDWARE_MOCK=false`.

Useful service commands on the Pi:

```bash
sudo systemctl status aquapatch-backend
sudo journalctl -u aquapatch-backend -f
sudo systemctl restart aquapatch-backend
```

Manual setup on the Pi, if rsync deployment is skipped:

```bash
cd /home/christopher/aquapatch
bash scripts/setup-pi.sh
```

The systemd unit is installed from:

```bash
backend/systemd/aquapatch-backend.service
```

It runs the API:

```text
/home/christopher/aquapatch/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

and reads configuration from:

```text
/home/christopher/aquapatch/backend/.env
```

Nginx serves the built frontend from `/var/www/aquapatch` on port `80` and proxies `/api` to `127.0.0.1:8000`.

If you need to install the unit manually:

```bash
sudo cp backend/systemd/aquapatch-backend.service /etc/systemd/system/aquapatch-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now aquapatch-backend
sudo systemctl status aquapatch-backend
```

The Nginx site config is installed from:

```bash
backend/systemd/aquapatch-nginx.conf
```

## MQTT and Home Assistant Readiness

MQTT is optional and disabled by default. When enabled, AquaPatch publishes under `garden_irrigation` unless `MQTT_BASE_TOPIC` is changed.

Topics include:

```text
garden_irrigation/bed/{bed_id}/name
garden_irrigation/bed/{bed_id}/moisture_percent
garden_irrigation/bed/{bed_id}/moisture_raw
garden_irrigation/bed/{bed_id}/moisture_voltage
garden_irrigation/bed/{bed_id}/sensor/status
garden_irrigation/bed/{bed_id}/sensor/warning_code
garden_irrigation/bed/{bed_id}/sensor/is_valid
garden_irrigation/bed/{bed_id}/moisture/series_available
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
garden_irrigation/climate/temperature_c
garden_irrigation/climate/humidity_percent
garden_irrigation/climate/status
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
[ ] DHT21 is detected when `DHT21_ENABLED=true`
[ ] moisture values can be read from all configured channels
[ ] sensor warning appears for disconnected or implausibly low moisture sensors
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
[ ] automatic watering is blocked when a moisture reading is invalid
[ ] frontend shows current bed states
[ ] frontend shows climate, daily summary and moisture charts
[ ] manual watering works from frontend
[ ] README matches the actual setup
```

## Known Limitations

- MQTT command handling is prepared at the service layer, but REST is the primary supported control path in this first implementation.
- Hardware behavior still needs validation on the Raspberry Pi with the actual relay board and ADS1115.
- DHT21 support is optional and still needs validation with the actual sensor wiring on Raspberry Pi hardware.
