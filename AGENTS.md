# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

INTERCEPT is a web-based Signal Intelligence (SIGINT) platform providing a unified Flask interface for software-defined radio (SDR) tools. It supports pager decoding, 433MHz sensors, ADS-B aircraft tracking, ACARS messaging, WiFi/Bluetooth scanning, satellite tracking, ISS SSTV decoding, AIS vessel tracking, weather satellite imagery (NOAA APT & Meteor LRPT), and Meshtastic mesh networking.

## Common Commands

### Docker (Primary)
```bash
# Build and run (basic profile)
docker compose --profile basic up -d

# Build and run with ADS-B history (Postgres)
docker compose --profile history up -d

# Rebuild after code changes
docker compose --profile basic up -d --build

# Multi-arch build (amd64 + arm64 for RPi)
./build-multiarch.sh
```

### Local Setup (Alternative)
```bash
# First-time setup (interactive wizard with install profiles)
./setup.sh

# Or headless full install
./setup.sh --non-interactive

# Or install specific profiles
./setup.sh --profile=core,weather

# Run with production server (gunicorn + gevent, handles concurrent SSE/WebSocket)
sudo ./start.sh

# Or for quick local dev (Flask dev server)
sudo -E venv/bin/python intercept.py

# Other setup utilities
./setup.sh --health-check      # Verify installation
./setup.sh --postgres-setup    # Set up ADS-B history database
./setup.sh --menu              # Force interactive menu
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_bluetooth.py

# Run with coverage
pytest --cov=routes --cov=utils

# Run a specific test
pytest tests/test_bluetooth.py::test_function_name -v
```

### Linting and Formatting
```bash
# Lint with ruff
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Format with black
black .

# Type checking
mypy .
```

## Architecture

### Entry Points
- `setup.sh` - Menu-driven installer with profile system (wizard, health check, PostgreSQL setup, env configurator, update, uninstall). Sources `.env` on startup via `start.sh`.
- `start.sh` - Production startup script (gunicorn + gevent auto-detection, CLI flags, HTTPS, `.env` sourcing, fallback to Flask dev server)
- `intercept.py` - Direct Flask dev server entry point (quick local development)
- `app.py` - Flask application initialization, global state management, process lifecycle, SSE streaming infrastructure, conditional gevent monkey-patch

### Route Blueprints (routes/)
Each signal type has its own Flask blueprint:
- `pager.py` - POCSAG/FLEX decoding via rtl_fm + multimon-ng
- `sensor.py` - 433MHz IoT sensors via rtl_433
- `adsb.py` - Aircraft tracking via dump1090 (SBS protocol on port 30003)
- `acars.py` - Aircraft datalink messages via acarsdec
- `wifi.py`, `wifi_v2.py` - WiFi scanning (legacy and unified APIs)
- `bluetooth.py`, `bluetooth_v2.py` - Bluetooth scanning (legacy and unified APIs)
- `satellite.py` - Pass prediction using TLE data
- `sstv.py` - ISS SSTV image decoding via slowrx
- `weather_sat.py` - NOAA APT & Meteor LRPT via SatDump
- `ais.py` - AIS vessel tracking and VHF DSC distress monitoring
- `aprs.py` - Amateur packet radio via direwolf
- `rtlamr.py` - Utility meter reading
- `meshtastic_routes.py` - Meshtastic LoRa mesh networking

### Core Utilities (utils/)

**SDR Abstraction Layer** (`utils/sdr/`):
- `SDRFactory` with factory pattern for multiple SDR types (RTL-SDR, LimeSDR, HackRF, Airspy, SDRPlay)
- Each type has a `CommandBuilder` for generating CLI commands

**Bluetooth Module** (`utils/bluetooth/`):
- Multi-backend: DBus/BlueZ primary, fallback for systems without BlueZ
- `aggregator.py` - Merges observations across time
- `tracker_signatures.py` - 47K+ known tracker fingerprints (AirTag, Tile, SmartTag)
- `heuristics.py` - Behavioral analysis for device classification

