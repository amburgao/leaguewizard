"""LeagueWizard main entry point."""

import asyncio
import socket
from datetime import datetime, timezone

from loguru import logger

from leaguewizard.api.core import start
from leaguewizard.core.constants import LOG_DIR
from leaguewizard.core.exceptions import LeWizardGenericError


def main() -> None:
    """LeagueWizard main entry point function."""
    LOG_DIR.mkdir(exist_ok=True, parents=True)
    logger.add(
        LOG_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')}.log",
    )
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 13463))
    except OSError as e:
        raise LeWizardGenericError(
            message="Another instance is already running",
            show=True,
            title="Error!",
            terminate=True,
        ) from e

    asyncio.run(start())
