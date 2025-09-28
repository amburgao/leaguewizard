"""LeagueWizard main entry point."""

import asyncio
import os
import socket
from pathlib import Path

from loguru import logger

from leaguewizard.api.core import start
from leaguewizard.core.constants import LOG_DIR
from leaguewizard.core.exceptions import LeWizardGenericError

base_dir = os.getenv("LOCALAPPDATA", "tempfile.gettempdir()")
lewizard_dir = Path(base_dir, "LeagueWizard")
log_dir = Path(lewizard_dir, "logs")
log_dir.mkdir(parents=True, exist_ok=True)


def main() -> None:
    """LeagueWizard main entry point function."""
    LOG_DIR.mkdir(exist_ok=True, parents=True)
    logger.add(f"{LOG_DIR}/log.txt", rotation="1MB")
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 13463))
    except OSError as e:
        raise LeWizardGenericError(
            message="Another instance is already running",
            show=True,
            title="Error!",
            exit=True,
        ) from e

    asyncio.run(start())
