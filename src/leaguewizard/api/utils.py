"""Provides utilities for SSL context management.

This module contains functions for creating and configuring SSL contexts,
primarily for client connections, to interact with secure services.
It leverages the standard `ssl` library and custom certificate paths.
"""

import ssl
from pathlib import Path

from leaguewizard.data import riot_cert_path


def ssl_context(cert_path: Path = riot_cert_path) -> ssl.SSLContext:
    """Creates an SSL context for client connections.
    
    Args:
        cert_path: The path to the CA certificate file.
    
    Returns:
        An SSLContext object configured for client use.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cert_path)
    context.check_hostname = False
    return context
