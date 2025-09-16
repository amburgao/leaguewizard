"""Mobalytics handler module."""

import os
import re
from pathlib import Path
from typing import Any

import aiohttp
from async_lru import alru_cache
from dotenv import load_dotenv
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

if Path(".env").exists():
    load_dotenv(".env")


def _build_url(champion_name: str, role: str | None) -> str:
    base_url = "https://mobalytics.gg/lol/champions"
    return (
        f"{base_url}/{champion_name}/build/{role}"
        if role != "" and role is not None
        else f"{base_url}/{champion_name}/aram-builds"
    )


async def _get_html(url: str, client: aiohttp.ClientSession) -> HTMLParser:
    try:
        response = await client.get(url)
        if response.status >= RESPONSE_ERROR_CODE:
            raise ConnectionError
        raw_html = await response.text()
        return HTMLParser(raw_html)
    except (aiohttp.ClientResponseError, ConnectionError) as e:
        logger.error(e)
        raise LeWizardGenericError("_get_html returned None.") from e


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
        page_url = _build_url(champion_name, role)
        response = await conn.get(page_url)
        page_content = await response.text()
        tree = HTMLParser(page_content)

        item_sets = (
            _get_aram_item_sets(tree) if role is None else _get_sr_item_sets(tree)
        )
        itemsets_payload = _get_item_sets_payload(
            item_sets, summoner_id, champion_id, champion_name
        )

        perks = _get_perks(tree)

        perks_payload = _get_perks_payload(
            perks=perks, champion_name=champion_name, role=role
        )

        spells = _get_spells(tree)
        spells_payload = _get_spells_payload(spells)

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
    item_sets: dict, accountId: int, champion_id: int, champion_name: str
) -> Any:
    blocks = []
    for block, items in item_sets.items():
        _items = []
        for item in items:
            _items.append(Item(1, item))
        blocks.append(Block(_items, block))
    itemset = ItemSet([champion_id], blocks, champion_name)
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


def _get_perks_payload(perks: Any, champion_name: str, role: str | None) -> Any:
    return Payload_Perks(
        name=f"{champion_name} - {role}"
        if role is not None and role != ""
        else f"{champion_name} - ARAM",
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
    flash_config = (
        os.getenv("FLASH_POS", "").lower()
        if flash_env is not None
        else WizConfig["spells"]["flash"]
    )
    spells = _set_flash_position(spells, 4, (0 if flash_config == "on_left" else 1))
    return Payload_Spells(spells[0], spells[1], selectedSkinId=0)
