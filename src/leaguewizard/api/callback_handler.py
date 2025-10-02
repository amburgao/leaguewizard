"""Handles WebSocket messages from the League of Legends client to update game data.

This module provides functions to process real-time game events, fetch champion-specific
information from external sources like Mobalytics, and then send updated item sets,
rune pages, and summoner spells back to the League of Legends client.
"""

import asyncio
import contextlib
import json
import sys
from ssl import SSLContext
from typing import Any

import aiohttp
from async_lru import alru_cache

from leaguewizard import config, logger
from leaguewizard.api.models import SummonerData
from leaguewizard.api.utils import ssl_context
from leaguewizard.core.constants import ROLES
from leaguewizard.core.models import PayloadItemSets, PayloadPerks, PayloadSpells
from leaguewizard.mobalytics import get_mobalytics_info


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


async def send_itemsets(
    client: aiohttp.ClientSession,
    payload: PayloadItemSets,
    account_id: int,
    context: SSLContext,
) -> None:
    """Sends item set data for a given account ID.

    Args:
        client: An aiohttp client session for making HTTP requests.
        payload: The PayloadItemSets object containing the item set data.
        account_id: The unique identifier for the League of Legends account.
        context: An SSLContext object for secure HTTP connections.
    """
    await client.put(
        url=f"/lol-item-sets/v1/item-sets/{account_id}/sets",
        json=payload.asjson(),
        ssl=context,
    )
    logger.debug("Successfully imported itemsets.")


async def send_perks(
    client: aiohttp.ClientSession,
    payload: PayloadPerks,
    context: SSLContext,
) -> None:
    """Deletes the current rune page and creates a new one.

    Deletes the current rune page if it exists and then creates a new rune
    page based on the provided payload.

    Args:
        client: An aiohttp.ClientSession for making HTTP requests.
        payload: A PayloadPerks object containing the data for the new rune page.
        context: An SSLContext for establishing secure connections.
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
    logger.debug("Successfully imported perks.")


async def send_spells(
    client: aiohttp.ClientSession,
    payload: PayloadSpells,
    context: SSLContext,
) -> None:
    """Sends a spell to the League of Legends client.

    Args:
        client: An aiohttp client session.
        payload: The payload containing spell information.
        context: The SSL context for the client.
    """
    await client.patch(
        url="/lol-champ-select/v1/session/my-selection",
        json=payload.asjson(),
        ssl=context,
    )
    logger.debug("Successfully imported spells.")


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
    return champion_name or None


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


async def on_message(
    event: str | bytes,
    conn: aiohttp.ClientSession,
    aio_client_id: int,
) -> None:
    """Handles incoming messages from a connection.

    Args:
        event: The incoming message event.
        conn: The aiohttp client session for the connection.
        aio_client_id: Random int to ensure there is only one
            aiohttp ClientSession being used.
    """
    logger.debug(f"aio_client_id: {aio_client_id}")
    try:
        if config.auto_accept is True:
            await handle_auto_accept(conn)

        data = json.loads(event)[2]["data"]

        summoner = next(
            (
                player
                for player in data.get("myTeam")
                if player.get("cellId") == data.get("localPlayerCellId")
            ),
            None,
        )
        summoner_data = SummonerData.model_validate(summoner, by_alias=True)

        champion_id = max(
            summoner_data.champion_id,
            summoner_data.champion_pick_intent,
        )

        if champion_id == champion_tracker.last_id():
            return
        logger.debug(
            f"Last champion: {champion_tracker.last_id()} | Current: {champion_id}.",
        )
        champion_list = await _get_champion_dict(conn)
        logger.debug("Fetched champion_list.")

        champion_name = champion_list.get(champion_id)
        logger.debug(f"Champion name: {champion_name}")

        role = (
            ROLES.get(summoner_data.assigned_position)
            if summoner_data.assigned_position is not None
            else "aram"
        )

        itemsets_payload, perks_payload, spells_payload = await get_mobalytics_info(
            champion_name,
            role,
            conn,
            champion_id,
            summoner_data.summoner_id,
        )

        await asyncio.gather(
            send_itemsets(
                conn,
                itemsets_payload,
                summoner_data.summoner_id,
                context=ssl_context(),
            ),
            send_perks(conn, perks_payload, context=ssl_context()),
            send_spells(conn, spells_payload, context=ssl_context()),
        )
        champion_tracker.last_id(champion_id)

    except (
        KeyError,
        TypeError,
        IndexError,
        json.decoder.JSONDecodeError,
        ValueError,
    ) as e:
        logger.debug(e)

    except (KeyboardInterrupt, asyncio.exceptions.CancelledError) as e:
        logger.exception(e)
        sys.exit(0)


async def handle_auto_accept(conn: Any) -> None:
    """Handles the automatic acceptance of game phases.

    Continuously checks the gameflow session for phase changes.
    If the phase is "ChampSelect", it breaks the loop.
    If the phase is "ReadyCheck", it accepts the match and breaks.
    For other phases, it logs the phase change if it's different
    from the last observed phase.

    Arguments:
        conn: The connection object to interact with the game client.
        last_phase: The last observed game phase, used for logging.

    Returns:
        None
    """
    while True:
        context = ssl_context()

        response = await conn.get("/lol-gameflow/v1/session", ssl=context)
        content = await response.json()

        phase = content.get("phase")

        match phase:
            case "ChampSelect":
                break

            case "ReadyCheck":
                await conn.post(
                    "/lol-matchmaking/v1/ready-check/accept",
                    ssl=context,
                )
                break

        await asyncio.sleep(1)
