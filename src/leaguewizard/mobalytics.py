"""Mobalytics handler module."""

import os
import re
from pathlib import Path
from typing import Any

import aiohttp
from async_lru import alru_cache
from loguru import logger
from selectolax.parser import HTMLParser, Node

from leaguewizard.config import WizConfig
from leaguewizard.constants import RESPONSE_ERROR_CODE, SPELLS
from leaguewizard.exceptions import LeWizardGenericError
from leaguewizard.models import (
    Block,
    Item,
    ItemSet,
    Payload_ItemSets,
    Payload_Perks,
    Payload_Spells,
)


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
                raise aiohttp.ClientResponseError(
                    response.request_info, response.history
                )
            content = await response.text()
            self.html = HTMLParser(content)
            return self.html
        except aiohttp.ClientResponseError as e:
            raise LeWizardGenericError("Could not get champion html.") from e

    def _get_itemsets_by_role(self) -> Any:
        if self.html is None:
            return {}
        if self.role == "aram":
            return _get_aram_item_sets(self.html)
        return _get_sr_item_sets(self.html)

    def itemsets_payload(self, summoner_id: int, champion_id: int) -> Any:
        """Generates the item sets payload for the LCU API.

        Args:
            summoner_id (int): The summoner's ID.
            champion_id (int): The champion's ID.

        Returns:
            Any: The Payload_ItemSets object.
        """
        return _get_item_sets_payload(
            self._get_itemsets_by_role(),
            summoner_id,
            champion_id,
            self.champion_name,
            self.role,
        )

    def perks_payload(self) -> Any:
        """Generates the perks payload for the LCU API.

        Returns:
            Any: The Payload_Perks object or an empty dictionary if not HTML.
        """
        if self.html is None:
            return {}
        return _get_perks_payload(
            perks=_get_perks(self.html),
            champion_name=self.champion_name,
            role=self.role,
        )

    def spells_payload(self) -> Any:
        """Generates the spells payload for the LCU API.

        Returns:
            Any: The Payload_Spells object or an empty dictionary if not HTML.
        """
        if self.html is None:
            return {}
        return _get_spells_payload(_get_spells(self.html))


@alru_cache
async def get_mobalytics_info(
    champion_name: str,
    role: str | None,
    conn: aiohttp.ClientSession,
    champion_id: int,
    summoner_id: int,
) -> Any:
    """TODO."""
    try:
        if role is None:
            role = "aram"
        champion = MobaChampion(champion_name, role)
        await champion.fetch_data(conn)

        itemsets_payload = champion.itemsets_payload(summoner_id, champion_id)
        perks_payload = champion.perks_payload()
        spells_payload = champion.spells_payload()

        logger.debug(f"Added to cache: {champion_name}")
        return itemsets_payload, perks_payload, spells_payload
    except (TypeError, AttributeError, ValueError, LeWizardGenericError) as e:
        logger.exception(e)


def _get_itemsets(tree: list[Node]) -> list[list[Any]]:
    item_sets_groups = []

    for node in tree:
        items = []

        if node is None:
            continue

        for img in node.css("img"):
            src = img.attributes.get("src")
            matches = re.search("/(\\d+)\\.png", src) if src else None

            if matches:
                items.append(matches.group(1))

        item_sets_groups.append(items)
    return item_sets_groups


def _get_sr_item_sets(html: HTMLParser) -> dict[str, Any]:
    container_div = html.css_first("div.m-owe8v3:nth-child(2)")

    if container_div is None:
        raise ValueError

    tree = container_div.css(".m-1q4a7cx") + html.css(".m-s76v8c")
    itemsets = _get_itemsets(tree)
    return {
        "Starter Items": itemsets[0],
        "Early Items": itemsets[1],
        "Core Items": itemsets[2],
        "Full Build": itemsets[3],
        "Situational Items": itemsets[4],
    }


def _get_aram_item_sets(html: HTMLParser) -> dict[str, Any]:
    container_div = html.css_first("div.m-owe8v3:nth-child(2)")

    if container_div is None:
        raise ValueError

    tree = container_div.css(".m-1q4a7cx") + html.css(".m-s76v8c")
    itemsets = _get_itemsets(tree)
    return {
        "Starter Items": itemsets[0],
        "Core Items": itemsets[1],
        "Full Build": itemsets[2],
        "Situational Items": itemsets[3],
    }


def _get_item_sets_payload(
    item_sets: dict, accountId: int, champion_id: int, champion_name: str, role: str
) -> Any:
    blocks = []
    for block, items in item_sets.items():
        _items = []
        for item in items:
            _items.append(Item(1, item))
        blocks.append(Block(_items, block))
    itemset = ItemSet(
        [champion_id], blocks, f"{champion_name.capitalize()} - {role.upper()}"
    )
    return Payload_ItemSets(accountId, [itemset], 0)


def _get_perks(html: HTMLParser) -> Any:
    perks_selectors = [".m-68x97p", ".m-1iebrlh", ".m-1nx2cdb", ".m-1u3ui07"]
    perks = []
    for selector in perks_selectors:
        nodes = html.css(selector)
        for node in nodes:
            src = node.attributes.get("src")
            if src:
                matches = re.search("/(\\d+)\\.(svg|png)\\b", src)
                if matches:
                    perks.append(int(matches.group(1)))
    if len(perks) == 0:
        raise ValueError
    return perks


def _get_perks_payload(perks: Any, champion_name: str, role: str) -> Any:
    return Payload_Perks(
        name=f"{champion_name.capitalize()} - {role.upper()}",
        current=True,
        primaryStyleId=perks[0],
        subStyleId=perks[1],
        selectedPerkIds=perks[2:],
    )


def _set_flash_position(
    spell_list: list[int], spell_id: int = 4, index: int = 1
) -> list[int]:
    if spell_id not in spell_list:
        return spell_list

    spell_list = [x for x in spell_list if x != spell_id]
    spell_list.insert(index, spell_id)
    return spell_list


def _get_spells(html: HTMLParser) -> list[int]:
    spells = []

    nodes = html.css(".m-d3vnz1")
    for node in nodes:
        alt = node.attributes.get("alt")
        if not alt:
            raise ValueError
        spell = SPELLS[alt]
        spells.append(int(spell))
    if not spells:
        raise ValueError
    return spells


def _get_spells_payload(spells: list[int]) -> Any:
    flash_env = os.getenv("FLASH_POS", None)
    if flash_env is None:
        from dotenv import load_dotenv  # noqa: PLC0415

        if Path(".env").exists():
            load_dotenv(".env")
            flash_env = os.getenv("FLASH_POS", None)
    flash_config = (
        os.getenv("FLASH_POS", "").lower()
        if flash_env is not None
        else WizConfig["spells"]["flash"]
    )
    spells = _set_flash_position(spells, 4, (0 if flash_config == "on_left" else 1))
    return Payload_Spells(spells[0], spells[1], selectedSkinId=0)
