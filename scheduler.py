import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apple_tv_service import send_command


DATA_DIR = Path(os.getenv("APPLE_TV_DATA_DIR", os.getenv("HOME", ".")))
SCHEDULE_FILE = DATA_DIR / "schedules.json"
DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
TIME_ZONE_NAME = os.getenv("APPLE_TV_TIME_ZONE", os.getenv("TZ", "America/Chicago"))
LOGGER = logging.getLogger(__name__)

try:
    TIME_ZONE = ZoneInfo(TIME_ZONE_NAME)
except ZoneInfoNotFoundError:
    TIME_ZONE = None
    LOGGER.warning("Unknown time zone %s. Falling back to container local time.", TIME_ZONE_NAME)


class ScheduleStore:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.schedules = []

    async def load(self):
        async with self.lock:
            DATA_DIR.mkdir(parents=True, exist_ok=True)

            if not SCHEDULE_FILE.exists():
                self.schedules = []
                return

            with SCHEDULE_FILE.open("r", encoding="utf-8") as file:
                self.schedules = json.load(file)

    async def save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        temp_file = SCHEDULE_FILE.with_suffix(".json.tmp")

        with temp_file.open("w", encoding="utf-8") as file:
            json.dump(self.schedules, file, indent=2)

        temp_file.replace(SCHEDULE_FILE)

    async def list(self):
        async with self.lock:
            return sorted(self.schedules, key=lambda item: (item["time"], item["name"]))

    async def add(self, data):
        schedule = validate_schedule(data)
        schedule["id"] = uuid.uuid4().hex
        schedule["enabled"] = data.get("enabled", True)
        schedule["last_run_key"] = None
        schedule["last_result"] = None
        schedule["last_error"] = None

        async with self.lock:
            self.schedules.append(schedule)
            await self.save()

        return schedule

    async def update(self, schedule_id, data):
        async with self.lock:
            schedule = find_schedule(self.schedules, schedule_id)

            for key in (
                "name",
                "identifier",
                "address",
                "device_name",
                "command",
                "time",
                "days",
                "enabled",
            ):
                if key in data:
                    schedule[key] = data[key]

            updated = validate_schedule(schedule)
            updated["id"] = schedule_id
            updated["last_run_key"] = schedule.get("last_run_key")
            updated["last_result"] = schedule.get("last_result")
            updated["last_error"] = schedule.get("last_error")

            index = self.schedules.index(schedule)
            self.schedules[index] = updated
            await self.save()

        return updated

    async def delete(self, schedule_id):
        async with self.lock:
            schedule = find_schedule(self.schedules, schedule_id)
            self.schedules.remove(schedule)
            await self.save()

        return schedule

    async def mark_attempt(self, schedule_id, run_key, result=None, error=None):
        async with self.lock:
            schedule = find_schedule(self.schedules, schedule_id)
            schedule["last_run_key"] = run_key
            schedule["last_result"] = result
            schedule["last_error"] = str(error) if error else None
            await self.save()


def find_schedule(schedules, schedule_id):
    for schedule in schedules:
        if schedule["id"] == schedule_id:
            return schedule

    raise RuntimeError("Schedule was not found.")


def validate_schedule(data):
    schedule = {
        "name": str(data.get("name") or "").strip(),
        "identifier": str(data.get("identifier") or "").strip(),
        "address": str(data.get("address") or "").strip(),
        "device_name": str(data.get("device_name") or "").strip(),
        "command": str(data.get("command") or "").strip().lower(),
        "time": str(data.get("time") or "").strip(),
        "days": [str(day).lower() for day in data.get("days", [])],
        "enabled": bool(data.get("enabled", True)),
    }

    if not schedule["identifier"] or not schedule["address"]:
        raise RuntimeError("Schedule requires an Apple TV.")

    if schedule["command"] not in ("on", "off"):
        raise RuntimeError("Schedule command must be on or off.")

    try:
        datetime.strptime(schedule["time"], "%H:%M")
    except ValueError as error:
        raise RuntimeError("Schedule time must use HH:MM format.") from error

    if not schedule["days"] or any(day not in DAYS for day in schedule["days"]):
        raise RuntimeError("Schedule requires at least one valid day.")

    if not schedule["name"]:
        action = "Power On" if schedule["command"] == "on" else "Power Off"
        schedule["name"] = f"{schedule['device_name']} {action}".strip()

    return schedule


def current_run_key():
    now = datetime.now(TIME_ZONE) if TIME_ZONE else datetime.now()
    return f"{now.date().isoformat()} {now.strftime('%H:%M')}"


async def run_schedule(schedule):
    return await send_command(
        schedule["identifier"],
        schedule["address"],
        schedule["command"],
    )


async def scheduler_loop(app):
    store = app["schedule_store"]
    LOGGER.info(
        "Scheduler started with time zone %s and schedule file %s",
        TIME_ZONE_NAME if TIME_ZONE else "container local time",
        SCHEDULE_FILE,
    )

    while True:
        now = datetime.now(TIME_ZONE) if TIME_ZONE else datetime.now()
        day = now.strftime("%a").lower()
        current_time = now.strftime("%H:%M")
        run_key = current_run_key()

        for schedule in await store.list():
            if not schedule.get("enabled", True):
                continue

            if schedule["time"] != current_time or day not in schedule["days"]:
                continue

            if schedule.get("last_run_key") == run_key:
                continue

            LOGGER.info(
                "Running schedule %s: %s %s for %s",
                schedule["id"],
                schedule["device_name"],
                schedule["command"],
                run_key,
            )

            try:
                result = await run_schedule(schedule)
                await store.mark_attempt(schedule["id"], run_key, result=result)
                LOGGER.info("Schedule %s completed successfully.", schedule["id"])
            except Exception as error:
                await store.mark_attempt(schedule["id"], run_key, error=error)
                LOGGER.exception("Schedule %s failed.", schedule["id"])

        await asyncio.sleep(20)


async def start_scheduler(app):
    store = ScheduleStore()
    await store.load()
    app["schedule_store"] = store
    app["scheduler_task"] = asyncio.create_task(scheduler_loop(app))


async def stop_scheduler(app):
    task = app.get("scheduler_task")

    if task:
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass
