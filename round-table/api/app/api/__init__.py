# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""API routes package"""

from .workspaces import router as workspaces_router
from .sandboxes import router as sandboxes_router
from .messages import router as messages_router
from .collaborations import router as collaborations_router
from .system import router as system_router

__all__ = [
    "workspaces_router",
    "sandboxes_router",
    "messages_router",
    "collaborations_router",
    "system_router",
]
