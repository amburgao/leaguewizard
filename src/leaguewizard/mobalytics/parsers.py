"""Provides parsers for extracting specific data from HTML content.

This module contains classes designed to parse web pages, specifically from
Mobalytics, to extract information such as item sets for League of Legends
champions.
"""

import re
from abc import ABC, abstractmethod
from typing import Any

from selectolax.parser import HTMLParser, Node

from leaguewizard import config
from leaguewizard.core.constants import SPELLS
from leaguewizard.core.models import (
    Block,
    Item,
    ItemSet,
    PayloadItemSets,
    PayloadPerks,
    PayloadSpells,
)


class BaseParser(ABC):
    """An abstract base class for parsers."""

    def __init__(self, html: HTMLParser) -> None:
        """Initializes the BaseParser.

        Args:
            html (HTMLParser): The HTML content to parse.
        """
        self.html = html
        self._payload: Any = None

    @abstractmethod
    def parse(self, *args: Any, **kwargs: Any) -> None:
        """Parses the HTML content."""
        ...

    @property
    def payload(self) -> Any:
        """Returns the parsed payload.

        Returns:
            Any: The parsed payload.
        """
        return self._payload


class ItemsetsParser(BaseParser):
    """A parser for champion item sets."""

    def parse(
        self,
        account_id: int,
        champion_id: int,
        champion_name: str,
        role: str,
    ) -> None:
        """Parses the item sets from the HTML for a specific champion and role.

        Args:
            account_id (int): The account ID.
            champion_id (int): The champion ID.
            champion_name (str): The champion name.
            role (str): The role or game mode (e.g., 'aram').
        """
        item_sets = (
            self._get_aram_item_sets() if role == "aram" else self._get_sr_item_sets()
        )
        self._payload = self._get_item_sets_payload(
            item_sets,
            account_id,
            champion_id,
            champion_name,
            role,
        )

    def _get_sr_item_sets(self) -> dict[str, Any]:
        """Extracts Summoner's Rift item sets from the HTML.

        Raises:
            ValueError: If the main container for item sets is not found.

        Returns:
            dict[str, Any]: A dictionary of Summoner's Rift item sets.
        """
        container_div = self.html.css_first("div.m-owe8v3:nth-child(2)")

        if container_div is None:
            raise ValueError

        tree = container_div.css(".m-1q4a7cx") + self.html.css(".m-s76v8c")
        itemsets = self._get_itemsets(tree)
        return {
            "Starter Items": itemsets[0],
            "Early Items": itemsets[1],
            "Core Items": itemsets[2],
            "Full Build": itemsets[3],
            "Situational Items": itemsets[4],
        }

    def _get_aram_item_sets(self) -> dict[str, Any]:
        """Extracts ARAM item sets from the HTML.

        Raises:
            ValueError: If the main container for item sets is not found.

        Returns:
            dict[str, Any]: A dictionary of ARAM item sets.
        """
        container_div = self.html.css_first("div.m-owe8v3:nth-child(2)")

        if container_div is None:
            raise ValueError

        tree = container_div.css(".m-1q4a7cx") + self.html.css(".m-s76v8c")
        itemsets = self._get_itemsets(tree)
        return {
            "Starter Items": itemsets[0],
            "Core Items": itemsets[1],
            "Full Build": itemsets[2],
            "Situational Items": itemsets[3],
        }

    @staticmethod
    def _get_itemsets(tree: list[Node]) -> list[list[Any]]:
        """Extracts item sets from a list of HTML nodes.

        Args:
            tree (list[Node]): A list of HTML nodes containing item images.

        Returns:
            list[list[Any]]: A list of item sets, each item set is a list of item IDs.
        """
        item_sets_groups = []

        for node in tree:
            items = []

            for img in node.css("img"):
                src = img.attributes.get("src")
                matches = re.search(r"/(\d+)\.png", src) if src else None

                if matches:
                    items.append(matches.group(1))

            item_sets_groups.append(items)
        return item_sets_groups

    @staticmethod
    def _get_item_sets_payload(
        item_sets: dict,
        account_id: int,
        champion_id: int,
        champion_name: str,
        role: str,
    ) -> Any:
        """Creates the payload for the item sets.

        Args:
            item_sets (dict): A dictionary of item sets.
            account_id (int): The account ID.
            champion_id (int): The champion ID.
            champion_name (str): The champion name.
            role (str): The role or game mode (e.g., 'aram').

        Returns:
            Any: The constructed payload for the item sets.
        """
        blocks = []
        for block, items in item_sets.items():
            item_list = [Item(count=1, id=item) for item in items]
            blocks.append(Block(items=item_list, type=block))
        itemset = ItemSet(
            associatedChampions=[champion_id],
            blocks=blocks,
            title=f"{champion_name.capitalize()} - {role.upper()}",
        )
        return PayloadItemSets(accountId=account_id, itemSets=[itemset], timestamp=0)


class PerksParser(BaseParser):
    """A parser for champion rune (perks) pages."""

    def parse(self, champion_name: str, role: str) -> None:
        """Parses the perks from the HTML and creates a PayloadPerks object.

        Args:
            champion_name (str): The name of the champion.
            role (str): The role of the champion (e.g., "top", "aram").
        """
        perks = self._get_perks()
        self._payload = PayloadPerks(
            current=True,
            name=f"{champion_name.capitalize()} - {role.upper()}",
            primaryStyleId=perks[0],
            subStyleId=perks[1],
            selectedPerkIds=perks[2:],
        )

    def _get_perks(self) -> Any:
        perks_selectors = [".m-68x97p", ".m-1iebrlh", ".m-1nx2cdb", ".m-1u3ui07"]
        srcs = [
            node.attributes.get("src")
            for selector in perks_selectors
            for node in self.html.css(selector)
        ]
        matches = [
            re.search(r"/(\d+)\.(svg|png)\b", src) for src in srcs if src is not None
        ]
        if matches:
            perks = [int(match.group(1)) for match in matches if match is not None]
        if len(perks) == 0:
            raise ValueError
        return perks


class SpellsParser(BaseParser):
    """A parser for champion summoner spells."""

    def parse(self) -> None:
        """Parses the summoner spells from HTML and creates a PayloadSpells object."""
        spells = self._get_spells()
        flash_config = config.flash
        flash_pos = 0 if flash_config == "d" else 1
        spells = self._set_flash_position(spells, 4, flash_pos)
        self._payload = PayloadSpells(
            spell1Id=spells[0],
            spell2Id=spells[1],
            selectedSkinId=0,
        )

    def _get_spells(self) -> list[int]:
        spells = []

        nodes = self.html.css(".m-d3vnz1")
        for node in nodes:
            alt = node.attributes.get("alt")
            if not alt:
                raise ValueError
            spell = SPELLS[alt]
            spells.append(int(spell))
        if not spells:
            raise ValueError
        return spells

    @staticmethod
    def _set_flash_position(
        spell_list: list[int],
        spell_id: int = 4,
        index: int = 1,
    ) -> list[int]:
        if spell_id not in spell_list:
            return spell_list

        spell_list = [x for x in spell_list if x != spell_id]
        spell_list.insert(index, spell_id)
        return spell_list
