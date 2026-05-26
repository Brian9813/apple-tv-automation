# Agent Instructions

This file gives coding agents project-specific context for working on Apple TV
Automation.

## Project Overview

Apple TV Automation is a small local web app for controlling Apple TVs on the
same LAN.

Main files:

- `server.py`: aiohttp web server and API routes
- `apple_tv_service.py`: Apple TV discovery, pairing, connection caching, and
  command execution
- `scheduler.py`: persistent power on/off schedules and scheduler loop
- `static/`: browser UI
- `Dockerfile` and `docker-compose.yml`: container deployment
- `*.service`: systemd service templates

## Important Constraints

- Apple TV discovery depends on local network discovery/mDNS.
- Docker deployment intentionally uses `network_mode: host`.
- Do not replace host networking with bridge networking unless discovery is
  explicitly redesigned and tested.
- Pairing credentials are sensitive. Do not log, commit, or expose
  `.pyatv.conf` or the Docker `data/` directory.
- Schedules are stored in `data/schedules.json`; keep that runtime data out of
  Git.
- Scheduled events use `APPLE_TV_TIME_ZONE`; Docker defaults to
  `America/Chicago`.
- Authentication is not implemented. Treat the app as LAN-only.
- Keep examples and docs generic. Do not add personal paths, usernames,
  hostnames, IP addresses, device names, or pairing credentials.

## Python Runtime

- The app uses `aiohttp` and `pyatv`.
- `pyatv` is async; keep service functions async.
- Keep the connection cache in `apple_tv_service.py` unless replacing it with a
  deliberate connection manager.
- Reusing live Apple TV connections is important for remote-control latency.
- Keep cleanup paths that close cached Apple TV connections on server shutdown.

## UI Guidance

- This is an operational control UI, not a marketing page.
- Keep the first screen focused on device scanning, selection, pairing, and
  remote-control actions.
- Avoid adding decorative UI that slows down common button presses.
- Remote actions should remain one click.

## Deployment

Docker is the preferred Raspberry Pi deployment path.

Expected Docker behavior:

- App runs on port `2332` by default.
- `APPLE_TV_APP_HOST=0.0.0.0`
- `APPLE_TV_APP_PORT=2332`
- `APPLE_TV_TIME_ZONE=America/Chicago`
- `HOME=/data`
- `./data:/data` persists pairing credentials.
- Python dependencies are installed at container startup because some Raspberry
  Pi Docker/libseccomp combinations block Python during image build steps.

The deploy script must not contain personal defaults. Use `-HostName`, `-User`,
`-RemotePath`, or local environment variables:

- `APPLE_TV_DEPLOY_HOST`
- `APPLE_TV_DEPLOY_USER`
- `APPLE_TV_DEPLOY_PATH`
- `APPLE_TV_DEPLOY_OWNER`

The native Python deployment remains supported through
`DEPLOY_RASPBERRY_PI.md`.

## Testing Expectations

After code changes, run:

```bash
python -m py_compile server.py apple_tv_service.py scheduler.py
```

For Docker changes, validate on a machine with Docker:

```bash
docker compose config
docker compose build
```

For behavior changes, manually verify:

- `/api/health` returns `{"ok": true, "status": "ready"}`.
- Device scan returns Apple TVs on the LAN.
- Selecting a device returns supported commands.
- Repeated remote commands reuse the cached connection and remain responsive.
- Pairing still persists across restart/rebuild.
- Scheduled power on/off commands run in the configured timezone and update the
  last run status in the UI.
- The app still works from another device on the LAN when bound to `0.0.0.0`.

## Documentation Rules

- Keep README and deployment docs free of user-specific information.
- Use placeholders such as `<pi-user>`, `<pi-host>`, and
  `<local-project-path>`.
- Do not document real local machine paths or real device names.
