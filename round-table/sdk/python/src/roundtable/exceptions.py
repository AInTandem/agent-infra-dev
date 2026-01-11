# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Custom exceptions for Round Table SDK.
"""

from __future__ import annotations

from typing import Any


class RoundTableError(Exception):
    """
    Base exception for all Round Table SDK errors.

    Attributes:
        message: Error message
        status_code: HTTP status code (if applicable)
        response: Full response data (if applicable)
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class AuthenticationError(RoundTableError):
    """
    Raised when authentication fails.

    This can occur when:
    - Invalid API key or access token
    - Expired token
    - Missing authentication headers
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        status_code: int = 401,
        response: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code, response)


class NotFoundError(RoundTableError):
    """
    Raised when a requested resource is not found.

    This can occur when:
    - Workspace doesn't exist
    - Sandbox doesn't exist
    - Message doesn't exist
    - Collaboration doesn't exist
    """

    def __init__(
        self,
        message: str = "Resource not found",
        status_code: int = 404,
        response: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code, response)


class ValidationError(RoundTableError):
    """
    Raised when request validation fails.

    This can occur when:
    - Invalid request parameters
    - Missing required fields
    - Invalid data format
    """

    def __init__(
        self,
        message: str = "Validation failed",
        status_code: int = 422,
        response: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code, response)


class RateLimitError(RoundTableError):
    """
    Raised when rate limit is exceeded.

    This can occur when:
    - Too many requests in a short time period
    - API quota exceeded
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        status_code: int = 429,
        response: dict[str, Any] | None = None,
        retry_after: int | None = None,
    ):
        super().__init__(message, status_code, response)
        self.retry_after = retry_after


class ForbiddenError(RoundTableError):
    """
    Raised when access is forbidden.

    This can occur when:
    - User doesn't have permission to access a resource
    - Attempting to access another user's workspace
    - Invalid authorization for the operation
    """

    def __init__(
        self,
        message: str = "Access forbidden",
        status_code: int = 403,
        response: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code, response)


class BadRequestError(RoundTableError):
    """
    Raised when the request is malformed.

    This can occur when:
    - Invalid JSON in request body
    - Malformed request URL
    - Invalid query parameters
    """

    def __init__(
        self,
        message: str = "Bad request",
        status_code: int = 400,
        response: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code, response)


class ConflictError(RoundTableError):
    """
    Raised when there's a conflict with the current state.

    This can occur when:
    - Resource already exists
    - Duplicate entry
    - Concurrent modification conflict
    """

    def __init__(
        self,
        message: str = "Resource conflict",
        status_code: int = 409,
        response: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code, response)


class ServerError(RoundTableError):
    """
    Raised when the server encounters an error.

    This can occur when:
    - Internal server error
    - Service unavailable
    - Gateway timeout
    """

    def __init__(
        self,
        message: str = "Server error",
        status_code: int = 500,
        response: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code, response)


class ConnectionError(RoundTableError):
    """
    Raised when there's a connection error.

    This can occur when:
    - Network is unreachable
    - DNS resolution fails
    - Connection timeout
    """

    def __init__(
        self,
        message: str = "Connection error",
        status_code: int = None,
        response: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code, response)


def raise_for_status(response: dict[str, Any]) -> None:
    """
    Raise an appropriate exception based on response status code.

    Args:
        response: Response dictionary with 'success' and 'status_code' keys

    Raises:
        AuthenticationError: If status code is 401
        ForbiddenError: If status code is 403
        NotFoundError: If status code is 404
        BadRequestError: If status code is 400
        ValidationError: If status code is 422
        RateLimitError: If status code is 429
        ConflictError: If status code is 409
        ServerError: If status code is 500 or higher
        RoundTableError: For other error codes
    """
    status_code = response.get("status_code", 0)
    message = response.get("message", "Unknown error")

    exception_map = {
        400: BadRequestError,
        401: AuthenticationError,
        403: ForbiddenError,
        404: NotFoundError,
        409: ConflictError,
        422: ValidationError,
        429: RateLimitError,
    }

    exception_class = exception_map.get(status_code)
    if exception_class:
        raise exception_class(message, status_code, response)
    elif status_code >= 500:
        raise ServerError(message, status_code, response)
    elif status_code >= 400:
        raise RoundTableError(message, status_code, response)
