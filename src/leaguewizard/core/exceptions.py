"""Exceptions module for LeWizard."""

import sys
from tkinter import messagebox


class LeWizardGenericError(Exception):
    """Base custom exception error for LeagueWizard."""

    def __init__(
        self, message: str, show: bool = False, title: str = "", exit: bool = False
    ) -> None:
        """Initializes the LeWizardGenericError.

        Args:
            message (str): The error message.
            show (bool): If True, displays a message box with the error.
                Defaults to False.
            title (str): The title for the message box, if shown. Defaults to "".
            exit (bool): If True, exits the application after handling the error.
                Defaults to False.
        """
        super().__init__(message)
        if show:
            messagebox.showerror(title=title, message=message)
        if exit:
            sys.exit(0)
