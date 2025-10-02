"""Core module for LeagueWizard, handling LCU connection and event processing.

This module establishes a connection to the League of Legends client (LCU) via
WebSocket, retrieves necessary authentication details, and dispatches incoming
game events to the `on_message` handler. It also manages the system tray icon.
"""

from __future__ import annotations

import asyncio
import os
import random
import sys
from pathlib import Path
from typing import Any

import aiohttp
import psutil
import websockets
from infi.systray import SysTrayIcon
from loguru import logger

from leaguewizard.api.callback_handler import on_message
from leaguewizard.api.models import LockFile
from leaguewizard.api.utils import ssl_context
from leaguewizard.core.exceptions import LeWizardGenericError
from leaguewizard.data import image_path


def find_client_full_path(exe: str = "LeagueClient.exe") -> Path:
    """Finds the full path of the League of Legends client executable.

    Args:
        exe: The name of the executable to find. Defaults to "LeagueClient.exe".

    Returns:
        The full path to the executable as a `pathlib.Path` object.

    Raises:
        LeWizardGenericError: If the executable is not found.
    """
    proc_path: Any = next(
        (i.exe() for i in psutil.process_iter() if i.name() == exe),
        None,
    )
    if proc_path is None:
        raise LeWizardGenericError(
            message=f"{exe} not found. Is client running?",
            show=True,
            title="Error.",
            terminate=True,
        )
    return Path(proc_path)


async def start() -> None:
    """Initializes the application, connects to the LCU, and starts listening events.

    Raises:
        LeWizardGenericError: If 'LeagueClient.exe' or 'LeagueClientUx.exe'
            is not found.

    Returns:
        None: This function runs indefinitely until interrupted.
    """
    with SysTrayIcon(
        str(image_path),
        "LeagueWizard",
        on_quit=lambda e: os._exit(0),
    ) as tray:
        logger.debug("Tray initialized")
        try:
            league_client = find_client_full_path()
            logger.debug(f"Client found: {league_client}")
            lockfile = LockFile(league_client)
            logger.debug(f"Lockfile found: {lockfile.lockfile_path}")
            context = ssl_context()
            assert lockfile.wss_addr is not None  # noqa: S101
            async with websockets.connect(
                uri=lockfile.wss_addr,
                additional_headers=lockfile.auth_header,
                ssl=context,
            ) as ws:
                logger.debug("Joining websocket session.")

                await ws.send('[5, "OnJsonApiEvent_lol-champ-select_v1_session"]')
                logger.debug(
                    "Subscribed to OnJsonApiEvent_lol-champ-select_v1_session.",
                )
                aio_client = aiohttp.ClientSession(
                    base_url=lockfile.https_addr,
                    headers=lockfile.auth_header,
                )
                aio_client_id = random.randint(0, 1000)  # noqa: S311
                async for event in ws:
                    logger.debug("Event received.")
                    min_event_length = 3
                    if event is not None and len(event) >= min_event_length:
                        await on_message(
                            event,
                            aio_client,
                            aio_client_id,
                        )

        except websockets.exceptions.ConnectionClosedError as e:
            logger.exception(e.args)

        except (KeyboardInterrupt, asyncio.exceptions.CancelledError) as e:
            logger.exception(e.args)
            raise LeWizardGenericError(show=False, terminate=True) from e

        finally:
            tray.shutdown()
            sys.exit(0)
