# Copyright (c) 2025 AInTandem
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Security Policies for AInTandem Agent MCP Scheduler.

Provides security validation, sanitization, and policy enforcement.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


# ============================================================================
# Security Policy Configuration
# ============================================================================

class SecurityPolicy:
    """
    Security policy configuration.

    Defines rules for:
    - Command execution
    - File system access
    - Network access
    - Input validation
    - Output sanitization
    """

    # Dangerous commands/patterns to block
    DANGEROUS_COMMANDS = [
        r"rm\s+-rf\s+/",
        r"dd\s+if=/dev/zero",
        r":\(\)\{\}:\;",
        r"chmod\s+000\s+/",
        r"mkfs\.",
        r"format\s+c:",
        r"curl.*\|.*sh",
        r"wget.*\|.*sh",
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__\s*\(",
    ]

    # Sensitive file patterns to block
    SENSITIVE_PATTERNS = [
        r"/etc/passwd",
        r"/etc/shadow",
        r"/etc/sudoers",
        r"/root/\.ssh",
        r"\.ssh/id_rsa",
        r"\.ssh/id_ed25519",
        r"\.gnupg",
        r"\.aws/credentials",
        r"\.env",
        r"secret",
        r"password",
        r"token",
    ]

    # Allowed file extensions
    ALLOWED_EXTENSIONS = [
        ".txt", ".md", ".json", ".yaml", ".yml",
        ".csv", ".log", ".py", ".js", ".ts",
        ".html", ".css", ".xml",
    ]

    # Maximum file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    # Maximum input length
    MAX_INPUT_LENGTH = 10000

    def __init__(
        self,
        allow_command_execution: bool = False,
        allow_file_write: bool = True,
        allow_network_access: bool = True,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
    ):
        """
        Initialize security policy.

        Args:
            allow_command_execution: Allow command execution
            allow_file_write: Allow file write operations
            allow_network_access: Allow network access
            allowed_domains: List of allowed domains
            blocked_domains: List of blocked domains
        """
        self.allow_command_execution = allow_command_execution
        self.allow_file_write = allow_file_write
        self.allow_network_access = allow_network_access
        self.allowed_domains = allowed_domains or []
        self.blocked_domains = blocked_domains or [
            "malware.com",
            "evil.com",
        ]

        # Compile regex patterns
        self.dangerous_patterns = [re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_COMMANDS]
        self.sensitive_patterns = [re.compile(p, re.IGNORECASE) for p in self.SENSITIVE_PATTERNS]


# ============================================================================
# Security Validator
# ============================================================================

class SecurityValidator:
    """
    Validates inputs and actions against security policies.
    """

    def __init__(self, policy: Optional[SecurityPolicy] = None):
        """
        Initialize the security validator.

        Args:
            policy: Security policy to enforce
        """
        self.policy = policy or SecurityPolicy()
        self._violations: List[Dict[str, Any]] = []

    def validate_input(self, input_str: str) -> tuple[bool, Optional[str]]:
        """
        Validate user input.

        Args:
            input_str: Input string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not input_str:
            return True, None

        # Check length
        if len(input_str) > self.policy.MAX_INPUT_LENGTH:
            return False, f"Input exceeds maximum length of {self.policy.MAX_INPUT_LENGTH}"

        # Check for dangerous patterns
        for pattern in self.policy.dangerous_patterns:
            if pattern.search(input_str):
                violation = f"Dangerous pattern detected: {pattern.pattern}"
                logger.warning(f"Security violation: {violation}")
                self._violations.append({
                    "type": "dangerous_pattern",
                    "pattern": pattern.pattern,
                    "input": input_str[:100],
                })
                return False, violation

        # Check for sensitive file access
        for pattern in self.policy.sensitive_patterns:
            if pattern.search(input_str):
                violation = f"Sensitive file access detected: {pattern.pattern}"
                logger.warning(f"Security violation: {violation}")
                self._violations.append({
                    "type": "sensitive_file",
                    "pattern": pattern.pattern,
                    "input": input_str[:100],
                })
                return False, violation

        return True, None

    def validate_command(self, command: List[str]) -> tuple[bool, Optional[str]]:
        """
        Validate command execution.

        Args:
            command: Command list to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.policy.allow_command_execution:
            return False, "Command execution is not allowed"

        command_str = " ".join(command)

        # Check for dangerous commands
        for pattern in self.policy.dangerous_patterns:
            if pattern.search(command_str):
                violation = f"Dangerous command detected: {pattern.pattern}"
                logger.warning(f"Security violation: {violation}")
                self._violations.append({
                    "type": "dangerous_command",
                    "pattern": pattern.pattern,
                    "command": command_str[:100],
                })
                return False, violation

        return True, None

    def validate_file_path(self, file_path: str, mode: str = "read") -> tuple[bool, Optional[str]]:
        """
        Validate file path access.

        Args:
            file_path: File path to validate
            mode: Access mode (read, write, execute)

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for sensitive files
        for pattern in self.policy.sensitive_patterns:
            if pattern.search(file_path):
                violation = f"Sensitive file access detected: {pattern.pattern}"
                logger.warning(f"Security violation: {violation}")
                self._violations.append({
                    "type": "sensitive_file",
                    "pattern": pattern.pattern,
                    "path": file_path,
                })
                return False, violation

        # Check write permissions
        if mode == "write" and not self.policy.allow_file_write:
            return False, "File write is not allowed"

        # Normalize path
        try:
            normalized_path = Path(file_path).resolve()
        except Exception as e:
            return False, f"Invalid path: {e}"

        # Check if path exists
        if not normalized_path.exists():
            return True, None  # New files are OK

        # Check if path is a file
        if not normalized_path.is_file():
            return False, "Path is not a file"

        # Check file size
        try:
            file_size = normalized_path.stat().st_size
            if file_size > self.policy.MAX_FILE_SIZE:
                return False, f"File exceeds maximum size of {self.policy.MAX_FILE_SIZE} bytes"
        except Exception as e:
            return False, f"Cannot access file: {e}"

        return True, None

    def validate_network_url(self, url: str) -> tuple[bool, Optional[str]]:
        """
        Validate network URL.

        Args:
            url: URL to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.policy.allow_network_access:
            return False, "Network access is not allowed"

        # Extract domain
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check blocked domains
            for blocked in self.policy.blocked_domains:
                if blocked in domain:
                    return False, f"Domain {blocked} is blocked"

            # Check allowed domains (if specified)
            if self.policy.allowed_domains:
                allowed = False
                for allowed_domain in self.policy.allowed_domains:
                    if allowed_domain in domain:
                        allowed = True
                        break
                if not allowed:
                    return False, f"Domain {domain} is not in allowed list"

        except Exception as e:
            return False, f"Invalid URL: {e}"

        return True, None

    def sanitize_input(self, input_str: str) -> str:
        """
        Sanitize input string.

        Args:
            input_str: Input string to sanitize

        Returns:
            Sanitized string
        """
        if not input_str:
            return ""

        # Remove null bytes
        sanitized = input_str.replace("\x00", "")

        # Trim excessive whitespace
        sanitized = " ".join(sanitized.split())

        # Limit length
        if len(sanitized) > self.policy.MAX_INPUT_LENGTH:
            sanitized = sanitized[:self.policy.MAX_INPUT_LENGTH]

        return sanitized

    def sanitize_output(self, output_str: str) -> str:
        """
        Sanitize output string.

        Args:
            output_str: Output string to sanitize

        Returns:
            Sanitized string
        """
        if not output_str:
            return ""

        # Remove null bytes
        sanitized = output_str.replace("\x00", "")

        # Remove ANSI escape codes
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        sanitized = ansi_escape.sub('', sanitized)

        return sanitized

    def get_violations(self) -> List[Dict[str, Any]]:
        """Get list of security violations."""
        return self._violations.copy()

    def clear_violations(self):
        """Clear violation history."""
        self._violations.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get security validator statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "allow_command_execution": self.policy.allow_command_execution,
            "allow_file_write": self.policy.allow_file_write,
            "allow_network_access": self.policy.allow_network_access,
            "violations": len(self._violations),
            "blocked_domains": len(self.policy.blocked_domains),
            "allowed_domains": len(self.policy.allowed_domains),
        }


# ============================================================================
# Factory Functions
# ============================================================================

def create_security_validator(policy: Optional[SecurityPolicy] = None) -> SecurityValidator:
    """
    Create a security validator.

    Args:
        policy: Security policy to enforce

    Returns:
        SecurityValidator instance
    """
    return SecurityValidator(policy)


def create_default_policy() -> SecurityPolicy:
    """
    Create default security policy.

    Returns:
        SecurityPolicy with default settings
    """
    return SecurityPolicy(
        allow_command_execution=False,
        allow_file_write=True,
        allow_network_access=True,
    )


def create_strict_policy() -> SecurityPolicy:
    """
    Create strict security policy.

    Returns:
        SecurityPolicy with strict settings
    """
    return SecurityPolicy(
        allow_command_execution=False,
        allow_file_write=False,
        allow_network_access=False,
    )