**TSCM (Counter-Surveillance)** (`utils/tscm/`):
- `baseline.py` - Snapshot "normal" RF environment
- `detector.py` - Compare current scan to baseline, flag anomalies
- `device_identity.py` - Track devices despite MAC randomization
- `correlation.py` - Cross-reference Bluetooth and WiFi observations

**WiFi Utilities** (`utils/wifi/`):
- Platform-agnostic scanner with parsers for airodump-ng, nmcli, iw, iwlist, airport (macOS)
- `channel_analyzer.py` - Frequency band analysis

**Weather Satellite** (`utils/weather_sat.py`):
- Singleton `WeatherSatDecoder` using SatDump CLI for NOAA APT and Meteor LRPT
- Subprocess management with stdout parsing, image watcher via rglob
- Pass prediction using skyfield TLE data

**SSTV Decoder** (`utils/sstv.py`):
- ISS SSTV reception via slowrx with Doppler tracking
- Singleton pattern, image gallery with timestamped filenames

### Key Patterns

**Server-Sent Events (SSE)**: All real-time features stream via SSE endpoints (`/stream_pager`, `/stream_sensor`, etc.). Pattern uses `queue.Queue` with timeout and keepalive messages. Under gunicorn + gevent, each SSE connection is a lightweight greenlet instead of an OS thread.

**Process Management**: External decoders run as subprocesses with output threads feeding queues. Use `safe_terminate()` for cleanup. Global locks prevent race conditions.

**Data Stores**: `DataStore` class with TTL-based automatic cleanup (WiFi: 10min, Bluetooth: 5min, Aircraft: 5min).

**Input Validation**: Centralized in `utils/validation.py` - always validate frequencies, gains, device indices before spawning processes.

### External Tool Integrations

| Tool | Purpose | Integration |
|------|---------|-------------|
| rtl_fm | FM demodulation | Subprocess, pipes to multimon-ng |
| multimon-ng | Pager decoding | Reads from rtl_fm stdout |
| rtl_433 | 433MHz sensors | JSON output parsing |
| dump1090 | ADS-B decoding | SBS protocol socket (port 30003) |
| acarsdec | ACARS messages | Output parsing |
| airmon-ng/airodump-ng | WiFi scanning | Monitor mode, CSV parsing |
| bluetoothctl/hcitool | Bluetooth | Fallback when DBus unavailable |
| slowrx | SSTV decoding | Subprocess with audio pipe |
| SatDump | Weather satellites | CLI live mode, NOAA APT + Meteor LRPT |
| AIS-catcher | AIS vessel tracking | JSON output parsing |
| direwolf | APRS | TNC modem for packet radio |

### Frontend Structure
- **Templates**: `templates/index.html` (main SPA), `templates/partials/modes/*.html` (sidebar panels), `templates/partials/nav.html` (global nav)
- **JS Modules**: `static/js/modes/*.js` - IIFE pattern per mode (e.g., `WeatherSat`, `SSTV`, `Meshtastic`)
- **CSS**: `static/css/modes/*.css` - scoped styles per mode, CSS variables for theming (`--bg-card`, `--accent-cyan`, `--font-mono`)
- **Mode Integration**: Each mode needs entries in `index.html` at ~12 points: CSS include, welcome card, partial include, visuals container, JS include, `validModes` set, `modeGroups` map, classList toggle, `modeNames`, visuals display toggle, titles, and init call in `switchMode()`

### Docker
- `Dockerfile` - Multi-stage build: a Python 3.11 builder compiles SDR tools from source; the runtime copies their binaries/libraries (dump1090, AIS-catcher, slowrx, SatDump, etc.). CMD runs `start.sh` (gunicorn + gevent)
- `docker-compose.yml` - Two profiles: `basic` (standalone) and `history` (with Postgres for ADS-B)
- `build-multiarch.sh` - Multi-arch build script for amd64 + arm64 (RPi5)
- Data persisted via `./data:/app/data` volume mount

