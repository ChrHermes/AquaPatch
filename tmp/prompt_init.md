Erstelle ein neues Projekt from scratch für ein lokales Garten-Bewässerungssystem auf einem Raspberry Pi 4.

Projektziel:
Ein Raspberry Pi 4 soll ein einfaches, lokales und modernes Bewässerungssystem steuern. Das System soll vollständig standalone funktionieren, also ohne Home Assistant, Cloud, Internetverbindung oder Anmeldung. Gleichzeitig soll die Architektur so aufgebaut sein, dass später eine einfache Kopplung an Home Assistant möglich ist, bevorzugt über MQTT und zusätzlich über die bereits vorhandene REST-API.

Hardware:
- Raspberry Pi 4
- ADS1115 ADC per I2C
- 3x Capacitive Soil Moisture Sensor v1.2
- 3x 24-V-DC-Tauchpumpe
- 3x Relaismodul zur Pumpensteuerung
- Pro Beet gilt vorerst eine 1:1:1-Kombination:
  - 1 Beet
  - 1 Feuchtesensor
  - 1 Pumpe / Relaiskanal
- Wir starten mit 3 Beeten.
- Weitere Beete/Zonen sollen später über das Frontend angelegt werden können.
- Füllstandssensor, Schwimmerschalter, Zeitpläne und Wetterdaten werden noch nicht umgesetzt, sollen aber architektonisch später ergänzbar sein.

Tech-Stack:
- Backend: Python 3.11+ mit FastAPI
- Datenbank: SQLite
- ORM: SQLAlchemy 2.x
- API-Schemas: Pydantic v2
- Frontend: Vue 3 + Vite + TypeScript
- Styling: TailwindCSS
- Zielsystem: Raspberry Pi 4 unter Linux
- Hardware-Zugriff:
  - RPi.GPIO für Relais
  - Adafruit ADS1x15 für ADS1115
- Es muss einen Mock-Modus geben, damit die Anwendung auch ohne Raspberry-Pi-Hardware lokal entwickelt und getestet werden kann.

Projektstruktur:
- backend/
- frontend/
- README.md

Backend-Anforderungen:
1. Erstelle eine saubere FastAPI-Anwendung.
2. Verwende SQLite als lokale Datenbank.
3. Verwende SQLAlchemy 2.x für die Datenbankmodelle.
4. Verwende Pydantic v2 für API-Schemas.
5. Implementiere eine klare Schichtenstruktur:
   - api/
   - models/
   - schemas/
   - services/
   - hardware/
   - integrations/
   - core/
6. Hardwarezugriffe dürfen nicht direkt in API-Endpunkten stattfinden.
7. Hardwarezugriff muss über Services gekapselt werden:
   - RelayService
   - MoistureService
   - IrrigationService
8. Es muss einen Mock-Modus geben:
   - HARDWARE_MOCK=true
   - Sensorwerte werden simuliert
   - Relaisaktionen werden nur geloggt
   - Das Frontend und die API sollen trotzdem vollständig nutzbar sein
9. Konfiguration über Umgebungsvariablen:
   - DATABASE_URL
   - HARDWARE_MOCK
   - RELAY_ACTIVE_LOW
   - MAX_WATERING_SECONDS
   - MQTT_ENABLED
   - MQTT_HOST
   - MQTT_PORT
   - MQTT_USERNAME
   - MQTT_PASSWORD
   - MQTT_BASE_TOPIC
10. Logging soll sauber, nachvollziehbar und strukturiert sein.
11. Beim Programmstart sollen Tabellen automatisch erzeugt werden.
12. Beim ersten Start sollen automatisch drei Beispiel-Beete angelegt werden, falls die Datenbank leer ist:
   - Hochbeet 1:
     - relay_pin=17
     - ads_channel=0
     - watering_seconds=120
   - Tomaten:
     - relay_pin=27
     - ads_channel=1
     - watering_seconds=120
   - Blumen:
     - relay_pin=22
     - ads_channel=2
     - watering_seconds=90
