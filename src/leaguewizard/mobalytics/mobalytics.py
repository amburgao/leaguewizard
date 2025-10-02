"""Mobalytics handler module."""

from typing import Any

import aiohttp
from async_lru import alru_cache
from loguru import logger
from selectolax.parser import HTMLParser

from leaguewizard.core.constants import RESPONSE_ERROR_CODE
from leaguewizard.core.exceptions import LeWizardGenericError
from leaguewizard.mobalytics.parsers import ItemsetsParser, PerksParser, SpellsParser


class MobaChampion:
    """Represents the champion mobalytics webpage."""

    def __init__(self, champion_name: str, role: str) -> None:
        """Initializes the MobaChampion instance.

        Args:
            champion_name (str): The name of the champion.
            role (str): The role of the champion (e.g., "top", "aram").
        """
        self.champion_name = champion_name
        self.role = role
        self.url = self._build_url()
        self.html: HTMLParser | None = None

    def _build_url(self) -> str:
        """Builds the Mobalytics URL for the champion and role.

        Returns:
            str: The constructed URL.
        """
        base_url = "https://mobalytics.gg/lol/champions"
        endpoint = (
            f"{self.champion_name}/build/{self.role}"
            if self.role != "aram"
            else f"{self.champion_name}/aram-builds"
        )
        return f"{base_url}/{endpoint}"

    async def fetch_data(self, client: aiohttp.ClientSession) -> HTMLParser:
        """Fetches the HTML content of the Mobalytics champion page.

        Args:
            client (aiohttp.ClientSession): The aiohttp client session.

        Raises:
            LeWizardGenericError: If the champion HTML could not be retrieved.

        Returns:
            HTMLParser: The parsed HTML content.
        """
        try:
            response = await client.get(self.url)
            if response.status >= RESPONSE_ERROR_CODE:
                logger.debug(f"request failed: {response.request_info}")
            content = await response.text()
            self.html = HTMLParser(content)

        except aiohttp.ClientResponseError as e:
            raise LeWizardGenericError from e

        return self.html

    def itemsets_payload(self, summoner_id: int, champion_id: int) -> Any:
        """Generates the item sets payload for the LCU API.

        Args:
            summoner_id (int): The summoner's ID.
            champion_id (int): The champion's ID.

        Returns:
            Any: The PayloadItemSets object or None if HTML content is not available.
        """
        if self.html is None:
            return None
        itemsets = ItemsetsParser(html=self.html)
        itemsets.parse(
            account_id=summoner_id,
            champion_id=champion_id,
            champion_name=self.champion_name,
            role=self.role,
        )
        return itemsets.payload

    def perks_payload(self) -> Any:
        """Generates the perks payload for the LCU API.

        Returns:
            Any: The PayloadPerks object or an empty dictionary if not HTML.
        """
        if self.html is None:
            return None
        perks = PerksParser(self.html)
        perks.parse(champion_name=self.champion_name, role=self.role)
        return perks.payload

    def spells_payload(self) -> Any:
        """Generates the spells payload for the LCU API.

        Returns:
            Any: The PayloadSpells object or an empty dictionary if not HTML.
        """
        if self.html is None:
            return None
        spells = SpellsParser(self.html)
        spells.parse()
        return spells.payload


@alru_cache
async def get_mobalytics_info(
    champion_name: str,
    role: str | None,
    conn: aiohttp.ClientSession,
    champion_id: int,
    summoner_id: int,
) -> Any:
    """Fetches Mobalytics item sets, perks, spells for a given champion and role.

    Args:
        champion_name (str): The name of the champion.
        role (str): The role of the champion (e.g., "top", "aram").
        conn (aiohttp.ClientSession): Aiohttp client session for making HTTP requests.
        champion_id (int): The ID of the champion.
        summoner_id (int): The ID of the summoner.

    Returns:
        Any: A tuple containing the itemsets_payload, perks_payload, and spells_payload.
    """
    try:
        if role is None:
            role = "aram"
        champion = MobaChampion(champion_name, role)
        await champion.fetch_data(conn)

        itemsets_payload = champion.itemsets_payload(summoner_id, champion_id)
        perks_payload = champion.perks_payload()
        spells_payload = champion.spells_payload()

        logger.debug(f"Added to cache: {champion_name}")

    except (TypeError, AttributeError, ValueError, LeWizardGenericError) as e:
        logger.exception(e)

    return itemsets_payload, perks_payload, spells_payload
