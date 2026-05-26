import argparse
import errno
import logging
import os
from pathlib import Path

from aiohttp import web

from apple_tv_service import (
    close_all_connections,
    finish_pairing,
    list_commands,
    now_playing,
    scan_devices,
    send_command,
    start_pairing,
)
from scheduler import current_run_key, run_schedule, start_scheduler, stop_scheduler


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "static"


async def index(request):
    return web.FileResponse(STATIC_DIR / "index.html")


async def api_health(request):
    return web.json_response({"ok": True, "status": "ready"})


async def api_scan(request):
    return web.json_response({"devices": await scan_devices()})


async def api_commands(request):
    data = await request.json()
    commands = await list_commands(data["identifier"], data["address"])
    return web.json_response({"commands": commands})


async def api_command(request):
    data = await request.json()
    result = await send_command(data["identifier"], data["address"], data["command"])
    return web.json_response({"ok": True, **result})


async def api_now_playing(request):
    data = await request.json()
    return web.json_response(await now_playing(data["identifier"], data["address"]))


async def api_pair_start(request):
    data = await request.json()
    return web.json_response(await start_pairing(data["identifier"], data["address"]))


async def api_pair_finish(request):
    data = await request.json()
    result = await finish_pairing(data["pairing_id"], data["pin"])
    return web.json_response({"ok": True, **result})


async def api_schedules(request):
    return web.json_response({"schedules": await request.app["schedule_store"].list()})


async def api_schedule_create(request):
    data = await request.json()
    schedule = await request.app["schedule_store"].add(data)
    return web.json_response({"ok": True, "schedule": schedule})


async def api_schedule_update(request):
    data = await request.json()
    schedule = await request.app["schedule_store"].update(
        request.match_info["schedule_id"],
        data,
    )
    return web.json_response({"ok": True, "schedule": schedule})


async def api_schedule_delete(request):
    schedule = await request.app["schedule_store"].delete(
        request.match_info["schedule_id"]
    )
    return web.json_response({"ok": True, "schedule": schedule})


async def api_schedule_run(request):
    schedule_id = request.match_info["schedule_id"]
    store = request.app["schedule_store"]
    schedules = await store.list()
    schedule = next(
        (item for item in schedules if item["id"] == schedule_id),
        None,
    )

    if not schedule:
        raise RuntimeError("Schedule was not found.")

    run_key = current_run_key()

    try:
        result = await run_schedule(schedule)
        await store.mark_attempt(schedule_id, run_key, result=result)
        return web.json_response({"ok": True, **result})
    except Exception as error:
        await store.mark_attempt(schedule_id, run_key, error=error)
        raise


@web.middleware
async def error_middleware(request, handler):
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except Exception as error:
        LOGGER.exception("Request failed: %s %s", request.method, request.path)
        return web.json_response({"ok": False, "error": str(error)}, status=500)


def create_app():
    app = web.Application(middlewares=[error_middleware])
    app.on_startup.append(start_scheduler)
    app.on_cleanup.append(cleanup)
    app.router.add_get("/", index)
    app.router.add_static("/static", STATIC_DIR)
    app.router.add_get("/api/health", api_health)
    app.router.add_get("/api/devices", api_scan)
    app.router.add_post("/api/commands", api_commands)
    app.router.add_post("/api/command", api_command)
    app.router.add_post("/api/now-playing", api_now_playing)
    app.router.add_post("/api/pair/start", api_pair_start)
    app.router.add_post("/api/pair/finish", api_pair_finish)
    app.router.add_get("/api/schedules", api_schedules)
    app.router.add_post("/api/schedules", api_schedule_create)
    app.router.add_put("/api/schedules/{schedule_id}", api_schedule_update)
    app.router.add_delete("/api/schedules/{schedule_id}", api_schedule_delete)
    app.router.add_post("/api/schedules/{schedule_id}/run", api_schedule_run)
    return app


async def cleanup(app):
    await stop_scheduler(app)
    await close_all_connections()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Apple TV Automation web app.")
    parser.add_argument("--host", default=os.getenv("APPLE_TV_APP_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port",
        default=int(os.getenv("APPLE_TV_APP_PORT", "8000")),
        type=int,
    )
    args = parser.parse_args()

    try:
        web.run_app(create_app(), host=args.host, port=args.port)
    except OSError as error:
        if error.errno in (errno.EADDRINUSE, 10048):
            print(f"Port {args.port} is already in use.")
            print(f"Open http://{args.host}:{args.port}/ if the app is already running.")
            print("Or run on another port:")
            print("  python server.py --port 8001")
        else:
            raise
