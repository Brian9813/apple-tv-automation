# Deploy with Docker on Raspberry Pi

This runs Apple TV Automation as a Docker container on the Raspberry Pi.

The container uses host networking because Apple TV discovery depends on local
network discovery/mDNS. Pairing credentials are stored in `./data/.pyatv.conf`
on the Pi so they survive container rebuilds.

## 1. Install Docker on the Pi

SSH into the Pi:

```powershell
ssh pi@raspberrypi.local
```

Install Docker if it is not installed:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker pi
```

Log out and back in after adding the user to the `docker` group.

Check Docker:

```bash
docker --version
docker compose version
```

## 2. Copy the app to the Pi

From this Windows machine:

```powershell
scp -r C:\Users\brian\Documents\Scripts\Python\apple-tv-automation pi@raspberrypi.local:/home/pi/apple-tv-automation
```

If `raspberrypi.local` does not resolve, use the Pi IP address.

## 3. Build and run

On the Pi:

```bash
cd /home/pi/apple-tv-automation
docker compose up -d --build
```

Open:

```text
http://raspberrypi.local:8000/
```

Or use the Pi IP address:

```text
http://PI_IP_ADDRESS:8000/
```

## 4. Pair Apple TVs

Open the web app, scan, select an Apple TV, click Pair, and enter the PIN shown
on the Apple TV.

The pairing file is stored here on the Pi:

```text
/home/pi/apple-tv-automation/data/.pyatv.conf
```

## 5. Run as a systemd service

Install the Docker service:

```bash
sudo cp /home/pi/apple-tv-automation/apple-tv-automation-docker.service /etc/systemd/system/apple-tv-automation.service
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
docker compose logs -f
```

Or:

```bash
journalctl -u apple-tv-automation -f
```

## 6. Update after code changes

Copy the updated folder again, then run:

```bash
cd /home/pi/apple-tv-automation
docker compose up -d --build
```

If using systemd:

```bash
sudo systemctl restart apple-tv-automation
```

## Useful commands

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
- Authentication is not included yet.
