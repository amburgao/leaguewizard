"""Exceptions module for LeWizard."""

import sys
from tkinter import messagebox


class LeWizardGenericError(Exception):
    """Base custom exception error for LeagueWizard."""

    def __init__(
        self,
        *,
        message: str = "",
        show: bool = False,
        title: str = "",
        terminate: bool = False,
    ) -> None:
        """Initializes the LeWizardGenericError.

        Args:
            message (str): The error message.
            show (bool): If True, displays a message box with the error.
                Defaults to False.
            title (str): The title for the message box, if shown. Defaults to "".
            terminate (bool): If True, exits the application after handling the error.
                Defaults to False.
        """
        super().__init__(message)
        if show:
            messagebox.showerror(title=title, message=message)
        if terminate:
            sys.exit(0)
