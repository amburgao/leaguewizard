"""Exceptions module for LeWizard."""

import sys
from tkinter import messagebox


class LeWizardGenericError(Exception):
    """Base custom exception error for LeagueWizard."""

    def __init__(
        self, message: str, show: bool = False, title: str = "", exit: bool = False
    ) -> None:
        super().__init__(message)
        if show:
            messagebox.showerror(title=title, message=message)
        if exit:
            sys.exit()
