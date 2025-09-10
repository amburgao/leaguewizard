"""LeagueWizard main entry point."""

import asyncio
import os
import sys
import tempfile
import threading
import urllib
import urllib.request
from typing import Any

import pystray
import win32api
import win32event
import win32security
import winerror
from PIL import Image

from leaguewizard.core import start


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


def already_running_error() -> None:
    """Keep only one process running at system.

    Raises:
        RuntimeWarning: Another instance is already running error.
    """
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            0,
            "Another instance is already running. Close it to create a new one.",
            "Warn!",
            48,
        )
        raise RuntimeWarning("Another instance is already running.")
    except RuntimeWarning:
        sys.exit(1)


def main() -> None:
    """LeagueWizard main entry point function."""
    win32event.CreateMutex(
        win32security.SECURITY_ATTRIBUTES(), False, "leaguewizardlock"
    )
    last_error = win32api.GetLastError()
    if last_error == winerror.ERROR_ALREADY_EXISTS:
        already_running_error()

    tray = to_tray()
    tray_thread = threading.Thread(target=tray.run, daemon=True)
    tray_thread.start()

    asyncio.run(start())
    tray.stop()


if __name__ == "__main__":
    main()
