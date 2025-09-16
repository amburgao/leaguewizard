from __future__ import annotations

import asyncio
import base64
import json
import ssl
import sys
import tempfile
import urllib
from pathlib import Path
from typing import Any

import aiohttp
import psutil
import websockets
from loguru import logger

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
    with lockfile.open() as f:
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
    if type(name) is str:
        name = list(name)
    for proc in psutil.process_iter():
        if proc.name() in name:
            return proc.exe()
    return None


async def start() -> None:
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
            async with aiohttp.ClientSession(base_url=https, headers=header) as conn:
                async for event in ws:
                    await on_message(event, conn)
    except websockets.exceptions.ConnectionClosedError as e:
        logger.exception(e.args)
    except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
        sys.exit(0)
