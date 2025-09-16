from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Payload:
    """Base class for all LCU API payloads."""

    def asdict(self) -> dict[str, Any]:
        """Convert the payload to a dictionary.

        Returns:
            (dict[str, Any]): A dictionary representation of the payload.
        """
        return asdict(self)


@dataclass
class Payload_ItemSets(Payload):
    """Payload for the itemsets endpoint (/lol-item-sets/v1/item-sets/{accountId}/sets).

    Attributes:
        accountId (int): Summoner account ID.
        itemSets (list[ItemSet] | None): List of item sets. Defaults to None.
        timestamp (int): Timestamp value. Defaults to 1 (unused).
    """

    accountId: int
    itemSets: list[ItemSet] | None = None
    timestamp: int = 1


@dataclass
class ItemSet:
    """Represents a single item set configuration.

    Attributes:
        associatedChampions (list[int]): Champion IDs this set applies to.
        blocks (list[Block]): List of item blocks in the set.
        title (str): Name of the item set (e.g., "Ezreal - ADC").
    """

    associatedChampions: list[int]
    blocks: list[Block]
    title: str


@dataclass
class Block:
    """A group of items within an item set.

    Attributes:
        items (list[Item]): List of items in the block.
        type (str): Block title or category (e.g., "Core Items").
    """

    items: list[Item]
    type: str


@dataclass
class Item:
    """Individual item configuration.

    Attributes:
        count (int): Number of item units to display.
        id (str): Item identifier.
    """

    count: int
    id: str


@dataclass
class Payload_Perks(Payload):
    """Payload for the rune pages endpoint (/lol-perks/v1/pages).

    Attributes:
        name (str): Rune page name.
        primaryStyleId (int): Primary rune style ID.
        subStyleId (int): Secondary rune style ID.
        current (bool): Whether this is the current page. Defaults to True.
        selectedPerkIds (list[int] | None): List of selected perk IDs. Defaults to None.
    """

    name: str
    primaryStyleId: int
    subStyleId: int
    current: bool
    selectedPerkIds: list[int] | None = None


@dataclass
class Payload_Spells(Payload):
    """Payload for the spells endpoint (/lol-champ-select/v1/session/my-selection).

    Attributes:
        spell1Id (int): Summoner spell ID for the D key.
        spell2Id (int): Summoner spell ID for the F key.
        selectedSkinId (int): Selected champion skin ID.
    """

    spell1Id: int
    spell2Id: int
    selectedSkinId: int


@dataclass
class EventSchema:
    """Champion selection event data structure.

    Attributes:
        actions (list[Action]): List of champion selection actions.
        localPlayerCellId (int): Local player's cell ID.
        myTeam (list[Ally]): List of ally team members.
    """

    actions: list[Action]
    localPlayerCellId: int
    myTeam: list[Ally]


@dataclass
class Action:
    """Champion selection action.

    Attributes:
        actorCellId (int): Cell ID of the player performing the action.
        championId (int): Selected champion ID.
        completed (bool): Whether the action is completed.
        type (str): Type of action.
    """

    actorCellId: int
    championId: int
    completed: bool
    type: str


@dataclass
class Ally:
    """Ally team member information.

    Attributes:
        assignedPosition (str): Assigned lane or role.
        cellId (int): Player's cell ID.
        championId (int): Selected champion ID.
        selectedSkinId (int): Selected skin ID.
        summonerId (int): Player's summoner ID.
        wardSkinId (int): Selected ward skin ID.
    """

    assignedPosition: str
    cellId: int
    championId: int
    selectedSkinId: int
    summonerId: int
    wardSkinId: int
