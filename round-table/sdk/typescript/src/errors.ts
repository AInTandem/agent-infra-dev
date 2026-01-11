// Copyright (c) 2025 AInTandem
// SPDX-License-Identifier: MIT

/**
 * Custom exceptions for Round Table SDK
 */

/**
 * Base error class for all Round Table SDK errors
 */
export class RoundTableError extends Error {
  public readonly statusCode?: number;
  public readonly response?: unknown;

  constructor(message: string, statusCode?: number, response?: unknown) {
    super(message);
    this.name = 'RoundTableError';
    this.statusCode = statusCode;
    this.response = response;

    // Maintains proper stack trace for where our error was thrown (only available on V8)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, RoundTableError);
    }
  }

  toString(): string {
    if (this.statusCode) {
      return `[${this.statusCode}] ${this.message}`;
    }
    return this.message;
  }
}

/**
 * Authentication error (401)
 */
export class AuthenticationError extends RoundTableError {
  constructor(message: string = 'Authentication failed', response?: unknown) {
    super(message, 401, response);
    this.name = 'AuthenticationError';
  }
}

/**
 * Forbidden error (403)
 */
export class ForbiddenError extends RoundTableError {
  constructor(message: string = 'Access forbidden', response?: unknown) {
    super(message, 403, response);
    this.name = 'ForbiddenError';
  }
}

/**
 * Not found error (404)
 */
export class NotFoundError extends RoundTableError {
  constructor(message: string = 'Resource not found', response?: unknown) {
    super(message, 404, response);
    this.name = 'NotFoundError';
  }
}

/**
 * Bad request error (400)
 */
export class BadRequestError extends RoundTableError {
  constructor(message: string = 'Bad request', response?: unknown) {
    super(message, 400, response);
    this.name = 'BadRequestError';
  }
}

/**
 * Validation error (422)
 */
export class ValidationError extends RoundTableError {
  constructor(message: string = 'Validation failed', response?: unknown) {
    super(message, 422, response);
    this.name = 'ValidationError';
  }
}

/**
 * Conflict error (409)
 */
export class ConflictError extends RoundTableError {
  constructor(message: string = 'Resource conflict', response?: unknown) {
    super(message, 409, response);
    this.name = 'ConflictError';
  }
}

/**
 * Rate limit error (429)
 */
export class RateLimitError extends RoundTableError {
  public readonly retryAfter?: number;

  constructor(message: string = 'Rate limit exceeded', response?: unknown, retryAfter?: number) {
    super(message, 429, response);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

/**
 * Server error (500+)
 */
export class ServerError extends RoundTableError {
  constructor(message: string = 'Server error', statusCode: number = 500, response?: unknown) {
    super(message, statusCode, response);
    this.name = 'ServerError';
  }
}

/**
 * Connection error
 */
export class ConnectionError extends RoundTableError {
  constructor(message: string = 'Connection error', response?: unknown) {
    super(message, undefined, response);
    this.name = 'ConnectionError';
  }
}

/**
 * Raise appropriate error based on status code
 */
export function raiseForStatus(response: { success: boolean; status_code?: number; message?: string; data?: unknown }): void {
  if (response.success) {
    return;
  }

  const statusCode = response.status_code || 0;
  const message = response.message || 'Unknown error';

  const errorMap: Record<number, new (msg: string, data?: unknown) => RoundTableError> = {
    400: BadRequestError,
    401: AuthenticationError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    422: ValidationError,
    429: RateLimitError,
  };

  const ErrorClass = errorMap[statusCode];

  if (ErrorClass) {
    throw new ErrorClass(message, response.data);
  } else if (statusCode >= 500) {
    throw new ServerError(message, statusCode, response.data);
  } else if (statusCode >= 400) {
    throw new RoundTableError(message, statusCode, response.data);
  }
}
