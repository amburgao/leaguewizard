"""Exceptions module for LeWizard."""

import sys


class LeWizardGenericError(Exception):
    """Base custom exception error for LeagueWizard."""

    def __init__(
        self, message: str, show: bool = False, title: str = "", exit: bool = False
    ) -> None:
        super().__init__(message)
        if show:
            from tkinter import messagebox

            messagebox.showerror(title=title, message=message)
        if exit:
            sys.exit()
