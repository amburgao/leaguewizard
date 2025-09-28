"""Handles WebSocket messages from the League of Legends client to update game data.

This module provides functions to process real-time game events, fetch champion-specific
information from external sources like Mobalytics, and then send updated item sets,
rune pages, and summoner spells back to the League of Legends client.
"""

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

from leaguewizard import config, logger
from leaguewizard.core.constants import ROLES
from leaguewizard.core.models import PayloadItemSets, PayloadPerks, PayloadSpells
from leaguewizard.mobalytics import get_mobalytics_info

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
    """Retrieves the latest DDragon version from the Riot Games API.

    Args:
        client (aiohttp.ClientSession): The aiohttp client session.
        url (str): The URL to fetch the versions from. Defaults to
            "https://ddragon.leagueoflegends.com/api/versions.json".

    Returns:
        Any: The latest version string.
    """
    response = await client.get(url)
    content = await response.json()
    return content[0]


@alru_cache
async def _get_champion_dict(client: aiohttp.ClientSession) -> Any:
    """Retrieves a dictionary mapping champion IDs to champion names.

    Args:
        client (aiohttp.ClientSession): The aiohttp client session.

    Returns:
        Any: A dictionary of champion IDs (int) mapped to their champion names (str).
    """
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
    client: aiohttp.ClientSession, payload: PayloadItemSets, account_id: int
) -> None:
    """Sends item set data to the League of Legends client.

    Args:
        client (aiohttp.ClientSession): The aiohttp client session.
        payload (PayloadItemSets): The item sets payload to send.
        account_id (int): The summoner's account ID.
    """
    await client.put(
        url=f"/lol-item-sets/v1/item-sets/{account_id}/sets",
        json=payload.asjson(),
        ssl=context,
    )


async def send_perks(client: aiohttp.ClientSession, payload: PayloadPerks) -> None:
    """Sends rune page data to the League of Legends client.

    If a current rune page exists, it will be deleted before creating a new one.

    Args:
        client (aiohttp.ClientSession): The aiohttp client session.
        payload (PayloadPerks): The rune page payload to send.
    """
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
        json=payload.asjson(),
        ssl=context,
    )


async def send_spells(client: aiohttp.ClientSession, payload: PayloadSpells) -> None:
    """Sends summoner spell data to the League of Legends client.

    Args:
        client (aiohttp.ClientSession): The aiohttp client session.
        payload (PayloadSpells): The summoner spells payload to send.
    """
    await client.patch(
        url="/lol-champ-select/v1/session/my-selection",
        json=payload.asjson(),
        ssl=context,
    )


async def get_champion_name(
    client: aiohttp.ClientSession,
    champion_id: int,
) -> str | None:
    """Retrieves the name of a champion given their ID.

    Args:
        client (aiohttp.ClientSession): The aiohttp client session.
        champion_id (int): The ID of the champion.

    Returns:
        str | None: The champion's name if found, otherwise None.
    """
    champions = await _get_champion_dict(client)
    champion_name = champions[champion_id]
    return champion_name if champion_name else None


class _ChampionTracker:
    """Tracks the last processed champion ID to avoid redundant updates."""

    def __init__(self) -> None:
        self._value: int = 0

    def last_id(self, value: int | None = None) -> int:
        """Gets or sets the last champion ID.

        Args:
            value (int | None): The new champion ID to set. If None, the current
                value is returned. Defaults to None.

        Returns:
            int: The current or newly set last champion ID.
        """
        if value is not None:
            self._value = value
        return self._value


champion_tracker = _ChampionTracker()


async def on_message(event: str | bytes, conn: Any, ws: Any) -> None:
    """Handles incoming WebSocket messages from the League of Legends client.

    This function parses champion selection events, fetches Mobalytics data,
    and sends item sets, runes, and summoner spells to the client.

    Args:
        event (str | bytes): The WebSocket message event data.
        conn (Any): The connection object (aiohttp.ClientSession).
        ws (Any): The WebSocket connection object.
    """
    try:
        last_check: str = ""
        if config.auto_accept is True:
            while True:
                res = await conn.get("/lol-gameflow/v1/session", ssl=context)
                _msg = await res.json()
                phase = _msg.get("phase")
                logger.info(phase)
                if phase == "ChampSelect":
                    break
                if phase != last_check:
                    logger.info(last_check)
                    if phase == "ReadyCheck":
                        await conn.post(
                            "/lol-matchmaking/v1/ready-check/accept",
                            ssl=context,
                        )
                        break
                last_check = phase
                await asyncio.sleep(1)
        data = json.loads(event)[2]["data"]
        logger.info(json.dumps(data, indent=2))
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