13. Die Relaissteuerung muss active-low konfigurierbar sein.
14. Es darf niemals mehr als eine Pumpe gleichzeitig laufen.
15. Jede Bewässerung muss eine maximale Laufzeit haben.
16. Bei Fehlern muss das betroffene Relais sicher ausgeschaltet werden.
17. Beim Beenden oder bei Exceptions sollen alle Relais ausgeschaltet werden.
18. Implementiere für Bewässerungsläufe eine einfache Sperre/Lock-Logik, damit parallele Pumpenstarts verhindert werden.

Datenmodell:

Bed:
- id
- name
- relay_pin
- ads_channel
- moisture_dry_raw
- moisture_wet_raw
- watering_seconds
- enabled
- created_at
- updated_at

MoistureReading:
- id
- bed_id
- raw_value
- voltage
- moisture_percent
- created_at

IrrigationRun:
- id
- bed_id
- duration_seconds
- started_at
- finished_at
- trigger
- success
- message

SystemEvent:
- id
- level
- component
- message
- created_at

Feuchteberechnung:
- Verwende moisture_dry_raw und moisture_wet_raw pro Beet zur Kalibrierung.
- 0 % bedeutet trocken.
- 100 % bedeutet nass.
- Begrenze den berechneten Prozentwert auf 0 bis 100.
- Berücksichtige, dass je nach Sensor die Rohwerte invertiert sein können.
- Implementiere die Berechnung robust und dokumentiert.
- Speichere jeden aktiv abgefragten Messwert als MoistureReading.

API-Endpunkte:
Implementiere mindestens folgende REST-Endpunkte:

Beds:
- GET /api/beds
- POST /api/beds
- GET /api/beds/{bed_id}
- PUT /api/beds/{bed_id}
- DELETE /api/beds/{bed_id}

Moisture:
- GET /api/beds/{bed_id}/moisture
- GET /api/readings/latest
- GET /api/readings?bed_id=1&limit=100

Irrigation:
- POST /api/beds/{bed_id}/water
- GET /api/irrigation/runs
- GET /api/irrigation/runs?bed_id=1&limit=50

System:
- GET /api/system/status
- GET /api/system/events

Verhalten von POST /api/beds/{bed_id}/water:
- Prüfe, ob das Beet existiert.
- Prüfe, ob das Beet enabled ist.
- Prüfe, ob aktuell bereits eine andere Bewässerung läuft.
- Begrenze die Laufzeit auf MAX_WATERING_SECONDS.
- Schalte das Relais ein.
- Warte die konfigurierte oder übergebene Dauer.
- Schalte das Relais sicher aus.
- Speichere einen IrrigationRun.
- Gib einen verständlichen Status zurück.

Optionaler Request-Body für manuelles Bewässern:
- duration_seconds optional
- trigger optional, default "manual"

Frontend-Anforderungen:
1. Erstelle ein schlichtes, modernes Dashboard.
2. Keine Anmeldung.
3. Keine Benutzerverwaltung.
4. Keine Cloud-Funktionen.
5. Das Frontend soll lokal gegen die FastAPI-API arbeiten.
6. Nutze Vue 3, Vite, TypeScript und TailwindCSS.
7. Erstelle eine API-Kapselung in src/api/client.ts.
8. Zeige alle Beete als responsive Karten an.
9. Pro Beet anzeigen:
   - Name
   - aktuelle Bodenfeuchte in Prozent
   - Rohwert
   - Spannung
   - Status: trocken / okay / nass
   - konfigurierte Bewässerungsdauer
   - Pumpe läuft / läuft nicht
   - letzte Messung
   - Button "Jetzt bewässern"
   - Button "Bearbeiten"
