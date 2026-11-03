# Intercept in AMI

This fork retains the native Flask application and receiver/decoder processes. Its AMI visual layer also applies when used standalone. `?ami=1` embeds it in AMI, with mode navigation and receiver controls still available. Spectrum, map and warning colours retain their meanings. The theme and bridge are local assets and work offline. Static asset URLs use an `-ami1` cache revision so browsers discard scripts cached from the upstream release without a release-version bump.

## Enable the module

Use an HTTPS hostname under the same parent domain as AMI (for example `intercept.example.test` and `ami.example.test`). The browser must be able to send Intercept's own sign-in cookie in AMI's frame. Authentication remains enabled; never use `INTERCEPT_DISABLE_AUTH` for this deployment. AMI can exchange its service token and an MFA-verified, allowlisted username for a one-use browser entry pass (see below).

1. Create a service token locally, outside shell history, using `python3 scripts/ami-token.py`. Store the printed token in your password manager and paste it into AMI's module registration. Store the separately printed digest in Intercept's private environment file. The script neither writes a credential file nor changes running configuration.
2. Configure Intercept, then restart it through its normal deployment:

   ```dotenv
   AMI_URL=https://ami.example.test
   INTERCEPT_AMI_TOKEN_SHA256=<64-character digest>
   ```

   `AMI_URL` must be an origin, with no path, credentials, query or fragment. Missing/invalid `AMI_URL` disables all module routes and preserves same-origin framing. The digest alone cannot authenticate; keep the bearer token secret. Rotate by generating a new pair, updating Intercept's digest and replacing AMI's saved token. Revocation also ends open event streams at their next heartbeat.
3. In **AMI → Modules**, add Intercept with its public HTTPS address. If it shares AMI's Docker network, use `http://intercept:5050` as the internal API address. Otherwise use an explicitly reachable private endpoint. Paste the bearer token. Only administrators may use the module by default; preserve that restriction because aircraft and vessel contacts are not per-user data.
4. Its Overview panel appears automatically. Open Intercept from AMI's app navigation and sign in to Intercept. The existing login, forced password change and standalone URL continue working. Framing is permitted only from self and the configured AMI origin; no token is exposed to the browser bridge.

## Reverse proxy client addresses

