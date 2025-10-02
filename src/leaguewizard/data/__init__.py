"""League Wizard data path constants.

This module defines paths to important data files for the
League Wizard application. It includes the path to the
application's logo icon and the Riot Games certificate for
secure communication.
"""

from importlib.resources import files
from pathlib import Path

image_path = Path(str(files("leaguewizard.data.images") / "logo.ico"))
riot_cert_path = Path(str(files("leaguewizard.data.certs") / "riotgames.pem"))


__all__ = ["image_path", "riot_cert_path"]
