# Deploy to Raspberry Pi

These steps run the Apple TV Automation web app on a Raspberry Pi and make it
available to other devices on your local network.

For the Docker deployment, use `DEPLOY_DOCKER_RASPBERRY_PI.md`.

## 1. Copy the app to the Pi

From this Windows machine, copy the folder to the Pi. Replace `pi` and
`raspberrypi.local` if your username or hostname is different.

```powershell
scp -r C:\Users\brian\Documents\Scripts\Python\apple-tv-automation pi@raspberrypi.local:/home/pi/apple-tv-automation
```

If `raspberrypi.local` does not resolve, use the Pi IP address instead.

## 2. Install dependencies on the Pi

SSH into the Pi:

```powershell
ssh pi@raspberrypi.local
```

Then run:

```bash
cd /home/pi/apple-tv-automation
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 3. Test the app manually

Run the server on all network interfaces:

```bash
cd /home/pi/apple-tv-automation
. .venv/bin/activate
python server.py --host 0.0.0.0 --port 8000
```

Open this from another device on the same network:

```text
http://raspberrypi.local:8000/
```

If the hostname does not work, use the Pi IP address:

```text
http://PI_IP_ADDRESS:8000/
```

## 4. Pair Apple TVs

Pairing credentials are stored per machine, so the Pi may need to pair again
even if your Windows machine is already paired.

Open the web app, scan, select an Apple TV, click Pair, and enter the PIN shown
on the Apple TV.

## 5. Install as a startup service

Edit `apple-tv-automation.service` if your Pi username or app path is not:

```text
/home/pi/apple-tv-automation
```

Then install and start the service:

```bash
sudo cp /home/pi/apple-tv-automation/apple-tv-automation.service /etc/systemd/system/apple-tv-automation.service
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
- The service binds to `0.0.0.0:8000`, so any device on your LAN can open it.
- Authentication is not included yet.