Behind exactly one Caddy reverse proxy, set `INTERCEPT_TRUSTED_PROXIES=1` in
Intercept's container environment and restart it. This trusts one (rightmost)
value of `X-Forwarded-For`, `X-Forwarded-Proto` and `X-Forwarded-Host`, so sign-in
logs, lockouts and rate limits use the client address and generated URLs use the
public scheme and host. The default is `0` (off); invalid or negative values also
disable trust. For other proxy chains, set the exact number of trusted hops.
Only enable this when clients cannot reach Intercept directly and every trusted
proxy sets the forwarded headers. This setting counts hops; it does not restrict
trusted proxy IP addresses. For Docker, pass the variable into the container
(e.g. through the stack's `environment` or `env_file`).

## AMI-only browser access away from home

Opt in with `INTERCEPT_AMI_ONLY_AWAY=1`, `INTERCEPT_TRUSTED_PROXIES=1` and
`INTERCEPT_AMI_USERS=alice=operator,bob`. The list contains exact, case-sensitive
AMI usernames; `ami_name=intercept_name` maps to an existing Intercept account,
and an unmapped name uses the same account name. Empty lists deny all entry
passes. Accounts must have `users.enabled=1` (the migration defaults existing
accounts to enabled). Intercept's account role and forced password-change flag
are authoritative; AMI's role never grants an Intercept role.

Caddy must **always overwrite** `X-Intercept-Access` on every public request:
`home` for the home network and `away` for everything else. Never pass through a
client's value. Keep exactly one trusted Caddy, restrict public ingress to it,
and do not expose the container port directly. Proxy trust counts hops, not
source IPs. The header is ignored unless proxy trust is positive and the away
option is `1`; the default remains today's password-login behaviour.

Away requests cannot sign in with a password, including password POSTs. The
login page returns 403 and links to `AMI_URL`. Sessions created by password
login are refused away (browser redirect to login; API/XHR/SSE 401). A session
created through AMI works both away and at home. Home and headerless internal
requests retain their existing behaviour. Module manifest/health, bearer MCP,
events and session issuance retain their existing independent authorization;
Docker-network service calls and the headerless loopback healthcheck need no
access header. Do not enable `INTERCEPT_DISABLE_AUTH`.

The shared AMI entry contract is advertised as `ui.session` and `ui.enter`:

1. AMI's server POSTs to `/api/module/session` over the internal connection with
   its service bearer token and JSON `{"user":"alice","role":"resident","mfa":true}`.
   `role` must be `admin`, `resident` or `viewer`; `mfa` must be the boolean true.
   AMI must derive these values from its authenticated, MFA-verified session.
2. Intercept checks the allowlist and enabled local account and returns
   `{"ticket":"<url-safe random pass>","expiresIn":60}`. Denied eligibility
   returns 403 `{"error":"not allowed"}`. Missing/invalid bearer tokens return
   401. Issuance is limited globally to 30 authenticated attempts per minute
   (429 with `Retry-After: 60`), including denied eligibility checks.
3. AMI opens Intercept's public `/ami/enter?ticket=<pass>`. Intercept consumes
   the ticket once, rechecks the enabled account, replaces the browser session,
   sets `via_ami`, and redirects to `/?ami=1`. Forced password change still
   applies. Invalid, expired or reused passes show a 403 page asking the person
   to open Intercept again from AMI; there is no redirect loop.

Tickets are stored only by hash in worker memory for 60 seconds. A restart
invalidates outstanding passes; keep the existing single gunicorn worker.
Entry responses disable caching and referrer transmission. Configure proxy
access logs to omit/redact the `ticket` query parameter; treat it as a short-lived
login credential. No bearer token is sent to the browser. Serve AMI and Intercept
under the same parent domain so the embedded session cookie works.

## Read-only contract

- Public manifest: `/.well-known/ami-module.json`; sanitized liveness: `/api/module/health`.
- Bearer-protected stateless MCP: `/api/module/mcp` (`initialize`, `ping`, `tools/list`, `tools/call`). Browser sessions never authorize this endpoint, even if standalone auth is disabled.
- Tools: `get_status`, `list_receivers`, `get_contacts` (aircraft/vessels, maximum 50), `get_overview`, `get_space_weather`, `get_recent_events` (sequence cursor, maximum 50), and AMI-only `get_panel`.
- Reads never probe USB/network receivers or start/stop decoders. Receiver data comes from the application's existing discovery cache, and is stale after 60 seconds. An unprobed cache is unknown, not proof of missing hardware.
- Contacts include only allowlisted aviation/maritime fields, the original observation time, and stale flags. No pager messages, WiFi/Bluetooth identities, raw decoded payloads, receiver serials/addresses or observer GPS coordinates are exposed. No transmitted or capture-changing actions are available to the model.
- `get_status` samples the legacy process slots listed in `utils/ami.py`; standalone WiFi/Bluetooth managers and other specialist pipelines remain visible in Intercept itself. Idle is normal and is not reported as a fault. Health is adapter liveness, not a guarantee that all radio equipment is operational.

## Feature discovery and current activity

The public manifest lists 36 features using navigation names, common aliases and their read tools, within AMI contract §10 limits. This includes SPACE WX, ADS-B/AIS, ACARS/VDL2, satellites, mesh and presence modes. AMI refreshes the manifest at its normal health check; no re-link is needed after an approved rollout.

`get_contacts` returns the usual envelope with `data: {contacts, total, fresh, stale, lastMessageAt}`. `contacts` is only the newest requested sample (default 20, maximum 50); counts cover the entire retained store at one snapshot. Fresh means its timestamp is within that store's `max_age`; missing/invalid timestamps count stale. `total` includes stale entries not yet cleaned. `lastMessageAt` and outer `asOf` are the newest valid store observation, not the request time. Outer `stale` remains a boolean, separate from the numeric count inside data. Consumers of the former data list must now use `data.contacts`.

`get_overview` returns one entry per feature, including `state`, `monitored`, `count`, `countScope` and `lastMessageAt`. It reads existing process slots, remote feed flags and already-created client state without calling lazy constructors or status/discovery routes. `monitored:false` means no server-side activity monitor exists for that feature (for example a browser display); its idle value is not evidence of receiver inactivity. A null count/time means unavailable. Aircraft/vessel counts are fresh contacts with total/fresh/stale alongside. WiFi/Bluetooth counts are retained presence entries only. ACARS/VDL2 and MeshCore report retained messages from the last hour (bounded buffers may omit earlier messages); Meshtastic counts stored last-hour messages by a read-only aggregate query. No message contents, device identities, observer coordinates or connection addresses enter the overview.

`get_space_weather` shares SPACE WX's seven existing NOAA SWPC fetchers and TTLs (5-minute current products, 30-minute Kp forecast, hourly flux). Fetches run in parallel within a 20-second tool budget. Results include latest Kp, future 72-hour Kp points, current R/S/G scales, 10.7 cm flux (sfu), solar-wind speed (km/s), Bz (nT), and at most 50 alert titles/issue times. Titles come from a supplied title or the NOAA headline, falling back to the product ID. Message bodies are never returned. `alerts` contains the latest notice per product with an explicit current validity interval; cancelled, expired, future-valid and superseded notices are excluded. Latest notices without a validity end appear separately in `recentAlerts`, so AMI cannot assume they remain active. Both lists contain titles and issue times only.

Each numeric reading includes its NOAA observation time; outer `asOf` is the oldest contributing cache-fetch time. `staleFields` and `missing` distinguish expired/failed products and unavailable readings. Failed refreshes may retain an older snapshot, marked stale. Old observation timestamps also mark Kp/flux/wind/scales stale even after a successful fetch; scales expose their publication time as `scalesAsOf`. Empty/malformed data never becomes an invented zero reading. This tool adds no NOAA URLs or independent refresh schedule and never starts a receiver.

## Embedded speech

Inside AMI, Intercept's existing voice-alert queue sends speech to AMI's origin-checked bridge. AMI chooses the signed-in person's voice, effects, speed and fallback. Automatic alerts require both the chosen Intercept source switches and AMI's automatic read-aloud preference; manual previews use AMI too. Browser speech is used only in standalone Intercept. Embedded voice/rate/pitch controls are hidden in favour of AMI's settings; source switches and mute remain available.

## Health events

`GET /api/module/events` is bearer-protected SSE with `event: ami-event`, durable `id: intercept:<sequence>`, and `Last-Event-ID` replay. History is retained for 48 hours in `instance/ami-events.sqlite`; persist that directory. Unknown/invalid/future cursors are rejected. Reconnecting without a cursor replays the retained journal; AMI applies its own freshness and deduplication rules.

After the first authenticated AMI connection, one monitor samples the existing decoder process slots every 15 seconds. An exited process that remains attached for 60 seconds emits one critical `decoder-health` event; release/restart emits its matching recovery. Deliberately released idle decoders do not alert. State survives restarts, so a persistent fault is not re-announced on every reconnect. AMI handles delivery, subscriptions and quiet hours.

The same monitor reports silence for running feeds as warning `feed-gap` events (an admin-only kind declared in the manifest's `eventKinds`) with `dedupeKey: feed-gap:<mode>`. `FEED_WINDOWS` in `utils/ami.py` defines the windows: ADS-B, ACARS and VDL2 60 minutes; AIS 120 minutes. ADS-B warnings open only from 07:00 inclusive to 23:00 exclusive in the server's local timezone (configure the host/container timezone accordingly). Quiet time includes overnight hours; an already quiet running feed can alert at 07:00. Nighttime does not clear an existing warning. New data clears the matching key, as does stopping/releasing the decoder. Idle/stopped feeds never open gaps. Titles contain the elapsed whole minutes; events contain no decoded contents, callsigns or positions.

A newly observed running feed gets a full quiet window, even if its cached timestamp predates that run. Quiet baselines and open/clear state persist in the same SQLite journal; reopening it does not re-announce an open gap, including when in-memory message timestamps reset. An observed stop followed by a start resets the window. Stops/starts entirely between samples (or while Intercept is down) cannot be distinguished from a continuing run. Detection and recovery occur on the next 15-second sample.

Keep Intercept's existing single WSGI worker: radio state is in process memory, and multiple workers would each see different decoders. This adapter uses no second web server and no node sidecar.

## Deployment and validation

The optional `ami-deploy/stacks/intercept/` configuration is deliberately separate from the existing AMI/VIGIL stacks. Choose the receiver host, devices, DNS and image revision before enabling it. No radio hardware or production stack is configured automatically. Automatic image publication is gated on the fork's successful main-branch CI run and builds `linux/arm64` only, on a native arm64 runner. To add amd64, manually run **Build and Push Docker Image** from `main` with `amd64` ticked; arm64 is always included, so the `main` tag never loses the image tyr runs. Manual runs publish the selected main revision without waiting for a CI run; all action SHA pins are retained.

```sh
python3 -m venv /tmp/intercept-test-env
/tmp/intercept-test-env/bin/pip install -r requirements-dev.txt
/tmp/intercept-test-env/bin/pytest tests/test_ami.py -q
/tmp/intercept-test-env/bin/pytest tests -q --timeout=120 --timeout-method=thread
/tmp/intercept-test-env/bin/ruff check .
```

The tests use temporary databases and mocked decoder state, never production receivers. Existing browser smoke tests exercise all dashboards and modes in dark/light themes and desktop/phone layouts. `tests/smoke/test_ami_embed.py` additionally checks a genuine cross-origin embedded login/navigation flow and bridge origin checks.

## Offline Meteor recordings

In Weather Satellites → Offline Decode (IQ File), select the recording's
transmission type, pick the recording, and press Decode File. Only plain files
placed directly in `data/weather_sat/` are offered or accepted (not links, hidden
files or anything in a sub-folder such as the decoded passes; Refresh lists new ones). Original
Meteor-M2 LRPT 72k and Meteor HRPT are offline-only choices; they do not add live
receiver or scheduling targets.

Stereo PCM I/Q WAV files are decoded as baseband. Their header supplies the sample
rate and 8-bit unsigned or 16-bit signed sample format, overriding the raw-file
rate field. Mono FM audio is not valid Meteor I/Q; unsupported or malformed WAV
files are rejected with an explanation. NOAA APT audio WAV compatibility is retained.
For headerless recordings, enter the actual sample rate, not the LRPT symbol rate.

Owner's test recordings in the persistent `/app/data/weather_sat/` mount:

| Recording | Recording type | Rate read from WAV |
|---|---|---|
| `LRPT_16-29-02_137900kHz.wav` | Meteor-M2 original (LRPT 72k) | 187500 samples/sec |
| `METEOR_HRPT.wav` | Meteor HRPT | 3000000 samples/sec |

Offline Meteor files run with isolated SatDump settings in their own output
folder. Channel images and equation/LUT colour composites are retained; orbital
projections, map overlays, scripted composites and background removal are skipped.
An empty per-run TLE override prevents downloading current orbital data for an
old recording. Global settings and live reception are unchanged. Historical maps
require matching timestamps and orbital data and are not generated by this path.

Verified with Tyr's installed SatDump on 2026-10-26, using temporary output and no
SDR access: without this profile, both recordings could segfault during timestamp
filtering after writing images. With the image-only profile, HRPT completed with
35 PNGs and LRPT with nine, both exit code zero. The HRPT recording is only 4.75
seconds long, so expect a narrow image strip rather than a complete pass.

## Flipper receive-only source

The 433 MHz panel can use an admin-only **Flipper (OOK receive)** source through
an optional Flipper module. Configure `INTERCEPT_FLIPPER_URL=http://flipper:3303`
and `INTERCEPT_FLIPPER_TOKEN` in Intercept's private server environment. The token
is never sent to the browser. The Flipper module stores only its SHA-256 digest,
requires `FLIPPER_RECEIVE_ENABLED=1`, explicit Momentum `mntm-012` acceptance and
its own selected serial device. Close qFlipper while the service owns that port.

Choose a frequency in 300–348, 387–464 or 779–928 MHz and a 1–30 second duration.
These are bounded internal-CC1101/OOK650 receive sessions. Observations are decoded
CLI text, explicitly separate from rtl_433 sensor cards. There is no IQ,
waterfall, RSSI, arbitrary preset, transmit, replay or saved-file-content access.
Metadata monitoring and receiving share one serial lease in the module.

Stopping, Stop All and shutdown request cancellation. A transport failure is
reported as unconfirmed rather than as stopped; the module also enforces its
own deadline. Observation replay stays bounded and requires a currently enabled
admin account. Payloads stay out of shared sensor SSE, recording and MQTT;
only lifecycle status enters the shared sensor stream. HTTP redirects, ambient proxies and oversized/slow responses are
refused by the server-side bridge. Short captures remain visible after stopping.

Before moving the Flipper to Tyr, replace Intercept's broad USB-bus mapping with
an explicitly verified RTL-SDR USB node. Map the Flipper's by-id serial device
only to the Flipper service, with its actual host device GID. See the sibling
ami-deploy Flipper rollout instructions. A replug can change USB paths; verify
identity and refresh mappings before restarting. Feature branches are not a
claim of live hardware validation or deployment.

## Repository name

The fork is `Morrolan/ami-module-intercept`, checked out beside AMI as `ami-module-intercept`. Git remotes should use `git@github.com:Morrolan/ami-module-intercept.git`. New builds publish `ghcr.io/morrolan/ami-module-intercept:sha-<tested-commit>`. Preserve the existing pinned old-package image for rollback until the owner approves a Portainer redeploy. The product name, module id, Compose service and public hostname remain Intercept/`intercept`.

## Opt-in RTL USB hotplug recovery

The companion deployment repo provides an optional identity-checked host publisher and `stacks/intercept/portainer-hotplug.yml`. It exposes only a private directory containing the selected RTL receiver; the Intercept container cannot create device nodes and never sees the host's full USB bus. Follow that repo's reviewed installation, migration and rollback instructions; an initial owner-approved rollout is required.

`INTERCEPT_SDR_HOTPLUG_STATE` enables the receive supervisor only in that stack. Commands are wrapped at the final process-spawn boundary, after tool-path and argument changes. Supported continuous local device0 tools:rtl_fm,rtl_433,rtl_tcp,dump1090/dump1090-fa/readsb,AIS-catcher,acarsdec,dumpvdl2, and rtl_sdr only when streaming to stdout without a finite sample count. Network/Soapy/non-RTL commands, explicit file captures, finite rtl_433 timeouts, timed scanner hops, SatDump jobs, radiosonde auto_rx and third-party pipelines retain their existing behavior. A failed finite job must be restarted through the UI; it is never automatically overwritten. A companion consumer which exits on network disconnect may likewise need its normal Start action.

The supervisor keeps stdin/stdout/stderr ownership stable across USB loss, preserves binary output, and resumes the same argv only after unavailable/changed receiver state. Its child is stopped before replacement; user Stop, worker death and cleanup prevent resurrection. Genuine decoder failure with unchanged receiver state propagates normally. Missing/malformed/stale host heartbeat fails closed. There is no discovery, USB reset, transmission or arbitrary-command HTTP endpoint in this helper.

AMI's existing passive status/overview expose only enabled/available hotplug flags, and its panel shows Waiting for receiver when appropriate. No serial, USB path, generation, observer coordinates or decoded payloads enter AMI tools. A supervised process can remain alive while waiting; the availability flag distinguishes that from active reception. Feature-off command construction and process lifecycle are unchanged.
