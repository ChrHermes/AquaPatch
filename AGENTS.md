# AGENTS.md

## Project Context

This repository contains a local, standalone garden irrigation system for a Raspberry Pi 4.

The system controls multiple garden beds or plant zones. Each bed is expected to have:

- one 24 V DC water pump
- one relay channel for pump control
- one capacitive soil moisture sensor
- one ADS1115 ADC channel

The initial setup starts with three beds, but the software must support adding more beds later.

The application should run locally on a Raspberry Pi 4 and must not require cloud services, user accounts, authentication, or Home Assistant. However, the architecture should remain Home Assistant friendly, preferably through MQTT and REST APIs.

The working project name is:

```text
AquaPatch
```

## Core Goals

Build a simple, reliable and maintainable irrigation dashboard.

The system should provide:

- a FastAPI backend
- a SQLite database
- a Vue 3 + Vite + TypeScript frontend
- TailwindCSS styling
- Raspberry Pi GPIO relay control
- ADS1115 soil moisture readings
- mock mode for local development without Raspberry Pi hardware
- optional MQTT integration for future Home Assistant usage
- clear documentation
- safe pump control

## Preferred Tech Stack

### Backend

- Python 3.11+
- FastAPI
- SQLAlchemy 2.x
- Pydantic v2
- SQLite
- RPi.GPIO
- Adafruit ADS1x15
- paho-mqtt, if MQTT support is implemented

### Frontend

- Vue 3
- Vite
- TypeScript
- TailwindCSS

### Target Hardware

- Raspberry Pi 4
- ADS1115 via I2C
- Capacitive Soil Moisture Sensor v1.2
- Relay modules
- 24 V DC pumps

## Repository Structure

Use this structure unless there is a strong reason to change it:

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── hardware/
│   │   └── integrations/
│   ├── requirements.txt
│   ├── .env.example
│   └── systemd/
│
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.*
│
├── README.md
├── AGENTS.md
└── CHANGELOG.md
```

If `CHANGELOG.md` does not exist yet, create it once the first meaningful implementation step is done.

## Development Principles

### Keep the System Standalone

The application must work without:

- Home Assistant
- internet access
- cloud services
- user login
- Docker
- external databases

Home Assistant support should be optional and must not be required for core operation.

### Keep Hardware Access Isolated

Do not access GPIO, ADS1115 or MQTT directly from API routes.

Use services and hardware abstraction layers.

Preferred service names:

```text
RelayService
MoistureService
IrrigationService
SystemService
MqttService
```

Preferred hardware modules:

```text
hardware/gpio.py
hardware/ads1115.py
```

### Mock Mode Is Required

The application must support a mock mode.

Use an environment variable:

```text
HARDWARE_MOCK=true
```

In mock mode:

- no real GPIO setup should be required
- no ADS1115 hardware should be required
- relay actions should be logged only
- sensor values should be simulated
- the frontend and backend should remain fully usable

Mock mode should be the safe default for local development.

### Safety Rules

Pump control must be conservative and safe.

Always follow these rules:

- never run more than one pump at the same time
- enforce a maximum watering duration
- turn relays off in `finally` blocks
- turn all relays off during application shutdown
- do not toggle GPIO during module import
- initialize GPIO only during application startup
- keep relay active-low behavior configurable
- validate GPIO pins and ADS channels
- fail safely if hardware access fails

Configuration values should include:

```text
DATABASE_URL
HARDWARE_MOCK
RELAY_ACTIVE_LOW
MAX_WATERING_SECONDS
MQTT_ENABLED
MQTT_HOST
MQTT_PORT
MQTT_USERNAME
MQTT_PASSWORD
MQTT_BASE_TOPIC
```

## Documentation Requirements

Documentation is part of the implementation, not a separate afterthought.

Whenever code behavior, setup steps, configuration, hardware wiring, API routes or frontend usage changes, update the documentation in the same change.

### README.md Must Always Be Current

Keep `README.md` accurate and useful.

It should include:

- project purpose
- current feature list
- hardware overview
- wiring overview
- backend setup
- frontend setup
- mock mode usage
- Raspberry Pi setup notes
- I2C enablement notes
- environment variables
- API overview
- MQTT/Home Assistant notes, if implemented
- systemd deployment notes, if available
- known limitations
- next planned improvements

Do not leave outdated instructions in the README.

If a feature is planned but not implemented, clearly mark it as planned.

Use wording such as:

```text
Planned:
```

or

```text
Not implemented yet:
```

Do not imply that unfinished functionality already works.

### CHANGELOG.md

Maintain a `CHANGELOG.md` once development begins.

Use short, clear entries.

Example:

```md
## Unreleased

### Added
- Initial FastAPI backend structure.
- SQLite models for beds, moisture readings and irrigation runs.
- Mock hardware mode.

### Changed
- Updated README with Raspberry Pi setup notes.

### Fixed
- Ensured relays are switched off after failed irrigation runs.
```

### Implementation Notes

Document important implementation decisions either in `README.md` or in a dedicated section inside `CHANGELOG.md`.

Examples:

- why mock mode exists
- why only one pump may run at a time
- why hardware access is isolated
- how moisture percentage is calculated
- how relay active-low logic works
- how MQTT topics are structured

## Codex Work Logging

Whenever Codex performs a meaningful development step, it should document what was done.

At minimum, after each implementation phase:

1. update `README.md`
2. update `CHANGELOG.md`
3. summarize changed files in the final response
4. mention anything that still needs manual testing on Raspberry Pi hardware

The final response after a coding task should include:

```text
Changed files:
- ...

