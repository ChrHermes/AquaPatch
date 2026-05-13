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

### Changed
- Simplified the dashboard so bed and app settings open in overlays instead of appearing permanently on the main page.
- Replaced symbol/emoji-style dashboard icons with inline Material Design SVG icons.
- Moved calibration values out of the dashboard cards and kept them in each bed's settings overlay.
- Active bed cards now show watering progress, remaining time and an `Abbrechen` action.
- Irrigation locking is global again: only one pump can run at a time.
- MQTT publishing now includes irrigation remaining/elapsed seconds, status, cancellation and automatic watering block topics.

### Implementation Notes
- Mock mode defaults to `HARDWARE_MOCK=true` so development does not require Raspberry Pi hardware.
- Hardware access is isolated in `backend/app/hardware` and service classes; API routes do not toggle GPIO directly.
- Moisture percentage maps each bed's dry calibration value to 0 percent and wet calibration value to 100 percent, including inverted raw ranges.
- A global async irrigation lock prevents concurrent pump operation; cancellation sets an event that causes the watering loop to exit and the relay to be switched off in `finally`.
