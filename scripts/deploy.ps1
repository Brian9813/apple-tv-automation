param(
    [string]$HostName = $env:APPLE_TV_DEPLOY_HOST,

    [string]$User = $env:APPLE_TV_DEPLOY_USER,

    [string]$RemotePath = $env:APPLE_TV_DEPLOY_PATH,
    [string]$Owner = $env:APPLE_TV_DEPLOY_OWNER,
    [string]$ServiceName = "apple-tv-automation",
    [switch]$InstallService,
    [switch]$ForceInstallService,
    [switch]$SkipBuild,
    [switch]$UseSudo
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

if (-not $HostName) {
    throw "Set -HostName or APPLE_TV_DEPLOY_HOST before deploying."
}

if (-not $RemotePath) {
    $RemotePath = "/opt/apple-tv-automation"
}

if ($UseSudo -and -not $Owner) {
    throw "Set -Owner or APPLE_TV_DEPLOY_OWNER when using -UseSudo."
}

$Remote = $HostName

if ($User) {
    $Remote = "$User@$HostName"
}

$ArchiveName = "apple-tv-automation-deploy.tar.gz"
$LocalArchive = Join-Path ([System.IO.Path]::GetTempPath()) $ArchiveName
$RemoteArchive = "/tmp/$ArchiveName"
$RemoteTemp = "/tmp/apple-tv-automation-deploy"

function Invoke-CheckedCommand {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments

    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

function Invoke-RemoteCommand {
    param(
        [string]$Description,
        [string]$Command,
        [switch]$Interactive
    )

    Write-Host $Description

    if ($Interactive) {
        Invoke-CheckedCommand ssh @("-tt", $Remote, "set -e; $Command")
    }
    else {
        Invoke-CheckedCommand ssh @($Remote, "set -e; $Command")
    }
}

function Wait-ForAppHealth {
    param(
        [int]$TimeoutSeconds = 420
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $healthUrl = "http://127.0.0.1:2332/api/health"
    $attempt = 1

    Write-Host "Waiting for app health check at $healthUrl"

    while ((Get-Date) -lt $deadline) {
        $command = "curl -fsS --max-time 3 '$healthUrl' >/dev/null 2>&1"
        & ssh $Remote $command

        if ($LASTEXITCODE -eq 0) {
            Write-Host "App is ready."
            return
        }

        Write-Host "Still starting... check $attempt"

        if (($attempt % 4) -eq 0) {
            & ssh $Remote "cd '$RemotePath'; docker compose logs --tail=25 apple-tv-automation"
        }

        $attempt += 1
        Start-Sleep -Seconds 10
    }

    & ssh $Remote "cd '$RemotePath'; docker compose logs --tail=120 apple-tv-automation"
    throw "App did not become healthy within $TimeoutSeconds seconds."
}

function Wait-ForDependencyInstall {
    param(
        [int]$TimeoutSeconds = 420
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $attempt = 1

    Write-Host "Waiting for container dependency install to finish before health checks"

    while ((Get-Date) -lt $deadline) {
        $logs = & ssh $Remote "cd '$RemotePath'; docker compose logs --tail=120 apple-tv-automation"

        if ($LASTEXITCODE -ne 0) {
            Write-Host "Container logs are not available yet... check $attempt"
        }
        elseif ($logs -match "Building wheel for miniaudio .* finished with status 'done'" -or
            $logs -match "Successfully built .*miniaudio" -or
            $logs -match "Successfully installed " -or
            $logs -match "Python dependencies are already installed" -or
            $logs -match "Running on http://") {
            Write-Host "Container dependency install has progressed past miniaudio."
            return
        }
        else {
            Write-Host "Dependencies are still installing... check $attempt"

            if (($attempt % 4) -eq 0) {
                $logs | Select-Object -Last 25 | Write-Host
            }
        }

        $attempt += 1
        Start-Sleep -Seconds 10
    }

    & ssh $Remote "cd '$RemotePath'; docker compose logs --tail=120 apple-tv-automation"
    throw "Container dependency install did not finish within $TimeoutSeconds seconds."
}

function Get-RemoteLanAddress {
    $addresses = (& ssh $Remote "hostname -I").Trim().Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries)
    $address = $addresses | Where-Object { $_ -match "^192\.168\." } | Select-Object -First 1

    if (-not $address) {
        $address = $addresses | Where-Object { $_ -match "^\d+\.\d+\.\d+\.\d+$" -and $_ -notmatch "^127\." -and $_ -notmatch "^172\." -and $_ -notmatch "^169\.254\." } | Select-Object -First 1
    }

    return $address
}

function Wait-ForLanHealth {
    param(
        [int]$TimeoutSeconds = 120
    )

    $lanAddress = Get-RemoteLanAddress

    if (-not $lanAddress) {
        Write-Host "Could not determine a LAN IP address for browser health check."
        return
    }

    $healthUrl = "http://${lanAddress}:2332/api/health"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $attempt = 1

    Write-Host "Waiting for browser/LAN health check at $healthUrl"

    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5

            if ($response.StatusCode -eq 200) {
                Write-Host "App is reachable from this machine."
                Write-Host "Open: http://${lanAddress}:2332/"
                return
            }
        }
        catch {
            Write-Host "LAN health check still failing... check $attempt"
        }

        $attempt += 1
        Start-Sleep -Seconds 5
    }

    throw "App is healthy on the Pi but not reachable from this machine at $healthUrl."
}

function Test-RemoteServiceInstalled {
    & ssh $Remote "test -f '/etc/systemd/system/$ServiceName.service'"
    return $LASTEXITCODE -eq 0
}

Write-Host "Packaging $ProjectRoot"

if (Test-Path $LocalArchive) {
    Remove-Item -LiteralPath $LocalArchive -Force
}

Invoke-CheckedCommand tar @(
    "-czf",
    $LocalArchive,
    "--exclude=.git",
    "--exclude=.git/",
    "--exclude=.gitignore",
    "--exclude=.gitattributes",
    "--exclude=.gitmodules",
    "--exclude=__pycache__",
    "--exclude=.venv",
    "--exclude=data",
    "--exclude=*.pyc",
    "-C",
    $ProjectRoot,
    "."
)

Write-Host "Copying package to $Remote"
Invoke-CheckedCommand scp @($LocalArchive, "${Remote}:${RemoteArchive}")

if ($UseSudo) {
    $SyncCommands = @(
        "sudo mkdir -p '$RemotePath'",
        "sudo rsync -a --delete --exclude data '$RemoteTemp/' '$RemotePath/'",
        "sudo chown -R '$Owner':'$Owner' '$RemotePath'"
    )
}
else {
    $SyncCommands = @(
        "mkdir -p '$RemotePath'",
        "rsync -a --delete --exclude data '$RemoteTemp/' '$RemotePath/'"
    )
}

$ExtractCommands = @(
    "rm -rf '$RemoteTemp'",
    "mkdir -p '$RemoteTemp'",
    "tar -xzf '$RemoteArchive' -C '$RemoteTemp'"
)

$ExtractScript = $ExtractCommands -join "; "
Invoke-RemoteCommand "Extracting package on $Remote" $ExtractScript

Invoke-RemoteCommand "Syncing files to $RemotePath" (($SyncCommands + @(
    "mkdir -p '$RemotePath/data'",
    "rm -rf '$RemotePath/.git' '$RemotePath/.gitignore' '$RemotePath/.gitattributes' '$RemotePath/.gitmodules'"
)) -join "; ")

if (-not $SkipBuild) {
    Invoke-RemoteCommand "Building Docker image" "cd '$RemotePath'; docker build -t apple-tv-automation:local ."
    Invoke-RemoteCommand "Starting Docker container" "cd '$RemotePath'; docker compose up -d --no-build"
}
else {
    Invoke-RemoteCommand "Starting Docker container without rebuild" "cd '$RemotePath'; docker compose up -d --no-build"
}

Invoke-RemoteCommand "Showing recent container logs" "cd '$RemotePath'; docker compose logs --tail=80 apple-tv-automation"
Wait-ForDependencyInstall
Wait-ForAppHealth
Wait-ForLanHealth

if ($InstallService -and ($ForceInstallService -or -not (Test-RemoteServiceInstalled))) {
    $ServiceCommands = @(
        "sudo cp '$RemotePath/apple-tv-automation-docker.service' '/etc/systemd/system/$ServiceName.service'",
        "sudo sed -i 's#/opt/apple-tv-automation#$RemotePath#g' '/etc/systemd/system/$ServiceName.service'",
        "sudo systemctl daemon-reload",
        "sudo systemctl enable '$ServiceName'",
        "sudo systemctl restart '$ServiceName'"
    )

    $ServiceScript = $ServiceCommands -join "; "
    Invoke-RemoteCommand "Installing systemd service" $ServiceScript -Interactive
}
elseif ($InstallService) {
    Write-Host "Systemd service already installed. Skipping sudo service installation."
    Write-Host "Use -ForceInstallService if you need to reinstall the service file."
}

Write-Host "Deployment complete."
Write-Host "Open: http://${HostName}:2332/"
