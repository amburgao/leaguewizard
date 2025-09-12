from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import ssl
from pathlib import Path
from typing import Any

import aiohttp
import psutil
import websockets
from async_lru import alru_cache
from loguru import logger

from leaguewizard.constants import ROLES
from leaguewizard.mobalytics import get_mobalytics_info
from leaguewizard.models import (
    Payload_ItemSets,
    Payload_Perks,
    Payload_Spells,
)

_last_champion_id = None


RIOT_CERT = Path("./riotgames.pem").resolve()

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


@alru_cache
async def _get_champion_list(client: aiohttp.ClientSession) -> Any:
    response = await client.get("https://ddragon.leagueoflegends.com/api/versions.json")
    content = await response.json()
    latest_ddragon_ver = content[0]

    response = await client.get(
        f"https://ddragon.leagueoflegends.com/cdn/{latest_ddragon_ver}/data/en_US/champion.json",
    )
    content = await response.json()
    return content["data"]


async def get_champion_name(
    client: aiohttp.ClientSession,
    champion_id: int,
) -> str | None:
    ddragon_data = await _get_champion_list(client)
    name = ""
    for item in ddragon_data.values():
        if item["key"] == str(champion_id):
            name = item["id"]
    if name:
        return name
    return None


async def on_message(event: str | bytes, conn: Any) -> None:
    try:
        _data = json.loads(event)[2]
        data = _data["data"]
        local_p_cell_id = data["localPlayerCellId"]
        my_team = data["myTeam"]
        champion_id = 0
        summoner_id = 0
        assigned_position = None
        for p in my_team:
            if p["cellId"] == local_p_cell_id:
                logger.debug(p)
                if str(p["championId"]).strip() != "0":
                    champion_id = p["championId"]
                else:
                    champion_id = p["championPickIntent"]
                assigned_position = p["assignedPosition"]
                summoner_id = p["summonerId"]
        champion_name = (
            await get_champion_name(conn, champion_id) if champion_id else None
        )
        role = ROLES.get(assigned_position) if assigned_position is not None else None
        itemsets_payload, perks_payload, spells_payload = await get_mobalytics_info(
            champion_name, role, conn, champion_id, summoner_id
        )
        global _last_champion_id
        logger.debug(f"{champion_id} // {_last_champion_id}")
        if _last_champion_id != champion_id:
            await asyncio.gather(
                send_itemsets(conn, itemsets_payload),
                send_perks(conn, perks_payload),
                send_spells(conn, spells_payload),
            )
        _last_champion_id = champion_id
    except (json.decoder.JSONDecodeError, KeyError, TypeError, IndexError) as e:
        logger.exception(e)
        pass
    except KeyboardInterrupt:
        raise


async def send_itemsets(
    client: aiohttp.ClientSession,
    payload: Payload_ItemSets,
) -> None:
    await client.put(
        url=payload.endpoint_put,
        json=payload.asdict(),
        ssl=context,
    )


async def send_perks(client: aiohttp.ClientSession, payload: Payload_Perks) -> None:
    with contextlib.suppress(KeyError):
        response = await client.get(
            url=payload.endpoint_get,
            ssl=context,
        )
        content = await response.json()
        page_id = content["id"]
        if page_id:
            payload.endpoint_delete = page_id
            await client.delete(
                url=payload.endpoint_delete,
                ssl=context,
            )

    await client.post(
        url=payload.endpoint_post,
        json=payload.asdict(),
        ssl=context,
    )


async def send_spells(client: aiohttp.ClientSession, payload: Payload_Spells) -> None:
    await client.patch(
        url=payload.endpoint_patch,
        json=payload.asdict(),
        ssl=context,
    )


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
        raise RuntimeError(msg)
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
    except (
        KeyboardInterrupt,
        asyncio.exceptions.CancelledError,
        websockets.exceptions.ConnectionClosedError,
    ) as e:
        logger.exception(e)
        pass

    return
