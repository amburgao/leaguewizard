"""Core module for LeagueWizard, handling LCU connection and event processing.

This module establishes a connection to the League of Legends client (LCU) via
WebSocket, retrieves necessary authentication details, and dispatches incoming
game events to the `on_message` handler. It also manages the system tray icon.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import ssl
import sys
import tempfile
import urllib
from pathlib import Path
from typing import Any

import aiohttp
import psutil
import websockets
from infi.systray import SysTrayIcon  # type: ignore[import-untyped]
from loguru import logger

from leaguewizard import config
from leaguewizard.callback_handler import on_message
from leaguewizard.exceptions import LeWizardGenericError

RIOT_CERT = Path(tempfile.gettempdir(), "riotgames.pem")
if not RIOT_CERT.exists():
    urllib.request.urlretrieve(
        "https://static.developer.riotgames.com/docs/lol/riotgames.pem", RIOT_CERT
    )

context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.load_verify_locations(RIOT_CERT)
context.check_hostname = False


def _lcu_lockfile(league_exe: str) -> Path:
    if not Path(league_exe).exists():
        msg = "LeagueClient.exe not running or not found."
        raise ProcessLookupError(msg)
    league_dir = Path(league_exe).parent
    return Path(league_dir / "lockfile")


def _lcu_wss(lockfile: Path) -> dict[str, str]:
    with lockfile.open(encoding="utf_8") as f:
        content = f.read()
    parts = content.split(":")

    port = parts[2]
    wss = f"wss://127.0.0.1:{port}"
    https = f"https://127.0.0.1:{port}"

    auth_key = parts[3]
    raw_auth = f"riot:{auth_key}"
    auth = base64.b64encode(bytes(raw_auth, "utf-8")).decode()
    return {"auth": auth, "wss": wss, "https": https}


def find_proc_by_name(name: str | list[str]) -> Any:
    """Finds the executable path of a process by its name.

    Args:
        name (str | list[str]): The name(s) of the process to find (e.g.,
            "LeagueClient.exe").

    Returns:
        Any: The full path to the executable if found, otherwise None.
    """
    if type(name) is str:
        name = list(name)
    proc_list = psutil.process_iter()
    for proc in proc_list:
        if proc.name() in name:
            return proc.exe()
    return None


async def start() -> None:
    """Initializes the application, connects to the LCU, and starts listening events.

    Raises:
        LeWizardGenericError: If 'LeagueClient.exe' or 'LeagueClientUx.exe'
            is not found.

    Returns:
        None: This function runs indefinitely until interrupted.
    """
    ico = f"{tempfile.gettempdir()}\\logo.ico"
    urllib.request.urlretrieve(
        "https://github.com/amburgao/leaguewizard/blob/main/.github/images/logo.ico?raw=true",
        ico,
    )
    tray = SysTrayIcon(ico, "LeagueWizard", on_quit=lambda e: os._exit(0))
    with tray:
        exe = find_proc_by_name(["LeagueClient.exe", "LeagueClientUx.exe"])
        if exe is None:
            msg = "league.exe not found."
            raise LeWizardGenericError(msg, True, "abc", True)
        lockfile = _lcu_lockfile(exe)
        lockfile_data = _lcu_wss(lockfile)
        https = lockfile_data["https"]
        wss = lockfile_data["wss"]
        auth = lockfile_data["auth"]
        header = {"Authorization": f"Basic {auth}"}

        try:
            async with websockets.connect(
                uri=wss,
                additional_headers=header,
                ssl=context,
            ) as ws:
                await ws.send('[2,"0", "GetLolSummonerV1CurrentSummoner"]')
                json.loads(await ws.recv())
                await ws.send('[5, "OnJsonApiEvent_lol-champ-select_v1_session"]')
                async with aiohttp.ClientSession(
                    base_url=https, headers=header
                ) as conn:
                    last_check: str = ""
                    if config.WizConfig['lobby'].get('auto_accept') is True:
                        while True:
                            res = await conn.get(
                                "/lol-gameflow/v1/session", headers=header, ssl=context
                            )
                            _msg = await res.json()
                            phase = _msg.get("phase")
                            if phase != last_check:
                                logger.info(last_check)
                                if phase == "ReadyCheck":
                                    await conn.post(
                                        "/lol-matchmaking/v1/ready-check/accept",
                                        headers=header,
                                        ssl=context,
                                    )
                                    break
                            last_check = phase
                            await asyncio.sleep(1)
                    async for event in ws:
                        await on_message(event, conn)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.exception(e.args)
        except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
            sys.exit(0)
