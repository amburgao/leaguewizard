"""Defines Pydantic models for various LeagueClientUpdates payloads and event schemas.

These models are used for serializing and deserializing data exchanged with the
League of Legends client, ensuring type safety and data validation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Payload(BaseModel):
    """Base class for all payload models, providing common serialization."""

    def asjson(self) -> dict[str, Any]:
        """Converts the model instance to a dictionary, using aliases for field names.

        Returns:
            dict[str, Any]: A dictionary representation of the model.
        """
        return self.model_dump(by_alias=True)


class PayloadItemSets(Payload):
    """Payload for the itemsets endpoint (/lol-item-sets/v1/item-sets/{accountId}/sets).

    Attributes:
        account_id (int): Summoner account ID.
        item_sets (list[ItemSet]): List of item sets. Defaults to None.
        timestamp (int): Timestamp value. Defaults to 1 (unused).
    """

    account_id: int = Field(..., alias="accountId")
    item_sets: list[ItemSet] = Field(..., alias="itemSets")
    timestamp: int = 1


class ItemSet(Payload):
    """Represents a single item set configuration.

    Attributes:
        associated_champions (list[int]): Champion IDs this set applies to.
        blocks (list[Block]): List of item blocks in the set.
        title (str): Name of the item set (e.g., "Ezreal - ADC").
    """

    associated_champions: list[int] = Field(..., alias="associatedChampions")
    blocks: list[Block]
    title: str


class Block(BaseModel):
    """A group of items within an item set.

    Attributes:
        items (list[Item]): List of items in the block.
        type (str): Block title or category (e.g., "Core Items").
    """

    items: list[Item]
    type: str


class Item(BaseModel):
    """Individual item configuration.

    Attributes:
        count (int): Number of item units to display.
        id (str): Item identifier.
    """

    count: int
    id: str


class PayloadPerks(Payload):
    """Payload for the rune pages endpoint (/lol-perks/v1/pages).

    Attributes:
        name (str): Rune page name.
        primary_style_id (int): Primary rune style ID.
        sub_style_id (int): Secondary rune style ID.
        current (bool): Whether this is the current page. Defaults to True.
        selected_perk_ids (list[int]): List of selected perk IDs.
    """

    name: str
    primary_style_id: int = Field(..., alias="primaryStyleId")
    sub_style_id: int = Field(..., alias="subStyleId")
    current: bool
    selected_perk_ids: list[int] = Field(..., alias="selectedPerkIds")


class PayloadSpells(Payload):
    """Payload for the spells endpoint (/lol-champ-select/v1/session/my-selection).

    Attributes:
        spell1_id (int): Summoner spell ID for the D key.
        spell2_id (int): Summoner spell ID for the F key.
        selected_skin_id (int): Selected champion skin ID.
    """

    spell1_id: int = Field(..., alias="spell1Id")
    spell2_id: int = Field(..., alias="spell2Id")
    selected_skin_id: int = Field(..., alias="selectedSkinId")


class EventSchema(Payload):
    """Champion selection event data structure.

    Attributes:
        actions (list[Action]): List of champion selection actions.
        local_player_cell_id (int): Local player's cell ID.
        my_team (list[Ally]): List of ally team members.
    """

    actions: list[Action]
    local_player_cell_id: int = Field(..., alias="localPlayerCellId")
    my_team: list[Ally] = Field(..., alias="myTeam")


class Action(Payload):
    """Champion selection action.

    Attributes:
        actor_cell_id (int): Cell ID of the player performing the action.
        champion_id (int): Selected champion ID.
        completed (bool): Whether the action is completed.
        type (str): Type of action.
    """

    actor_cell_id: int = Field(..., alias="actorCellId")
    champion_id: int = Field(..., alias="championId")
    completed: bool
    type: str


class Ally(Payload):
    """Ally team member information.

    Attributes:
        assigned_position (str): Assigned lane or role.
        cell_id (int): Player's cell ID.
        champion_id (int): Selected champion ID.
        selected_skin_id (int): Selected skin ID.
        summoner_id (int): Player's summoner ID.
        wardSkin_id (int): Selected ward skin ID.
    """

    assigned_position: str = Field(..., alias="assignedPosition")
    cell_id: int = Field(..., alias="cellId")
    champion_id: int = Field(..., alias="championId")
    selected_skin_id: int = Field(..., alias="selectedSkinId")
    summoner_id: int = Field(..., alias="summonerId")
    ward_skin_id: int = Field(..., alias="wardSkinId")
