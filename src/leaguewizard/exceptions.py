"""Exceptions module for LeWizard."""

from typing import Any


class LeWizardGenericError(Exception):
    """Base custom exception error for LeagueWizard."""

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
