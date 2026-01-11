// Copyright (c) 2025 AInTandem
// SPDX-License-Identifier: MIT

/**
 * Configuration management for Round Table SDK
 */

/**
 * Configuration options for Round Table client
 */
export interface RoundTableConfigOptions {
  apiKey: string;
  baseURL?: string;
  timeout?: number;
  maxRetries?: number;
  verifySSL?: boolean;
  extraHeaders?: Record<string, string>;
}

/**
 * Round Table configuration class
 */
export class RoundTableConfig {
  public readonly apiKey: string;
  public readonly baseURL: string;
  public readonly timeout: number;
  public readonly maxRetries: number;
  public readonly verifySSL: boolean;
  public readonly extraHeaders: Record<string, string>;

  constructor(options: RoundTableConfigOptions) {
    this.apiKey = options.apiKey;
    this.timeout = options.timeout ?? 30000;
    this.maxRetries = options.maxRetries ?? 3;
    this.verifySSL = options.verifySSL ?? true;
    this.extraHeaders = options.extraHeaders ?? {};

    // Normalize and set base URL
    let baseURL = options.baseURL ?? 'http://localhost:8000/api/v1';
    baseURL = baseURL.endsWith('/') ? baseURL.slice(0, -1) : baseURL;

    // Ensure base URL includes /api/v1
    if (!baseURL.endsWith('/api/v1')) {
      baseURL = `${baseURL}/api/v1`;
    }

    this.baseURL = baseURL;
  }

  /**
   * Create configuration from environment variables
   */
  static fromEnv(): RoundTableConfig {
    const apiKey = process.env.ROUNDTABLE_API_KEY;

    if (!apiKey) {
      throw new Error('ROUNDTABLE_API_KEY environment variable is required');
    }

    return new RoundTableConfig({
      apiKey,
      baseURL: process.env.ROUNDTABLE_BASE_URL,
      timeout: process.env.ROUNDTABLE_TIMEOUT ? parseInt(process.env.ROUNDTABLE_TIMEOUT, 10) : undefined,
      maxRetries: process.env.ROUNDTABLE_MAX_RETRIES ? parseInt(process.env.ROUNDTABLE_MAX_RETRIES, 10) : undefined,
      verifySSL: process.env.ROUNDTABLE_VERIFY_SSL !== 'false',
    });
  }

  /**
   * Convert configuration to plain object
   */
  toJSON(): Record<string, unknown> {
    return {
      apiKey: this.apiKey,
      baseURL: this.baseURL,
      timeout: this.timeout,
      maxRetries: this.maxRetries,
      verifySSL: this.verifySSL,
      extraHeaders: this.extraHeaders,
    };
  }
}