10. Beim Bewässern soll der Button deaktiviert sein.
11. Während eines laufenden Requests sollen Ladezustände sichtbar sein.
12. Fehler sollen verständlich angezeigt werden.
13. Es muss möglich sein:
   - neue Beete anzulegen
   - Beete umzubenennen
   - relay_pin zu ändern
   - ads_channel zu ändern
   - watering_seconds zu ändern
   - enabled zu setzen
   - Kalibrierwerte moisture_dry_raw und moisture_wet_raw zu ändern
14. Das UI soll modern, aber simpel sein:
   - helle Oberfläche
   - responsive Grid
   - abgerundete Karten
   - dezente Schatten
   - klare Statusfarben
   - saubere Abstände
   - gut auf Smartphone und Desktop nutzbar
15. Ergänze eine Systemstatus-Karte:
   - Hardware-Mock aktiv/inaktiv
   - Anzahl Beete
   - MQTT aktiv/inaktiv
   - Backend erreichbar
16. Frontend soll initial ohne komplexe Chart-Bibliothek auskommen.
17. Optional darf eine kleine Verlaufsliste der letzten Messwerte angezeigt werden.

Home-Assistant-Fähigkeit:
Das System soll standalone bleiben, aber später sauber an Home Assistant angebunden werden können.

Implementiere dafür eine optionale MQTT-Integrationsschicht im Backend:
- Datei/Modul z. B. integrations/mqtt_service.py
- MQTT muss vollständig deaktivierbar sein über MQTT_ENABLED=false.
- Wenn MQTT_ENABLED=true ist, soll das Backend Sensorwerte und Zustände veröffentlichen.
- Wenn MQTT nicht erreichbar ist, darf die Kernfunktion des Bewässerungssystems nicht abstürzen.
- MQTT-Fehler sollen geloggt werden.
- MQTT soll zunächst einfach und robust sein, keine komplexe Home-Assistant-Custom-Integration.

Verwende folgende MQTT-Topic-Struktur:

Basis:
- MQTT_BASE_TOPIC default: garden_irrigation

Pro Beet:
- garden_irrigation/bed/{bed_id}/name
- garden_irrigation/bed/{bed_id}/moisture_percent
- garden_irrigation/bed/{bed_id}/moisture_raw
- garden_irrigation/bed/{bed_id}/moisture_voltage
- garden_irrigation/bed/{bed_id}/pump/state
- garden_irrigation/bed/{bed_id}/irrigation/last_run
- garden_irrigation/bed/{bed_id}/status

Befehle:
- garden_irrigation/bed/{bed_id}/water/set

System:
- garden_irrigation/system/status
- garden_irrigation/system/hardware_mock
- garden_irrigation/system/mqtt/status

MQTT-Verhalten:
1. Nach jeder Feuchtemessung sollen die Messwerte publiziert werden.
2. Beim Start und Ende einer Bewässerung soll der Pumpenstatus publiziert werden.
3. Beim Start der Anwendung soll ein Systemstatus publiziert werden.
4. Optional: Das Backend darf auf water/set hören.
5. Payload für water/set:
   - entweder einfache Zahl als Sekundenwert
   - oder JSON: {"duration_seconds": 60}
6. Bei MQTT-Befehl muss dieselbe Sicherheitslogik gelten wie bei REST:
   - keine parallelen Pumpen
   - max. Laufzeit beachten
   - Relais sicher ausschalten
7. Implementiere MQTT so, dass es später leicht durch Home Assistant MQTT Discovery erweitert werden kann.
8. Ergänze im README ein Beispiel, wie die MQTT-Topics in Home Assistant verwendet werden könnten.
9. Home Assistant Discovery muss noch nicht vollständig umgesetzt werden, aber die Architektur soll dafür vorbereitet sein.

Backend-Service-Struktur:
Implementiere möglichst folgende Services:

RelayService:
- setup()
- turn_on(bed)
- turn_off(bed)
- turn_all_off()
- get_state(bed)

