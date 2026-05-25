# Docker Deployment on Raspberry Pi

This deployment runs Apple TV Automation in Docker on a Raspberry Pi.

The container uses host networking because Apple TV discovery depends on local
network discovery/mDNS. Pairing credentials are stored in `./data/.pyatv.conf`
next to the compose file, so they survive container rebuilds.

## Placeholders

Replace these values in the commands below:

- `<pi-user>`: your Raspberry Pi SSH username
- `<pi-host>`: your Raspberry Pi hostname or IP address
- `<local-project-path>`: the local path to this `apple-tv-automation` folder
- `/opt/apple-tv-automation`: the target install directory on the Pi

## Install Docker

SSH into the Pi:

```bash
ssh <pi-user>@<pi-host>
```

Install Docker if needed:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker <pi-user>
```

Log out and back in after adding the user to the `docker` group.

Check Docker:

```bash
docker --version
docker compose version
```

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

## Build and Run

On the Pi:

```bash
cd /opt/apple-tv-automation
docker compose up -d --build
```

Open:

```text
http://<pi-host>:8000/
```

## Pair Apple TVs

Open the web app, scan, select an Apple TV, click Pair, and enter the PIN shown
on the Apple TV.

The pairing file is stored here on the Pi:

```text
/opt/apple-tv-automation/data/.pyatv.conf
```

## Run as a Service

Install the systemd service:

```bash
sudo cp /opt/apple-tv-automation/apple-tv-automation-docker.service /etc/systemd/system/apple-tv-automation.service
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
cd /opt/apple-tv-automation
docker compose logs -f
```

Or:

```bash
journalctl -u apple-tv-automation -f
```

## Update After Code Changes

Copy the updated folder again, then run:

```bash
cd /opt/apple-tv-automation
docker compose up -d --build
```

If using systemd:

```bash
sudo systemctl restart apple-tv-automation
```

## Useful Commands

Stop:

```bash
docker compose down
```

Restart:

```bash
docker compose restart
```

See running containers:

```bash
docker ps
```

## Notes

- The Pi must be on the same local network as the Apple TVs.
- `network_mode: host` is intentional for Apple TV discovery.
- The web app listens on port `8000`.
- Authentication is not included.
