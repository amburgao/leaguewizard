import asyncio
import contextlib
import json
import ssl
import sys
import tempfile
import urllib
from pathlib import Path
from typing import Any

import aiohttp
from async_lru import alru_cache

from leaguewizard import logger
from leaguewizard.constants import ROLES
from leaguewizard.mobalytics import get_mobalytics_info
from leaguewizard.models import Payload_ItemSets, Payload_Perks, Payload_Spells

RIOT_CERT = Path(tempfile.gettempdir(), "riotgames.pem")
if not RIOT_CERT.exists():
    urllib.request.urlretrieve(
        "https://static.developer.riotgames.com/docs/lol/riotgames.pem", RIOT_CERT
    )

context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.load_verify_locations(RIOT_CERT)
context.check_hostname = False


@alru_cache
async def _get_latest_version(
    client: aiohttp.ClientSession,
    url: str = "https://ddragon.leagueoflegends.com/api/versions.json",
) -> Any:
    response = await client.get(url)
    content = await response.json()
    return content[0]


@alru_cache
async def _get_champion_dict(client: aiohttp.ClientSession) -> Any:
    latest_ddragon_ver = await _get_latest_version(client)

    response = await client.get(
        f"https://ddragon.leagueoflegends.com/cdn/{latest_ddragon_ver}/data/en_US/champion.json",
    )
    content = await response.json()
    data = content["data"]
    champion_list = {}
    for champion in data:
        champion_key = int(data[champion]["key"])
        champion_list[champion_key] = champion
    return dict(sorted(champion_list.items()))


context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.load_verify_locations(RIOT_CERT)
context.check_hostname = False


async def send_itemsets(
    client: aiohttp.ClientSession, payload: Payload_ItemSets, accountId: int
) -> None:
    await client.put(
        url=f"/lol-item-sets/v1/item-sets/{accountId}/sets",
        json=payload.asdict(),
        ssl=context,
    )


async def send_perks(client: aiohttp.ClientSession, payload: Payload_Perks) -> None:
    with contextlib.suppress(KeyError):
        response = await client.get(
            url="/lol-perks/v1/currentpage",
            ssl=context,
        )
        content = await response.json()
        page_id = content["id"]
        if page_id:
            await client.delete(
                url=f"/lol-perks/v1/pages/{page_id}",
                ssl=context,
            )

    await client.post(
        url="/lol-perks/v1/pages",
        json=payload.asdict(),
        ssl=context,
    )


async def send_spells(client: aiohttp.ClientSession, payload: Payload_Spells) -> None:
    await client.patch(
        url="/lol-champ-select/v1/session/my-selection",
        json=payload.asdict(),
        ssl=context,
    )


async def get_champion_name(
    client: aiohttp.ClientSession,
    champion_id: int,
) -> str | None:
    champions = await _get_champion_dict(client)
    champion_name = champions[champion_id]
    return champion_name if champion_name else None


class _ChampionTracker:
    def __init__(self) -> None:
        self._value: int = 0

    def last_id(self, value: int | None = None) -> int:
        if value is not None:
            self._value = value
        return self._value


champion_tracker = _ChampionTracker()


async def on_message(event: str | bytes, conn: Any) -> None:
    try:
        data = json.loads(event)[2]["data"]
        player_cell_id = data["localPlayerCellId"]
        my_team = data["myTeam"]

        for player in my_team:
            if player["cellId"] == player_cell_id:
                current_summoner = player

        if "current_summoner" not in locals():
            return

        selected_id = int(current_summoner["championId"])
        pick_intent = int(current_summoner["championPickIntent"])
        champion_id = selected_id if selected_id != 0 else pick_intent
        if champion_id == champion_tracker.last_id():
            return
        logger.debug(
            f"The last champion was {champion_tracker.last_id()}.\n"
            f"The current is {champion_id}."
        )
        summoner_id = current_summoner["summonerId"]
        assigned_position = current_summoner["assignedPosition"]

        champions = await _get_champion_dict(conn)

        champion_name = champions[champion_id]

        role = ROLES.get(assigned_position) if assigned_position else None

        itemsets_payload, perks_payload, spells_payload = await get_mobalytics_info(
            champion_name, role, conn, champion_id, summoner_id
        )

        if champion_tracker.last_id() != champion_id:
            await asyncio.gather(
                send_itemsets(conn, itemsets_payload, summoner_id),
                send_perks(conn, perks_payload),
                send_spells(conn, spells_payload),
            )

        champion_tracker.last_id(champion_id)

    except (
        KeyError,
        TypeError,
        IndexError,
        json.decoder.JSONDecodeError,
    ) as e:
        logger.debug(e)

    except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
        sys.exit(0)
