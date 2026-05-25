import asyncio
import logging
import secrets
from dataclasses import dataclass

import pyatv
from pyatv.const import FeatureName, Protocol
from pyatv.interface import FeatureState
from pyatv.storage.file_storage import FileStorage


class IgnoreCompanionPowerStateError(logging.Filter):
    def filter(self, record):
        return not (
            record.name == "pyatv.protocols.companion"
            and record.getMessage().startswith("Could not fetch SystemStatus")
        )


logging.getLogger("pyatv.protocols.companion").addFilter(
    IgnoreCompanionPowerStateError()
)


@dataclass
class PairingSession:
    pairing: object
    device_name: str
    protocol: Protocol
    storage: object


@dataclass
class DeviceConnection:
    atv: object
    device_name: str
    commands: dict
    lock: asyncio.Lock


PAIRING_SESSIONS = {}
CONNECTIONS = {}


def get_storage(loop):
    return FileStorage.default_storage(loop)


async def load_storage():
    loop = asyncio.get_running_loop()
    storage = get_storage(loop)
    await storage.load()
    return storage


async def scan_devices():
    loop = asyncio.get_running_loop()
    storage = await load_storage()
    devices = await pyatv.scan(loop, timeout=5, storage=storage)
    return [serialize_device(device) for device in devices]


def serialize_device(device):
    return {
        "name": device.name,
        "address": str(device.address),
        "identifier": device.identifier,
        "services": [
            {
                "protocol": service.protocol.name,
                "identifier": service.identifier,
                "paired": bool(service.credentials),
            }
            for service in device.services
        ],
    }


async def find_device(identifier, address):
    loop = asyncio.get_running_loop()
    storage = await load_storage()
    devices = await pyatv.scan(
        loop,
        timeout=5,
        identifier=identifier,
        hosts=[address],
        storage=storage,
    )

    for device in devices:
        if device.identifier == identifier and str(device.address) == address:
            return device, storage

    raise RuntimeError("Selected Apple TV was not found.")


def connection_key(identifier, address):
    return f"{identifier}|{address}"


def preferred_protocol(device):
    available_protocols = {service.protocol for service in device.services}

    for protocol in (Protocol.Companion, Protocol.MRP, Protocol.AirPlay):
        if protocol in available_protocols:
            return protocol

    raise RuntimeError("No supported protocol was found for this Apple TV.")


def feature_available(atv, feature_name):
    feature = atv.features.get_feature(feature_name)
    return feature.state == FeatureState.Available


def supported_commands(atv):
    commands = {
        "on": (FeatureName.TurnOn, atv.power.turn_on),
        "off": (FeatureName.TurnOff, atv.power.turn_off),
        "play": (FeatureName.Play, atv.remote_control.play),
        "pause": (FeatureName.Pause, atv.remote_control.pause),
        "up": (FeatureName.Up, atv.remote_control.up),
        "down": (FeatureName.Down, atv.remote_control.down),
        "left": (FeatureName.Left, atv.remote_control.left),
        "right": (FeatureName.Right, atv.remote_control.right),
        "select": (FeatureName.Select, atv.remote_control.select),
        "menu": (FeatureName.Menu, atv.remote_control.menu),
        "home": (FeatureName.Home, atv.remote_control.home),
        "top_menu": (FeatureName.TopMenu, atv.remote_control.top_menu),
    }

    return {
        name: action
        for name, (feature, action) in commands.items()
        if feature_available(atv, feature)
    }


async def list_commands(identifier, address):
    connection = await get_connection(identifier, address)
    return sorted(connection.commands)


async def create_connection(identifier, address):
    device, storage = await find_device(identifier, address)
    loop = asyncio.get_running_loop()
    protocol = preferred_protocol(device)
    atv = await pyatv.connect(device, loop, protocol=protocol, storage=storage)

    return DeviceConnection(
        atv=atv,
        device_name=device.name,
        commands=supported_commands(atv),
        lock=asyncio.Lock(),
    )


async def get_connection(identifier, address):
    key = connection_key(identifier, address)
    connection = CONNECTIONS.get(key)

    if connection:
        return connection

    connection = await create_connection(identifier, address)
    CONNECTIONS[key] = connection
    return connection


async def reconnect(identifier, address):
    close_connection(identifier, address)
    return await get_connection(identifier, address)


def close_connection(identifier, address):
    key = connection_key(identifier, address)
    connection = CONNECTIONS.pop(key, None)

    if connection:
        connection.atv.close()


async def close_all_connections():
    for connection in list(CONNECTIONS.values()):
        connection.atv.close()

    CONNECTIONS.clear()


async def send_command(identifier, address, command):
    connection = await get_connection(identifier, address)

    async with connection.lock:
        action = connection.commands.get(command)

        if not action:
            raise RuntimeError(f"Command is not supported: {command}")

        try:
            await action()
        except Exception:
            connection = await reconnect(identifier, address)
            action = connection.commands.get(command)

            if not action:
                raise RuntimeError(f"Command is not supported: {command}")

            await action()

        return {"command": command, "device": connection.device_name}


async def now_playing(identifier, address):
    connection = await get_connection(identifier, address)

    async with connection.lock:
        try:
            playing = await connection.atv.metadata.playing()
        except Exception:
            connection = await reconnect(identifier, address)
            playing = await connection.atv.metadata.playing()

        return {
            "title": playing.title or "Unknown title",
            "artist": playing.artist or "Unknown artist",
            "album": playing.album or "",
            "media_type": playing.media_type.name,
            "device_state": playing.device_state.name,
            "position": playing.position,
            "total_time": playing.total_time,
        }


async def start_pairing(identifier, address):
    device, storage = await find_device(identifier, address)
    loop = asyncio.get_running_loop()

    for protocol in (Protocol.Companion, Protocol.MRP, Protocol.AirPlay):
        if device.get_service(protocol):
            pairing = await pyatv.pair(device, protocol, loop, storage=storage)
            await pairing.begin()

            session_id = secrets.token_urlsafe(24)
            PAIRING_SESSIONS[session_id] = PairingSession(
                pairing=pairing,
                device_name=device.name,
                protocol=protocol,
                storage=storage,
            )

            return {
                "pairing_id": session_id,
                "device": device.name,
                "protocol": protocol.name,
                "device_provides_pin": pairing.device_provides_pin,
            }

    raise RuntimeError("No pairable protocol was found for this Apple TV.")


async def finish_pairing(pairing_id, pin):
    session = PAIRING_SESSIONS.pop(pairing_id, None)

    if not session:
        raise RuntimeError("Pairing session was not found or has expired.")

    try:
        session.pairing.pin(pin)
        await session.pairing.finish()

        if not session.pairing.has_paired:
            raise RuntimeError("Pairing did not complete.")

        await session.storage.save()

        return {
            "device": session.device_name,
            "protocol": session.protocol.name,
        }
    finally:
        await session.pairing.close()
