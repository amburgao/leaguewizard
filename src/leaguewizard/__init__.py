"""LeagueWizard main entry point."""

import asyncio
import os
import tempfile
import threading
import urllib
from pathlib import Path
from typing import Any

import pystray
from loguru import logger
from PIL import Image

from leaguewizard.core import start
from leaguewizard.exceptions import LeWizardGenericError

logfile = Path(tempfile.gettempdir(), "logs")
if not logfile.exists():
    logfile.mkdir(parents=True, exist_ok=True)
logger.add(f"{str(logfile)}/leaguewiz_log.log", rotation="1 MB")


def to_tray() -> Any:
    """Create the tray icon with exit action.

    Returns:
        Any: Must be a pystray Icon object.
    """
    dest = f"{tempfile.gettempdir()}\\logo.png"
    urllib.request.urlretrieve(
        "https://github.com/amburgao/leaguewizard/blob/main/.github/images/logo.png?raw=true",
        dest,
    )
    return pystray.Icon(
        (0, 0),
        icon=Image.open(dest),
        menu=pystray.Menu(pystray.MenuItem("Exit", lambda icon, item: os._exit(0))),
    )


def main() -> None:
    """LeagueWizard main entry point function."""
    import socket

    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 54321))
    except OSError as e:
        raise LeWizardGenericError(
            message="Another instance is already running",
            show=True,
            title="Error!",
            exit=True,
        ) from e

    tray = to_tray()
    tray_thread = threading.Thread(target=tray.run, daemon=True)
    tray_thread.start()

    asyncio.run(start())
    tray.stop()


if __name__ == "__main__":
    main()