MoistureService:
- read_raw(bed)
- read_voltage(bed)
- read_percent(bed)
- read_and_store(bed)

IrrigationService:
- water_bed(bed_id, duration_seconds=None, trigger="manual")
- is_any_irrigation_running()
- ensure_all_pumps_off()

MqttService:
- start()
- stop()
- publish_bed_state(bed)
- publish_moisture(bed, reading)
- publish_pump_state(bed, state)
- publish_system_status()
- handle_water_command(...)

SystemService:
- get_status()
- log_event(...)

Hardware-Abstraktion:
Erstelle unter hardware/ mindestens:
- gpio.py
- ads1115.py

Diese Module sollen jeweils Mock-Implementierungen unterstützen.

Sicherheit:
1. Kein GPIO darf beim Import automatisch schalten.
2. Relais werden erst bei App-Start initialisiert.
3. Nach Initialisierung sollen alle Relais aus sein.
4. Bei Fehlern muss das entsprechende Relais ausgeschaltet werden.
5. Bei App-Shutdown sollen alle Relais ausgeschaltet werden.
6. Es darf immer nur eine Pumpe gleichzeitig laufen.
7. Bewässerungsdauer darf MAX_WATERING_SECONDS nicht überschreiten.
8. Validierung:
   - relay_pin muss Integer sein
   - ads_channel muss 0 bis 3 sein
   - watering_seconds muss positiv sein
   - name darf nicht leer sein

Deployment:
1. Erstelle eine README mit vollständiger Setup-Anleitung für Raspberry Pi 4.
2. Beschreibe Installation von:
   - Python-Abhängigkeiten
   - Node/Vite-Abhängigkeiten
   - I2C-Aktivierung auf dem Raspberry Pi
   - ADS1115-Verkabelung
   - Sensorverkabelung
   - Relaisverkabelung
3. Beschreibe grob die Hardware:
   - ADS1115 an I2C
   - Feuchtesensoren an A0, A1, A2
   - Relais an GPIO17, GPIO27, GPIO22
   - Pumpen im 24-V-Lastkreis
4. Weisen ausdrücklich darauf hin:
   - Raspberry Pi GPIOs sind nicht 5-V-tolerant
   - Pumpen dürfen nicht direkt am GPIO hängen
   - 24-V-Pumpen müssen über Relais/MOSFET geschaltet werden
   - Lastkreis und Pi müssen sauber verdrahtet sein
5. Erstelle Beispiel-Dateien:
   - backend/.env.example
   - systemd-Service für Backend
   - optional systemd-Service oder nginx-Hinweis für Frontend
6. Erstelle Startbefehle:
   - Backend lokal starten
   - Frontend lokal starten
   - Frontend builden
7. Das Projekt soll später um folgende Dinge erweiterbar sein:
   - Zeitpläne pro Beet
   - Füllstandssensor JSN-SR04T
   - Schwimmerschalter
   - Wetterdaten/Regen-Sperre
   - Home Assistant MQTT Discovery
   - Diagramme für Feuchteverlauf
   - automatische Bewässerungslogik nach Feuchtegrenzwert

Qualitätsanforderungen:
1. Schreibe lesbaren, wartbaren Code.
2. Verwende Type Hints im Python-Code.
3. Verwende klare Pydantic-Schemas.
4. Verwende keine unnötig komplexe Architektur.
5. Keine Authentifizierung.
6. Keine Docker-Pflicht.
7. Keine Cloud-Dienste.
8. Backend und Frontend sollen getrennt sein.
9. API-Fehler sollen verständliche Fehlermeldungen liefern.
10. README soll praxisnah sein.

Bitte generiere den vollständigen Code für Backend und Frontend inklusive:
- requirements.txt
- package.json
- Tailwind-Konfiguration
- README.md
- .env.example
- Beispiel-systemd-Service
- vollständiger FastAPI-Anwendung
- vollständigem Vue-Frontend