What was implemented:
- ...

How to test:
- ...

Notes / limitations:
- ...
```

## Backend Requirements

### Initial Default Beds

If the database is empty, seed these default beds:

```text
Hochbeet 1:
  relay_pin: 17
  ads_channel: 0
  watering_seconds: 120

Tomaten:
  relay_pin: 27
  ads_channel: 1
  watering_seconds: 120

Blumen:
  relay_pin: 22
  ads_channel: 2
  watering_seconds: 90
```

### Required Models

Implement at least:

```text
Bed
MoistureReading
IrrigationRun
SystemEvent
```

### Required API Endpoints

Implement at least:

```text
GET    /api/beds
POST   /api/beds
GET    /api/beds/{bed_id}
PUT    /api/beds/{bed_id}
DELETE /api/beds/{bed_id}

GET    /api/beds/{bed_id}/moisture
GET    /api/readings/latest
GET    /api/readings?bed_id=1&limit=100

POST   /api/beds/{bed_id}/water
GET    /api/irrigation/runs
GET    /api/irrigation/runs?bed_id=1&limit=50

GET    /api/system/status
GET    /api/system/events
```

### Moisture Calculation

Each bed should have calibration values:

```text
moisture_dry_raw
moisture_wet_raw
```

Calculate moisture percentage from these values.

Rules:

- 0 % means dry
- 100 % means wet
- clamp the result to 0–100 %
- handle inverted sensor values robustly
- store actively requested readings as `MoistureReading`

## Frontend Requirements

The frontend should be simple, modern and responsive.

Required UI features:

- dashboard with cards for all beds
- display current moisture percentage
- display raw value and voltage
- display bed status: dry / okay / wet
- display pump status
- display watering duration
- button to water a bed manually
- form/dialog to add a bed
- form/dialog to edit a bed
- system status card
- clear error messages
- loading states

The UI should use:

- rounded cards
- subtle shadows
- clear spacing
- modern but simple layout
- responsive grid
- no authentication screens

## MQTT / Home Assistant Readiness

MQTT support should be optional.

The system must work without MQTT.

If MQTT is implemented, use this topic structure:

```text
garden_irrigation/bed/{bed_id}/name
garden_irrigation/bed/{bed_id}/moisture_percent
garden_irrigation/bed/{bed_id}/moisture_raw
garden_irrigation/bed/{bed_id}/moisture_voltage
garden_irrigation/bed/{bed_id}/pump/state
garden_irrigation/bed/{bed_id}/irrigation/last_run
garden_irrigation/bed/{bed_id}/status

garden_irrigation/bed/{bed_id}/water/set

garden_irrigation/system/status
garden_irrigation/system/hardware_mock
garden_irrigation/system/mqtt/status
```

MQTT errors must not crash the irrigation system.

Home Assistant MQTT Discovery may be added later, but it is not required for the first implementation.

## Hardware Notes

### Raspberry Pi GPIO

Raspberry Pi GPIOs are not 5 V tolerant.

Do not connect 5 V signals directly to GPIO pins.

### Relays

Relays may be active-low.

Make this configurable:

```text
RELAY_ACTIVE_LOW=true
```

### Pumps

24 V DC pumps must not be powered from Raspberry Pi GPIO pins.

Use relays or MOSFET modules and a suitable 24 V power supply.

### ADS1115

The ADS1115 is connected via I2C.

Soil moisture sensors connect to ADS1115 analog inputs A0–A3.

DRY raw value is 17750
MOIST raw value is 7700

## Testing Expectations

When adding or changing backend code:

- run Python syntax checks where possible
- ensure imports resolve
- ensure FastAPI can start
- test mock mode first
- avoid requiring Raspberry Pi hardware in development mode

When adding or changing frontend code:

- run package install/build checks where possible
- ensure TypeScript types are valid
- ensure API client paths match backend routes

When changing documentation:

- verify commands and paths match the actual repository layout

## Manual Testing Checklist

Use this checklist once hardware is connected:

```text
[ ] Raspberry Pi boots and application starts
[ ] I2C is enabled
[ ] ADS1115 is detected
[ ] moisture values can be read from all configured channels
[ ] each relay can be switched individually
[ ] relay active-low setting is correct
[ ] each pump starts only for its assigned bed
[ ] only one pump can run at a time
[ ] pump stops after configured duration
[ ] pump stops after API error or interruption
[ ] frontend shows current bed states
[ ] manual watering works from frontend
[ ] README matches the actual setup
```

## Style Guidelines

- Prefer clear, boring, maintainable code.
- Avoid overengineering.
- Use type hints in Python.
- Use explicit names.
- Keep API responses consistent.
- Keep frontend components small and readable.
- Do not introduce authentication unless explicitly requested.
- Do not introduce Docker unless explicitly requested.
- Do not introduce cloud dependencies.
- Keep German user-facing labels acceptable in the frontend.
- Code comments may be English.

## Final Reminder for Codex

After every meaningful change:

1. update `README.md`
2. update `CHANGELOG.md`
3. keep setup instructions accurate
4. mention hardware assumptions
5. document what was changed
6. leave the project in a runnable state