### Configuration
- `config.py` - Environment variable support with `INTERCEPT_` prefix (e.g., `INTERCEPT_PORT`, `INTERCEPT_WEATHER_SAT_GAIN`)
- Database: SQLite in `instance/` directory for settings, baselines, history

## Testing Notes

Tests use pytest with extensive mocking of external tools. Key fixtures in `tests/conftest.py`. Mock subprocess calls when testing decoder integration.


## Backlog: fix during the next major Intercept work

New minor items go in the shared backlog, `../ami/docs/backlog.md`, not here; the items below stay until done.

Owner-reported look-and-feel mismatches with AMI (2026-10-24). Not urgent; fold into the next substantial change. Fix them in the AMI visual layer (`static/css/ami-theme.css`, loaded by `partials/ami_head.html`) wherever possible, rather than per page.

- **Native checkboxes everywhere.** First noticed in ADS-B's DISPLAY group (`templates/adsb_dashboard.html` ~line 330: Trails, Rings, Labels, Reach), but every checkbox is the browser's own (only tinted by `accent-color`): about 90 in templates (index 13, adsb_dashboard 12, satellite_dashboard 7, settings-modal 7, modes/tscm 7, pager 6, waterfall 5, morse 5, ais_dashboard 5, wefax 3, and others) plus ones created in JS (`satellite-gps-drone.js`, `core/updater.js`, `tscm.js`, `spy-stations.js`). Give them one square outlined style matching AMI (`appearance:none`, border like AMI's outlined controls, accent tick, focus-visible ring), keeping them real inputs (keyboard and screen readers). Check the hand-styled ones aren't broken: `settings.css` ~286 (already `appearance:none`), `adsb_dashboard.css` 1298/1304, `.bias-t-label` (orange on purpose: it powers the antenna).
- **Alert counter is a red dot.** `.nav-notices-count` (`static/css/core/layout.css` ~1408; markup `partials/nav.html` `#navNoticesCount`) is a red rounded pill with white text. AMI's bell counter is a square amber badge with dark text (`ami/public/css/ami.css` `.bell-n`: `background:var(--warn)`, `color:#1a1000`). Match it. Leave red where it means danger (`.dsc-distress-alert`, `.squawk-alert-banner`, `.badge-danger`, error status dots).
- **Explanations (tooltips).** There's a lot on screen and most of it is unexplained to a newcomer. Today there are ~195 plain `title=` attributes (the browser's delayed, unstyled tooltip, none on touch) and a CSS-only `[data-tooltip]` (`static/css/core/components.css` ~627) used 6 times. Wanted: explanations of what each mode, control, reading and term means and why it matters, in the style of VIGIL's signal tooltips (`VIGIL/dashboard/public/js/tooltips.js`, `signalGuideItems` in core.js: what it means / why it matters / what it doesn't mean; whole rows as targets; hover delay set in Settings; tap-to-explain on touch). Build the tooltip engine once in `ami/shared/ui/` (ADR 0014) so VIGIL and Intercept share it, keep the explanation texts in Intercept, and inside AMI keep them readable aloud like the rest.
- **Satellite dashboard error:** `templates/satellite_dashboard.html` (~line 1881) uses `_gsEventSource`, which is never declared, so the page throws `ReferenceError: _gsEventSource is not defined` (seen in a headless run, 2026-10-24; predates the AMI work). Declare it with the other ground-station state.
- After any of these: run the browser smoke tests in light and dark, desktop and phone, embedded (`?ami=1`) and standalone.

## AMI integration (fork-owned)

