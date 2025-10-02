"""Manages the League of Legends lockfile.

This module provides the `LockFile` class to parse the League of Legends
lockfile and extract necessary connection details for interacting with
the client's API.

Classes:
    LockFile: Manages parsing the lockfile for API connection details.
"""

import base64
from pathlib import Path

from pydantic import BaseModel, Field


class LockFile:
    """Class to manage League of Legends lockfile.

    Handles parsing the lockfile to extract connection details for the
    League client API.

    Attributes:
        exe (str): Path to the League of Legends executable.
        https_addr (str | None): The HTTPS address for the League client API.
        wss_addr (str | None): The WSS address for the League client API.
        auth_header (dict[str, str] | None): The Authorization header for API
            requests.
    """

    def __init__(self, league_exe: str | Path) -> None:
        """Initializes the LeagueClient.

        Args:
            league_exe: Path to the League of Legends executable.
        """
        self.exe: str | Path = league_exe

        self.lockfile_path: Path = self._lockfile(self.exe)

        self._https_addr: str | None = None
        self._wss_addr: str | None = None
        self._auth_header: dict[str, str] | None = None
        self._port: str | None = None
        self._password: str | None = None

        self._parse()

    def _parse(self) -> None:
        with self.lockfile_path.open(encoding="utf-8") as f:
            parts: list[str] = f.read().split(":")

        self._port = parts[2]
        self._password = parts[3]

        full_addr: str = f"127.0.0.1:{self._port}"

        full_password: str | None = (
            "riot:" + self._password if self._password is not None else None
        )
        auth_string: str = base64.b64encode(
            bytes(str(full_password), "utf-8"),
        ).decode()

        self._https_addr = f"https://{full_addr}"
        self._wss_addr = f"wss://{full_addr}"
        self._auth_header = {"Authorization": f"Basic {auth_string}"}

    @property
    def https_addr(self) -> str | None:
        """Gets the HTTPS address.

        Returns:
            The HTTPS address as a string, or None if not set.
        """
        return self._https_addr

    @property
    def wss_addr(self) -> str | None:
        """Gets the WebSocket server address.

        Returns:
            The WebSocket server address string, or None if not set.
        """
        return self._wss_addr

    @property
    def auth_header(self) -> dict[str, str] | None:
        """Returns the authentication header.

        Returns:
            A dictionary of authentication headers, or None if none exist.
        """
        return self._auth_header

    @staticmethod
    def _lockfile(exe: str | Path) -> Path:
        return Path(exe).parent / "lockfile"


class SummonerData(BaseModel):
    """Data class for summoner information.

    Attributes:
        account_id (str): The unique account ID of the summoner.
        id (str): The unique summoner ID.
        name (str): The summoner's name.
        profile_icon_id (int): The ID of the summoner's profile icon.
        puuid (str): The platform-unique ID of the summoner.
        revision_date (int): The last modified date of the summoner's
            account.
        summoner_level (int): The summoner's level.
    """

    assigned_position: str = Field(alias="assignedPosition")
    cell_id: int = Field(alias="cellId")
    champion_id: int = Field(alias="championId")
    champion_pick_intent: int = Field(alias="championPickIntent")
    selected_skin_id: int = Field(alias="selectedSkinId")
    ward_skin_id: int = Field(alias="wardSkinId")
    summoner_id: int = Field(alias="summonerId")
