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

Do not commit real hostnames, usernames, IP addresses, local paths, or pairing
files. Keep those values in your shell environment or pass them as command-line
arguments.

## Deploy Script

From this project folder on your local machine:

```powershell
.\deploy.cmd -HostName <pi-host> -User <pi-user>
```

You can also configure the deploy target with local environment variables:

```powershell
$env:APPLE_TV_DEPLOY_HOST = "<pi-host>"
$env:APPLE_TV_DEPLOY_USER = "<pi-user>"
$env:APPLE_TV_DEPLOY_PATH = "/opt/apple-tv-automation"
.\deploy.cmd
```

Install the systemd service once:

```powershell
.\deploy.cmd -HostName <pi-host> -User <pi-user> -InstallService
```

Normal deploys after that do not need `-InstallService`.

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
docker build -t apple-tv-automation:local .
docker compose up -d --no-build
```

Open:

```text
http://<pi-host>:2332/
```

The app exposes a health check at:

```text
http://<pi-host>:2332/api/health
```

## Pair Apple TVs

Open the web app, scan, select an Apple TV, click Pair, and enter the PIN shown
on the Apple TV.

The pairing file is stored here on the Pi:

```text
/opt/apple-tv-automation/data/.pyatv.conf
```

Schedules are stored here:

```text
/opt/apple-tv-automation/data/schedules.json
```

The Docker configuration sets `APPLE_TV_TIME_ZONE=America/Chicago` by default
so scheduled events use Central time. Change that environment variable in
`docker-compose.yml` if the Pi should use a different timezone.

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
docker build -t apple-tv-automation:local .
docker compose up -d --no-build
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

## Troubleshooting

If Docker build fails with an error like:

```text
PermissionError: [Errno 1] Operation not permitted
```

while Python is importing `time` or `logging`, the Pi likely has an older
Docker/libseccomp stack that blocks newer Linux syscalls inside containers.

Update the Pi packages and Docker, then try the deploy again:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y libseccomp2
sudo reboot
```

After reboot:

```bash
cd /opt/apple-tv-automation
docker compose up -d --build
```

## Notes

- The Pi must be on the same local network as the Apple TVs.
- `network_mode: host` is intentional for Apple TV discovery.
- Python dependencies are installed into `./data/.venv` when the container
  starts, not during `docker build`. The virtual environment is reused on later
  deploys until `requirements.txt` or the container Python version changes.
  This avoids Raspberry Pi Docker builds that block Python time syscalls during
  image build steps.
- `seccomp=unconfined` is applied to the running container for the same reason.
- The Docker deployment listens on port `2332`.
- Scheduled commands show their last run result in the browser.
- Authentication is not included.
