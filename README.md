# Apple TV Automation

A small local web app for discovering and controlling Apple TVs on the same
network.

## Features

- Scan for Apple TVs on the local network
- Pair Apple TVs from the browser
- Send remote commands:
  - Power on/off
  - Directional navigation
  - Select, Menu, Home
  - Play and Pause when supported
- Show basic now-playing metadata when available
- Reuse live Apple TV connections for faster button presses

## Requirements

- Python 3.11 or newer
- Local network access to the Apple TVs
- `pyatv`
- `aiohttp`

For Docker deployment:

- Docker
- Docker Compose

## Run Locally with Python

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python server.py --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/
```

To make the app reachable from other devices on your LAN:

```bash
python server.py --host 0.0.0.0 --port 8000
```

Then open:

```text
http://<server-host-or-ip>:8000/
```

## Run with Docker

Build and run:

```bash
docker compose up -d --build
```

Open:

```text
http://<server-host-or-ip>:8000/
```

The Docker setup uses host networking so Apple TV discovery can work correctly.

## Pairing Data

Pairing credentials are stored by `pyatv`.

Native Python default:

```text
~/.pyatv.conf
```

Docker default:

```text
./data/.pyatv.conf
```

Do not commit or share pairing files. They contain credentials for controlling
paired devices.

## Raspberry Pi Deployment

Use one of these guides:

- `DEPLOY_DOCKER_RASPBERRY_PI.md`
- `DEPLOY_RASPBERRY_PI.md`

Docker is the preferred deployment path for a Raspberry Pi service.

## Configuration

The server accepts command-line arguments:

```bash
python server.py --host 0.0.0.0 --port 8000
```

Or environment variables:

```bash
APPLE_TV_APP_HOST=0.0.0.0
APPLE_TV_APP_PORT=8000
python server.py
```

## Security Notes

- Authentication is not included.
- Keep the app on a trusted local network.
- Do not expose the service directly to the internet.
- Do not publish pairing credentials from `.pyatv.conf` or the Docker `data`
  directory.

## Project Files

```text
apple_tv_service.py                 Apple TV scan, pair, and control logic
server.py                           aiohttp web server and API routes
static/                             Browser UI
Dockerfile                          Container image
docker-compose.yml                  Docker runtime config
apple-tv-automation-docker.service  systemd service for Docker deployment
apple-tv-automation.service         systemd service for native Python deployment
requirements.txt                    Python dependencies
```
