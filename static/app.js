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
const scheduleForm = document.querySelector("#schedule-form");
const scheduleCommand = document.querySelector("#schedule-command");
const scheduleTime = document.querySelector("#schedule-time");
const addScheduleButton = document.querySelector("#add-schedule-button");
const schedulesEl = document.querySelector("#schedules");
const dayInputs = [...document.querySelectorAll(".day-toggles input")];

let devices = [];
let selectedDevice = null;
let availableCommands = new Set();
let activePairingId = null;
let schedules = [];

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
  addScheduleButton.disabled = !hasDevice;
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
  selectedDetails.textContent = `${device.address} - ${device.identifier}`;
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

function schedulePayload() {
  const days = dayInputs
    .filter((input) => input.checked)
    .map((input) => input.value);

  return {
    name: `${selectedDevice.name} ${scheduleCommand.value === "on" ? "Power On" : "Power Off"}`,
    identifier: selectedDevice.identifier,
    address: selectedDevice.address,
    device_name: selectedDevice.name,
    command: scheduleCommand.value,
    time: scheduleTime.value,
    days,
    enabled: true,
  };
}

function formatDays(days) {
  const labels = {
    sun: "Sun",
    mon: "Mon",
    tue: "Tue",
    wed: "Wed",
    thu: "Thu",
    fri: "Fri",
    sat: "Sat",
  };

  return days.map((day) => labels[day] || day).join(", ");
}

function scheduleAttemptText(schedule) {
  if (!schedule.last_run_key) {
    return "Last run: never";
  }

  if (schedule.last_error) {
    return `Last run: ${schedule.last_run_key} - failed: ${schedule.last_error}`;
  }

  return `Last run: ${schedule.last_run_key} - ok`;
}

function renderSchedules() {
  schedulesEl.innerHTML = "";

  if (!schedules.length) {
    schedulesEl.innerHTML = '<p class="device-meta">No schedules yet.</p>';
    return;
  }

  for (const schedule of schedules) {
    const item = document.createElement("div");
    item.className = "schedule-item";

    const action = schedule.command === "on" ? "Power On" : "Power Off";
    const enabledText = schedule.enabled ? "Enabled" : "Disabled";

    item.innerHTML = `
      <div>
        <div class="schedule-name">${schedule.name}</div>
        <div class="schedule-meta">${schedule.device_name} - ${action} - ${schedule.time} - ${formatDays(schedule.days)} - ${enabledText}</div>
        <div class="schedule-meta ${schedule.last_error ? "schedule-error" : ""}">${scheduleAttemptText(schedule)}</div>
      </div>
      <div class="schedule-actions">
        <button data-schedule-action="run" data-id="${schedule.id}">Run</button>
        <button data-schedule-action="toggle" data-id="${schedule.id}">${schedule.enabled ? "Disable" : "Enable"}</button>
        <button data-schedule-action="delete" data-id="${schedule.id}">Delete</button>
      </div>
    `;

    schedulesEl.append(item);
  }
}

async function loadSchedules() {
  try {
    const data = await api("/api/schedules");
    schedules = data.schedules;
    renderSchedules();
  } catch (error) {
    setStatus(error.message);
  }
}

async function addSchedule(event) {
  event.preventDefault();

  if (!selectedDevice) {
    return;
  }

  const payload = schedulePayload();

  if (!payload.time) {
    setStatus("Choose a schedule time.");
    return;
  }

  if (!payload.days.length) {
    setStatus("Choose at least one schedule day.");
    return;
  }

  setStatus("Adding schedule...");

  try {
    await api("/api/schedules", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setStatus("Schedule added.");
    await loadSchedules();
  } catch (error) {
    setStatus(error.message);
  }
}

async function handleScheduleAction(event) {
  const button = event.target.closest("[data-schedule-action]");

  if (!button) {
    return;
  }

  const id = button.dataset.id;
  const action = button.dataset.scheduleAction;
  const schedule = schedules.find((item) => item.id === id);

  if (!schedule) {
    return;
  }

  try {
    if (action === "run") {
      setStatus(`Running ${schedule.name}...`);
      await api(`/api/schedules/${id}/run`, { method: "POST" });
      setStatus(`Ran ${schedule.name}.`);
      await loadSchedules();
    }

    if (action === "toggle") {
      setStatus("Updating schedule...");
      await api(`/api/schedules/${id}`, {
        method: "PUT",
        body: JSON.stringify({ enabled: !schedule.enabled }),
      });
      setStatus("Schedule updated.");
      await loadSchedules();
    }

    if (action === "delete") {
      setStatus("Deleting schedule...");
      await api(`/api/schedules/${id}`, { method: "DELETE" });
      setStatus("Schedule deleted.");
      await loadSchedules();
    }
  } catch (error) {
    setStatus(error.message);
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
      .join(" - ");
    nowPlaying.textContent = details ? `${data.title} - ${details}` : data.title;
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

    if (data.already_paired) {
      setStatus(`${data.device} is already paired with ${data.protocol}.`);
      await refreshCommands();
      return;
    }

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
scheduleForm.addEventListener("submit", addSchedule);
schedulesEl.addEventListener("click", handleScheduleAction);

for (const button of commandButtons) {
  button.addEventListener("click", () => sendRemoteCommand(button.dataset.command));
}

renderDevices();
updateCommandButtons();
scan();
loadSchedules();
