# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Round Table Python SDK

A Python SDK for interacting with the Round Table Collaboration Bus API.
"""

from __future__ import annotations

from roundtable.client import RoundTableClient
from roundtable.config import RoundTableConfig
from roundtable.exceptions import (
    RoundTableError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
)
from roundtable.models import (
    Workspace,
    Sandbox,
    AgentMessage,
    Collaboration,
)

__version__ = "0.1.0"
__all__ = [
    "RoundTableClient",
    "RoundTableConfig",
    "RoundTableError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "Workspace",
    "Sandbox",
    "AgentMessage",
    "Collaboration",
]
