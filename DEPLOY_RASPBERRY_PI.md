# Native Python Deployment on Raspberry Pi

This deployment runs Apple TV Automation directly with Python on a Raspberry Pi.
For the Docker deployment, use `DEPLOY_DOCKER_RASPBERRY_PI.md`.

## Placeholders

Replace these values in the commands below:

- `<pi-user>`: your Raspberry Pi SSH username
- `<pi-host>`: your Raspberry Pi hostname or IP address
- `<local-project-path>`: the local path to this `apple-tv-automation` folder
- `/opt/apple-tv-automation`: the target install directory on the Pi

## Copy the App

From your local machine:

```bash
scp -r <local-project-path> <pi-user>@<pi-host>:/tmp/apple-tv-automation
```

Then on the Pi:

```bash
sudo rm -rf /opt/apple-tv-automation
sudo mv /tmp/apple-tv-automation /opt/apple-tv-automation
sudo chown -R <pi-user>:<pi-user> /opt/apple-tv-automation
```

## Install Dependencies

On the Pi:

```bash
cd /opt/apple-tv-automation
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Test Manually

Run the server on all network interfaces:

```bash
cd /opt/apple-tv-automation
. .venv/bin/activate
python server.py --host 0.0.0.0 --port 8000
```

Open:

```text
http://<pi-host>:8000/
```

## Pair Apple TVs

Pairing credentials are stored per machine, so the Pi may need to pair again.

Open the web app, scan, select an Apple TV, click Pair, and enter the PIN shown
on the Apple TV.

## Run as a Service

The included `apple-tv-automation.service` assumes:

- App path: `/opt/apple-tv-automation`
- Service user: `appletv`

Create the service user if needed:

```bash
sudo useradd --system --home /opt/apple-tv-automation --shell /usr/sbin/nologin appletv
sudo chown -R appletv:appletv /opt/apple-tv-automation
```

Install and start the service:

```bash
sudo cp /opt/apple-tv-automation/apple-tv-automation.service /etc/systemd/system/apple-tv-automation.service
sudo systemctl daemon-reload
sudo systemctl enable apple-tv-automation
sudo systemctl start apple-tv-automation
```

Check status:

```bash
sudo systemctl status apple-tv-automation
```

View logs:

```bash
journalctl -u apple-tv-automation -f
```

Restart after code changes:

```bash
sudo systemctl restart apple-tv-automation
```

## Notes

- The Pi must be on the same local network as the Apple TVs.
- Apple TV discovery depends on local network discovery/mDNS.
- The service binds to `0.0.0.0:8000`, so devices on the LAN can open it.
- Authentication is not included.
