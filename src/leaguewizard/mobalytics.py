"""Mobalytics handler module."""

import re
from typing import Any

import aiohttp
from async_lru import alru_cache
from loguru import logger
from selectolax.parser import HTMLParser

from leaguewizard.constants import SPELLS
from leaguewizard.exceptions import LeWizardGenericError
from leaguewizard.models import (
    Block,
    Item,
    ItemSet,
    Payload_ItemSets,
    Payload_Perks,
    Payload_Spells,
)


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
        if response.status >= 400:
            raise ConnectionError
        raw_html = await response.text()
        return HTMLParser(raw_html)
    except (aiohttp.ClientResponseError, ConnectionError) as e:
        logger.error(e)
        raise LeWizardGenericError("_get_html returned None.") from e


@alru_cache
async def get_mobalytics_info(
    champion_name: str,
    role: str,
    conn: aiohttp.ClientSession,
    champion_id: int,
    summoner_id: int,
) -> Any:
    """TODO."""
    try:
        page_url = _build_url(champion_name, role)
        tree = await _get_html(page_url, conn)
        if tree is None:
            pass
        skill_order = tree.css(".m-m4se9")
        skills = []
        for node in skill_order:
            skill_attr = node.text()
            skills.append(skill_attr)
        skills_string = " > ".join(skills)
        nodes = tree.css(Payload_ItemSets.itemsets_css)
        blocks: list[Block] = []
        for node in nodes:
            block_name_node = node.css_first("h4")
            if len(blocks) == 0:
                block_name = skills_string
            else:
                block_name = block_name_node.text() if block_name_node else ""
            items_node = node.css(".m-5o4ika")
            block_items: list[Item] = []
            for item_node in items_node:
                item = item_node.attributes.get("src")
                matches = re.search("(\\d+)\\.png", item) if item else None
                if matches is not None:
                    block_items.append(Item(1, matches.group(1)))
            block = Block(block_items, block_name)
            blocks.append(block)
        nodes = tree.css(".m-1eeoc06")
        situational_block_items: list[Item] = []
        for node in nodes:
            item = node.attributes.get("src")
            matches = re.search("(\\d+)\\.png", item) if item else None
            if matches is not None:
                situational_block_items.append(Item(1, matches.group(1)))
        block = Block(situational_block_items, "Situational Items")
        blocks.append(block)
        itemsets = ItemSet(
            [champion_id],
            blocks,
            f"{champion_name} ({role})"
            if role is not None and role != ""
            else f"{champion_name} (ARAM)",
        )
        itemsets_payload = Payload_ItemSets(
            accountId=summoner_id,
            itemSets=[itemsets],
            timestamp=0,
        )

        nodes = tree.css(Payload_Perks.main_perks_css)
        main_perks = []
        selected_perks = []
        for node in nodes:
            src = node.attributes.get("src")
            matches = re.search("/(\\d+)\\.svg", src) if src else None
            if matches:
                main_perks.append(int(matches.group(1)))
        for css in Payload_Perks.selected_perks_css:
            nodes = tree.css(css)
            for node in nodes:
                src = node.attributes.get("src")
                matches = re.search("/(\\d+)(\\.svg|\\.png)\\b", src) if src else None
                if matches:
                    selected_perks.append(int(matches.group(1)))
        perks_payload = Payload_Perks(
            name=f"{champion_name} - {role}"
            if role is not None and role != ""
            else f"{champion_name} - ARAM",
            current=True,
            primaryStyleId=int(main_perks[0]),
            subStyleId=int(main_perks[1]),
            selectedPerkIds=selected_perks,
        )

        nodes = tree.css(Payload_Spells.spells_css)
        spells_ids = []
        for node in nodes:
            src = node.attributes.get("src")
            matches = re.search("(\\w+)\\.png", src) if src else None
            if matches:
                spells_ids.append(SPELLS[matches[1]])
        spells_payload = Payload_Spells(
            selectedSkinId=champion_id,
            spell1Id=int(spells_ids[0]),
            spell2Id=int(spells_ids[1]),
        )
        logger.debug(f"Added to cache: {champion_name}")
        return itemsets_payload, perks_payload, spells_payload
    except (TypeError, AttributeError, ValueError, LeWizardGenericError) as e:
        logger.exception(e)
