## Unreleased

### Added
- Initial FastAPI backend with SQLite, SQLAlchemy models, Pydantic schemas and required REST routes.
- Mock-safe hardware abstraction for Raspberry Pi GPIO relays and ADS1115 moisture readings.
- Irrigation safety service with a single-run lock, maximum duration enforcement and shutdown pump cleanup.
- Optional MQTT service with AquaPatch topic structure for moisture, pump and system state publishing.
- Vue 3, Vite, TypeScript and TailwindCSS dashboard with bed cards, moisture reads, manual watering and bed editing.
- Raspberry Pi setup notes, environment example and backend systemd unit.

### Implementation Notes
- Mock mode defaults to `HARDWARE_MOCK=true` so development does not require Raspberry Pi hardware.
- Hardware access is isolated in `backend/app/hardware` and service classes; API routes do not toggle GPIO directly.
- Moisture percentage maps each bed's dry calibration value to 0 percent and wet calibration value to 100 percent, including inverted raw ranges.
- Only one pump may run at a time because the irrigation service uses an async lock around watering.
