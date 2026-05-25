const statusEl = document.querySelector("#status");
const devicesEl = document.querySelector("#devices");
const scanButton = document.querySelector("#scan-button");
const pairButton = document.querySelector("#pair-button");
const nowButton = document.querySelector("#now-button");
const selectedName = document.querySelector("#selected-name");
const selectedDetails = document.querySelector("#selected-details");
const nowPlaying = document.querySelector("#now-playing");
const pairDialog = document.querySelector("#pair-dialog");
const pairForm = document.querySelector("#pair-form");
const pinInput = document.querySelector("#pin-input");
const pairMessage = document.querySelector("#pair-message");
const commandButtons = [...document.querySelectorAll("[data-command]")];

let devices = [];
let selectedDevice = null;
let availableCommands = new Set();
let activePairingId = null;

function setStatus(message) {
  statusEl.textContent = message;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json();

  if (!response.ok || data.ok === false) {
    throw new Error(data.error || "Request failed");
  }

  return data;
}

function devicePayload() {
  return {
    identifier: selectedDevice.identifier,
    address: selectedDevice.address,
  };
}

function renderDevices() {
  devicesEl.innerHTML = "";

  if (!devices.length) {
    devicesEl.innerHTML = '<p class="device-meta">No Apple TVs scanned yet.</p>';
    return;
  }

  for (const device of devices) {
    const button = document.createElement("button");
    button.className = `device ${
      selectedDevice?.identifier === device.identifier ? "active" : ""
    }`;

    const services = device.services
      .map(
        (service) =>
          `<span class="service ${service.paired ? "paired" : ""}">${
            service.protocol
          } ${service.paired ? "paired" : "not paired"}</span>`
      )
      .join("");

    button.innerHTML = `
      <span class="device-name">${device.name}</span>
      <span class="device-meta">${device.address}</span>
      <span class="service-list">${services}</span>
    `;

    button.addEventListener("click", () => selectDevice(device));
    devicesEl.append(button);
  }
}

function updateCommandButtons() {
  const hasDevice = Boolean(selectedDevice);

  for (const button of commandButtons) {
    const command = button.dataset.command;
    button.disabled = !hasDevice || !availableCommands.has(command);
  }

  pairButton.disabled = !hasDevice;
  nowButton.disabled = !hasDevice;
}

async function refreshCommands() {
  availableCommands = new Set();
  updateCommandButtons();

  if (!selectedDevice) {
    return;
  }

  const data = await api("/api/commands", {
    method: "POST",
    body: JSON.stringify(devicePayload()),
  });

  availableCommands = new Set(data.commands);
  updateCommandButtons();
}

async function selectDevice(device) {
  selectedDevice = device;
  selectedName.textContent = device.name;
  selectedDetails.textContent = `${device.address} · ${device.identifier}`;
  nowPlaying.textContent = "";
  renderDevices();
  setStatus(`Selected ${device.name}`);

  try {
    await refreshCommands();
    setStatus(`Connected to ${device.name}`);
  } catch (error) {
    setStatus(error.message);
  }
}

async function scan() {
  setStatus("Scanning...");
  scanButton.disabled = true;

  try {
    const data = await api("/api/devices");
    devices = data.devices;
    renderDevices();
    setStatus(`Found ${devices.length} device${devices.length === 1 ? "" : "s"}`);
  } catch (error) {
    setStatus(error.message);
  } finally {
    scanButton.disabled = false;
  }
}

async function sendRemoteCommand(command) {
  if (!selectedDevice) {
    return;
  }

  setStatus(`Sending ${command}...`);

  try {
    await api("/api/command", {
      method: "POST",
      body: JSON.stringify({ ...devicePayload(), command }),
    });
    setStatus(`Sent ${command} to ${selectedDevice.name}`);
  } catch (error) {
    setStatus(error.message);
  }
}

async function showNowPlaying() {
  if (!selectedDevice) {
    return;
  }

  setStatus("Reading now playing...");

  try {
    const data = await api("/api/now-playing", {
      method: "POST",
      body: JSON.stringify(devicePayload()),
    });
    const details = [data.artist, data.album, data.media_type, data.device_state]
      .filter(Boolean)
      .join(" · ");
    nowPlaying.textContent = details ? `${data.title} · ${details}` : data.title;
    setStatus(`Updated now playing for ${selectedDevice.name}`);
  } catch (error) {
    setStatus(error.message);
  }
}

async function startPairing() {
  if (!selectedDevice) {
    return;
  }

  setStatus(`Starting pairing for ${selectedDevice.name}...`);

  try {
    const data = await api("/api/pair/start", {
      method: "POST",
      body: JSON.stringify(devicePayload()),
    });

    activePairingId = data.pairing_id;
    pairMessage.textContent = `Enter the PIN shown on ${data.device}. Protocol: ${data.protocol}.`;
    pinInput.value = "";
    pairDialog.showModal();
    pinInput.focus();
    setStatus("Enter the PIN shown on the Apple TV.");
  } catch (error) {
    setStatus(error.message);
  }
}

async function finishPairing(event) {
  event.preventDefault();

  if (!activePairingId) {
    return;
  }

  setStatus("Finishing pairing...");

  try {
    const data = await api("/api/pair/finish", {
      method: "POST",
      body: JSON.stringify({
        pairing_id: activePairingId,
        pin: pinInput.value.trim(),
      }),
    });

    activePairingId = null;
    pairDialog.close();
    setStatus(`Paired ${data.device} with ${data.protocol}`);
    await scan();
  } catch (error) {
    setStatus(error.message);
  }
}

scanButton.addEventListener("click", scan);
pairButton.addEventListener("click", startPairing);
nowButton.addEventListener("click", showNowPlaying);
pairForm.addEventListener("submit", finishPairing);

for (const button of commandButtons) {
  button.addEventListener("click", () => sendRemoteCommand(button.dataset.command));
}

renderDevices();
updateCommandButtons();
scan();
