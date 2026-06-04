## Unreleased

### Added
- Initial FastAPI backend with SQLite, SQLAlchemy models, Pydantic schemas and required REST routes.
- Mock-safe hardware abstraction for Raspberry Pi GPIO relays and ADS1115 moisture readings.
- Irrigation safety service with a single-run lock, maximum duration enforcement and shutdown pump cleanup.
- Optional MQTT service with AquaPatch topic structure for moisture, pump and system state publishing.
- Vue 3, Vite, TypeScript and TailwindCSS dashboard with bed cards, moisture reads, manual watering and bed editing.
- Raspberry Pi setup notes, environment example and backend systemd unit.
- Root-level `mock-dev.sh` script to start the mock backend and frontend together.
- Confirmed bed deletion from the bed settings overlay.
- Irrigation current-status API with remaining runtime and elapsed runtime.
- Manual irrigation cancellation endpoints for a specific bed and the current run.
- Per-bed automatic watering pause after manual cancellation.
- Raspberry Pi rsync deployment script for host `aquapatch`.
- Raspberry Pi preflight/setup script for apt packages, backend venv, frontend build and systemd service installation.
- FastAPI production frontend serving from `frontend/dist`.
- Optional `ufw` opening for AquaPatch during Pi setup when `ufw` is active.
- DHT21 climate reader, mock climate values, `ClimateReading` storage and climate API routes.
- Moisture sensor plausibility warnings with per-bed raw-value thresholds.
- Irrigation run moisture-before/moisture-after fields for more detailed watering logs.
- Daily summary API with per-bed watering, moisture and sensor-warning totals.
- Moisture series and irrigation interval APIs for lightweight dashboard charts.
- Dashboard climate display, daily summary section, sensor warnings and 24h moisture mini charts.

### Changed
- Raspberry Pi deployment now serves the frontend through Nginx on HTTP port `80` so `http://aquapatch/` works without a port suffix.
- FastAPI now runs on port `8000` in the Raspberry Pi systemd deployment, with Nginx proxying `/api`.
- Pi setup now opens `80/tcp` and `8000/tcp` in `ufw` when `ufw` is active.
- Compact dashboard card layout so three beds fit on a wide desktop row and cards stay within narrow mobile viewports.
- Updated default moisture calibration raw values to dry `17750` and wet/moist `7700`, including startup migration for beds still using the old default pair.
- Simplified the dashboard so bed and app settings open in overlays instead of appearing permanently on the main page.
- Replaced symbol/emoji-style dashboard icons with inline Material Design SVG icons.
- Moved calibration values out of the dashboard cards and kept them in each bed's settings overlay.
- Active bed cards now show watering progress, remaining time and an `Abbrechen` action.
- Irrigation locking is global again: only one pump can run at a time.
- MQTT publishing now includes irrigation remaining/elapsed seconds, status, cancellation and automatic watering block topics.
- Reworked the dashboard layout to match the provided clean card-based reference design more closely.
- Updated the systemd service and deployment documentation for `/home/christopher/aquapatch` and user `christopher`.
- Vite dev server now explicitly uses port `5173`.
- Dashboard now auto-refreshes bed, reading, pump, climate and summary data every 10 seconds.
- Header status badges were reduced; MQTT-off is shown only quietly in system/status areas.
- Default first-start beds now match the project defaults: `Hochbeet 1`, `Tomaten`, `Blumen`.
- MQTT publishing now includes climate and moisture sensor status topics.
- Sensor disconnected threshold default is now `5000`.

### Fixed
- Background refresh no longer clears and redraws visible error messages on every interval.

### Implementation Notes
- Mock mode defaults to `HARDWARE_MOCK=true` so development does not require Raspberry Pi hardware.
- Hardware access is isolated in `backend/app/hardware` and service classes; API routes do not toggle GPIO directly.
- Moisture percentage maps each bed's dry calibration value to 0 percent and wet calibration value to 100 percent, including inverted raw ranges.
- Moisture readings below `sensor_disconnected_raw_threshold` are stored as invalid with warning metadata so they are not treated as normal percentages.
- A global async irrigation lock prevents concurrent pump operation; cancellation sets an event that causes the watering loop to exit and the relay to be switched off in `finally`.
- Pi setup keeps `HARDWARE_MOCK=true` by default on newly created `.env` files so first service startup is safe; pass `--real-hardware` when the relay and ADS1115 wiring has been verified.
