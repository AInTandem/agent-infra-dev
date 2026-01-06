#!/usr/bin/env python3
"""
Test script for Sandbox Environment.

Tests sandbox manager, resource limiter, and security validator.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.sandbox import SandboxConfig, SandboxManager, create_sandbox_manager
from core.resource_limiter import (
    ResourceLimiter,
    SystemResourceMonitor,
    create_resource_limiter,
)
from core.security import (
    SecurityPolicy,
    SecurityValidator,
    create_security_validator,
    create_default_policy,
    create_strict_policy,
)


async def test_sandbox_manager():
    """Test Sandbox Manager functionality."""
    print("=" * 60)
    print("Sandbox Manager Tests")
    print("=" * 60)
    print()

    # Test 1: Create sandbox manager
    print("Test 1: Create Sandbox Manager")
    config = SandboxConfig(
        enabled=True,
        max_memory_mb=256,
        max_cpu_time=10,
        max_wall_time=30,
        network_access=False,
    )
    sandbox = create_sandbox_manager(config)
    print(f"  ✓ Sandbox manager created")
    print(f"    Enabled: {sandbox.config.enabled}")
    print(f"    Max memory: {sandbox.config.max_memory_mb}MB")
    print(f"    Network access: {sandbox.config.network_access}")
    print()

    # Test 2: Sandbox context
    print("Test 2: Sandbox Context")
    async with sandbox.create_sandbox("test_task_1") as ctx:
        print(f"  ✓ Sandbox created: {ctx['task_id']}")
        print(f"    Sandboxed: {ctx['sandboxed']}")
        print(f"    Temp dir: {ctx['tmp_dir']}")
    print(f"  ✓ Sandbox cleaned up")
    print()

    # Test 3: Path access control
    print("Test 3: Path Access Control")
    blocked = sandbox.check_path_access("/etc/passwd")
    print(f"  Blocked /etc/passwd: {not blocked}")
    allowed = sandbox.check_path_access("/tmp/test.txt")
    print(f"  Allowed /tmp/test.txt: {allowed}")
    print()

    # Test 4: Active sandboxes
    print("Test 4: Active Sandboxes")
    async with sandbox.create_sandbox("test_task_2") as ctx:
        active = sandbox.list_active_sandboxes()
        print(f"  Active sandboxes: {active}")
        info = sandbox.get_sandbox_info("test_task_2")
        print(f"  Sandbox info: {info['task_id']}")
    print()

    # Test 5: Sandbox stats
    print("Test 5: Sandbox Stats")
    stats = sandbox.get_stats()
    print(f"  Enabled: {stats['enabled']}")
    print(f"  Active sandboxes: {stats['active_sandboxes']}")
    print(f"  Max memory: {stats['max_memory_mb']}MB")
    print(f"  Network access: {stats['network_access']}")
    print()


async def test_resource_limiter():
    """Test Resource Limiter functionality."""
    print("=" * 60)
    print("Resource Limiter Tests")
    print("=" * 60)
    print()

    # Test 1: Create resource limiter
    print("Test 1: Create Resource Limiter")
    limiter = create_resource_limiter(
        max_cpu_percent=50.0,
        max_memory_mb=256.0,
        max_open_files=50,
        max_threads=5,
        check_interval=0.5,
    )
    print(f"  ✓ Resource limiter created")
    print(f"    Max CPU: {limiter.max_cpu_percent}%")
    print(f"    Max memory: {limiter.max_memory_mb}MB")
    print(f"    Max open files: {limiter.max_open_files}")
    print()

    # Test 2: Current metrics
    print("Test 2: Current Metrics")
    metrics = limiter.get_current_metrics()
    print(f"  CPU: {metrics.cpu_percent:.1f}%")
    print(f"  Memory: {metrics.memory_mb:.1f}MB ({metrics.memory_percent:.1f}%)")
    print(f"  Open files: {metrics.open_files}")
    print(f"  Threads: {metrics.num_threads}")
    print()

    # Test 3: Resource limiting context
    print("Test 3: Resource Limiting Context")

    async def violation_callback(task_id, violations):
        print(f"    Violations for {task_id}: {violations}")

    async with limiter.limit_resources("test_task", violation_callback):
        print(f"  ✓ Resource limiting started")
        await asyncio.sleep(1)
        print(f"  ✓ Resource limiting stopped")
    print()

    # Test 4: System stats
    print("Test 4: System Stats")
    system_stats = SystemResourceMonitor.get_system_stats()
    print(f"  CPU: {system_stats['cpu']['percent']:.1f}%")
    print(f"  CPU count: {system_stats['cpu']['count']}")
    if system_stats.get('memory'):
        print(f"  Memory: {system_stats['memory']['percent']:.1f}%")
        print(f"    Available: {system_stats['memory']['available_mb']:.1f}MB")
    if system_stats.get('disk'):
        print(f"  Disk: {system_stats['disk']['percent']:.1f}%")
        print(f"    Free: {system_stats['disk']['free_mb']:.1f}MB")
    print()

    # Test 5: Limiter stats
    print("Test 5: Limiter Stats")
    stats = limiter.get_stats()
    print(f"  Monitoring: {stats['monitoring']}")
    print(f"  Violations: {stats['violations']}")
    print()


async def test_security_validator():
    """Test Security Validator functionality."""
    print("=" * 60)
    print("Security Validator Tests")
    print("=" * 60)
    print()

    # Test 1: Default policy
    print("Test 1: Default Policy")
    default_policy = create_default_policy()
    print(f"  ✓ Default policy created")
    print(f"    Command execution: {default_policy.allow_command_execution}")
    print(f"    File write: {default_policy.allow_file_write}")
    print(f"    Network access: {default_policy.allow_network_access}")
    print()

    # Test 2: Strict policy
    print("Test 2: Strict Policy")
    strict_policy = create_strict_policy()
    print(f"  ✓ Strict policy created")
    print(f"    Command execution: {strict_policy.allow_command_execution}")
    print(f"    File write: {strict_policy.allow_file_write}")
    print(f"    Network access: {strict_policy.allow_network_access}")
    print()

    # Test 3: Input validation
    print("Test 3: Input Validation")
    validator = create_security_validator(default_policy)

    valid, error = validator.validate_input("Hello, world!")
    print(f"  Valid input: {valid}")

    invalid, error = validator.validate_input("rm -rf /")
    print(f"  Dangerous command: {not valid}")
    if error:
        print(f"    Error: {error}")

    invalid, error = validator.validate_input("cat /etc/passwd")
    print(f"  Sensitive file: {not valid}")
    if error:
        print(f"    Error: {error}")
    print()

    # Test 4: Command validation
    print("Test 4: Command Validation")
    validator2 = create_security_validator(SecurityPolicy(allow_command_execution=True))

    valid, error = validator2.validate_command(["ls", "-la"])
    print(f"  Valid command: {valid}")

    invalid, error = validator2.validate_command(["rm", "-rf", "/"])
    print(f"  Dangerous command: {not valid}")
    if error:
        print(f"    Error: {error}")
    print()

    # Test 5: File path validation
    print("Test 5: File Path Validation")
    valid, error = validator.validate_file_path("/tmp/test.txt", "read")
    print(f"  Valid path: {valid}")

    invalid, error = validator.validate_file_path("/etc/passwd", "read")
    print(f"  Sensitive path: {not invalid}")
    if error:
        print(f"    Error: {error}")
    print()

    # Test 6: URL validation
    print("Test 6: URL Validation")
    validator3 = create_security_validator(
        SecurityPolicy(
            allow_network_access=True,
            allowed_domains=["example.com", "google.com"],
        )
    )

    valid, error = validator3.validate_network_url("https://example.com/test")
    print(f"  Allowed domain: {valid}")

    invalid, error = validator3.validate_network_url("https://evil.com/test")
    print(f"  Blocked domain: {not invalid}")
    if error:
        print(f"    Error: {error}")
    print()

    # Test 7: Input sanitization
    print("Test 7: Input Sanitization")
    dirty = "Hello\x00   World   "
    clean = validator.sanitize_input(dirty)
    print(f"  Original: {repr(dirty)}")
    print(f"  Sanitized: {repr(clean)}")
    print()

    # Test 8: Violations tracking
    print("Test 8: Violations Tracking")
    validator.validate_input("rm -rf /")
    validator.validate_input("cat /etc/passwd")
    violations = validator.get_violations()
    print(f"  Violations: {len(violations)}")
    for v in violations:
        print(f"    - {v['type']}: {v.get('pattern', v.get('command', v.get('path', 'N/A')))}")
    print()


async def main():
    """Run all tests."""
    # Test sandbox manager
    await test_sandbox_manager()

    # Test resource limiter
    await test_resource_limiter()

    # Test security validator
    await test_security_validator()

    print()
    print("=" * 60)
    print("Sandbox Environment Tests Complete! ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