- Read `../ami/docs/handoffs/README.md` (the sibling AMI checkout) and open notes before editing when that sibling checkout is available. Never commit another task's changes.
- `routes/ami.py` and `utils/ami.py` implement the opt-in, admin-only read-only service module. `AMI_URL` must be an HTTP(S) origin; `INTERCEPT_AMI_TOKEN_SHA256` contains the service token's SHA-256 digest. Browser sessions never authorize MCP or events.
- Receiver reads use the existing discovery cache; never probe or start a decoder from an AMI read tool. Tool data is explicitly allowlisted. No pager payloads, WiFi/Bluetooth identities, observer coordinates, serial numbers or network receiver addresses enter AMI read tools.
- `instance/ami-events.sqlite` persists decoder-health transitions for 48 hours. Existing stopped processes generate a critical event after 60 seconds; idle modes do not. One WSGI worker owns Intercept's global decoder state. SSE supports `Last-Event-ID`.
- `static/css/ami-theme.css` is a new fork-owned visual layer, loaded once by every document head. Preserve semantic spectrum/map colours and local/offline assets. Embed via `?ami=1`; allow framing only from the configured AMI origin and self. The UI still requires Intercept's own login.
- See `docs/AMI.md` for setup, tests and deployment. No version bumps or live deployment without the owner's authorization; hardware mappings must be explicit. Never add agent attribution to commits.

- Static asset URLs append `-ami1` to the upstream version as a cache key; the displayed release version is unchanged. Change the asset revision when future fork changes would otherwise reuse cached scripts.

- Embedded speech uses `window.InterceptAMI` in ami-bridge.js and AMI’s `ami-speak`/`ami-speech` messages. VoiceAlerts keeps its queue/mute/source choices; automatic speech also requires AMI autoplay. Never synthesize locally inside AMI or expose separate voice/rate/pitch choices there. Standalone speech remains native.

## Account preferences (fork-owned)

- `utils/preferences.py` is the complete localStorage classification and server allowlist; the first head script receives that same registry. Add every new key there, including any dynamic prefix, and choose its scope deliberately. `tests/test_preferences.py` checks literal keys and the layout list.
- SYNCED: observer/module locations, theme/map theme, timezone/hour format, UI tier, default mode/setup/disclaimer, update choice, `intercept_settings`, watch/ignore/mute lists, pager/OOK/waterfall presets, bias-T, Morse/station/receiver preferences and ADS-B range/retention/history choices. There is currently no separate AIS watch-list localStorage key.
- PER-DEVICE: all `LAYOUT_KEYS`/`LAYOUT_PREFIXES`, other view/overlay/autoscroll choices, speaker audio/mute/voice config, debug flags, transient handoff/session/dismissal data, legacy animation keys, `intercept.reach.*` reception caches and the sync owner marker/outbox (`intercept.prefs.pending.<user id>`). Generic storage helpers have no callers; module location keys are explicitly enumerated.
- Account prefs use the session username resolved to `users.id`, never identity headers. NULL rows are deletion markers; first imports cannot overwrite existing rows. Shared HTML heads hydrate before other scripts read storage; global observer-location `.env` persistence remains separate.

## AMI entry and away access (fork-owned)

- `INTERCEPT_AMI_ONLY_AWAY=1` enforces AMI entry for `X-Intercept-Access: away` only with positive `INTERCEPT_TRUSTED_PROXIES`. Caddy must overwrite home/away on every public request; headerless internal health/module calls retain existing behaviour. Never expose the container directly.
- Bearer-only `POST /api/module/session` requires MFA true and `INTERCEPT_AMI_USERS` mapping to an enabled local account; `/ami/enter` consumes a hashed, single-use 60-second pass and replaces the normal session with `via_ami=True`. Local account roles and forced password changes remain authoritative. Keep one worker and never log entry tickets.

## Content-first UI layout (owner rule, 2026-11-02)

Across Intercept, do not hide data behind fixed panes. Information panels must grow with their contents and push following sections down. In ADS-B, expanding selected-aircraft details must move TRACKED AIRCRAFT down instead of clipping the details or forcing scrolling inside a capped details pane. Use a clear page scroll path when full content exceeds the screen; preserve access to every value and action on desktop, mobile and inside AMI. Maps and plots may keep bounded canvas dimensions, but their containers must not obscure adjacent information. Review exceptions for large live streams explicitly. Plan: ../ami/docs/superpowers/plans/2026-11-02-content-first-layout.md.
