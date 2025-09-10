from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Payload:
    def asdict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Payload_ItemSets(Payload):
    _endpoint_put_template = "/lol-item-sets/v1/item-sets/{accountId}/sets"
    accountId: int
    itemSets: list[ItemSet] | None = None
    timestamp: int = 1
    itemsets_css = ".m-l9l2ov > .m-yare96 > .m-1d3w5wq"

    @property
    def endpoint_put(self) -> str:
        return self._endpoint_put_template.format(accountId=self.accountId)


@dataclass
class ItemSet:
    associatedChampions: list[int]
    blocks: list[Block]
    title: str


@dataclass
class Block:
    items: list[Item]
    type: str


@dataclass
class Item:
    count: int
    id: str


@dataclass
class Payload_Perks(Payload):
    endpoint_get = "/lol-perks/v1/currentpage"
    _endpoint_delete_template = "/lol-perks/v1/pages/{pageId}"
    endpoint_post = "/lol-perks/v1/pages"

    main_perks_css = ".m-68x97p"
    selected_perks_css = (".m-1iebrlh", ".m-1nx2cdb", ".m-1u3ui07")

    name: str
    primaryStyleId: int
    subStyleId: int
    current: bool
    selectedPerkIds: list[int] | None = None

    _page_id: str | None = None

    @property
    def endpoint_delete(self) -> str:
        return self._endpoint_delete_template.format(pageId=self._page_id)

    @endpoint_delete.setter
    def endpoint_delete(self, page_id: str) -> None:
        self._page_id = page_id


@dataclass
class Payload_Spells(Payload):
    endpoint_patch = "/lol-champ-select/v1/session/my-selection"
    spell1Id: int
    spell2Id: int
    selectedSkinId: int

    spells_css = ".m-d3vnz1"


@dataclass
class EventSchema:
    actions: list[Action]
    localPlayerCellId: int
    myTeam: list[Ally]


@dataclass
class Action:
    actorCellId: int
    championId: int
    completed: bool
    type: str


@dataclass
class Ally:
    assignedPosition: str
    cellId: int
    championId: int
    selectedSkinId: int
    summonerId: int
    wardSkinId: int
