# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Configuration management for Round Table SDK.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoundTableConfig:
    """
    Configuration for Round Table SDK client.

    Attributes:
        api_key: API key or access token for authentication
        base_url: Base URL of the Round Table API
        timeout: Request timeout in seconds
        max_retries: Maximum number of retries for failed requests
        verify_ssl: Whether to verify SSL certificates
    """

    api_key: str
    base_url: str = "http://localhost:8000/api/v1"
    timeout: float = 30.0
    max_retries: int = 3
    verify_ssl: bool = True
    extra_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and normalize configuration."""
        # Ensure base_url doesn't have trailing slash
        self.base_url = self.base_url.rstrip("/")

        # Ensure base_url includes /api/v1
        if not self.base_url.endswith("/api/v1"):
            self.base_url = f"{self.base_url}/api/v1"

    @classmethod
    def from_env(cls) -> "RoundTableConfig":
        """
        Create configuration from environment variables.

        Environment variables:
            ROUNDTABLE_API_KEY: API key (required)
            ROUNDTABLE_BASE_URL: Base URL (default: http://localhost:8000/api/v1)
            ROUNDTABLE_TIMEOUT: Request timeout (default: 30)
            ROUNDTABLE_MAX_RETRIES: Max retries (default: 3)

        Returns:
            RoundTableConfig instance

        Raises:
            ValueError: If required environment variables are missing
        """
        api_key = os.getenv("ROUNDTABLE_API_KEY")
        if not api_key:
            raise ValueError("ROUNDTABLE_API_KEY environment variable is required")

        return cls(
            api_key=api_key,
            base_url=os.getenv("ROUNDTABLE_BASE_URL", "http://localhost:8000/api/v1"),
            timeout=float(os.getenv("ROUNDTABLE_TIMEOUT", "30")),
            max_retries=int(os.getenv("ROUNDTABLE_MAX_RETRIES", "3")),
            verify_ssl=os.getenv("ROUNDTABLE_VERIFY_SSL", "true").lower() == "true",
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "verify_ssl": self.verify_ssl,
            "extra_headers": self.extra_headers,
        }
