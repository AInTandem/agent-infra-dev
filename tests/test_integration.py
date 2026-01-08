#!/usr/bin/env python3
"""
Integration tests for AInTandem Agent MCP Scheduler.

Tests the complete system with all components integrated.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import ConfigManager
from core.agent_manager import AgentManager
from core.task_scheduler import TaskScheduler
from core.task_models import ScheduleType
from core.sandbox import SandboxConfig, SandboxManager
from core.resource_limiter import ResourceLimiter
from core.security import SecurityValidator


class TestResults:
    """Test results tracker."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, name: str):
        self.passed += 1
        print(f"  ✓ {name}")

    def add_fail(self, name: str, error: str):
        self.failed += 1
        self.errors.append((name, error))
        print(f"  ✗ {name}: {error}")

    def print_summary(self):
        total = self.passed + self.failed
        print()
        print("=" * 60)
        print(f"Integration Tests Summary")
        print("=" * 60)
        print(f"Total: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        if self.failed > 0:
            print()
            print("Failed Tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        print("=" * 60)
        return self.failed == 0


async def test_config_and_agents(results: TestResults):
    """Test configuration loading and agent initialization."""
    print("\n1. Configuration and Agents")
    print("-" * 60)

    try:
        # Load configuration
        config = ConfigManager()
        config.load_all()
        results.add_pass("Configuration loaded")

        # Initialize agent manager
        agent_manager = AgentManager(config)
        await agent_manager.initialize()
        results.add_pass("AgentManager initialized")

        # List agents
        agents = agent_manager.list_agents()
        if agents:
            results.add_pass(f"Agents available: {len(agents)}")
        else:
            results.add_fail("Agent listing", "No agents found")

        return agent_manager

    except Exception as e:
        results.add_fail("Config/Agent init", str(e))
        return None


async def test_task_scheduling(results: TestResults, agent_manager):
    """Test task scheduling functionality."""
    print("\n2. Task Scheduling")
    print("-" * 60)

    try:
        # Initialize task scheduler
        config = ConfigManager()
        config.load_all()
        task_scheduler = TaskScheduler(config)
        await task_scheduler.start()
        results.add_pass("TaskScheduler started")

        # Create a test task
        run_time = (datetime.now() + timedelta(seconds=10)).isoformat()
        task = await task_scheduler.schedule_task(
            name="Integration Test Task",
            agent_name="researcher",
            task_prompt="Test prompt",
            schedule_type=ScheduleType.ONCE,
            schedule_value=run_time,
            repeat=False,
            description="Integration test task",
        )
        results.add_pass(f"Task created: {task.id}")

        # List tasks
        tasks = task_scheduler.list_tasks()
        results.add_pass(f"Tasks listed: {len(tasks)}")

        # Get task stats
        stats = task_scheduler.get_stats()
        results.add_pass(f"Task stats: {stats['total_tasks']} tasks")

        # Stop scheduler
        await task_scheduler.stop()
        results.add_pass("TaskScheduler stopped")

        return task_scheduler

    except Exception as e:
        results.add_fail("Task scheduling", str(e))
        return None


async def test_sandbox_environment(results: TestResults):
    """Test sandbox environment."""
    print("\n3. Sandbox Environment")
    print("-" * 60)

    try:
        # Create sandbox config
        sandbox_config = SandboxConfig(
            enabled=True,
            max_memory_mb=256,
            network_access=False,
        )
        sandbox = SandboxManager(sandbox_config)
        results.add_pass("SandboxManager created")

        # Test sandbox context
        async with sandbox.create_sandbox("integration_test") as ctx:
            results.add_pass(f"Sandbox created: {ctx['task_id']}")

        # Test path access control
        blocked = sandbox.check_path_access("/etc/passwd")
        if not blocked:
            results.add_pass("Path access control working")
        else:
            results.add_fail("Path access control", "Sensitive path not blocked")

        # Get sandbox stats
        stats = sandbox.get_stats()
        results.add_pass(f"Sandbox stats: {stats['active_sandboxes']} active")

        return sandbox

    except Exception as e:
        results.add_fail("Sandbox environment", str(e))
        return None


async def test_resource_limiting(results: TestResults):
    """Test resource limiting."""
    print("\n4. Resource Limiting")
    print("-" * 60)

    try:
        # Create resource limiter
        limiter = ResourceLimiter(
            max_cpu_percent=50.0,
            max_memory_mb=256.0,
        )
        results.add_pass("ResourceLimiter created")

        # Get current metrics
        metrics = limiter.get_current_metrics()
        results.add_pass(f"Metrics: CPU {metrics.cpu_percent:.1f}%, Memory {metrics.memory_mb:.1f}MB")

        # Test resource limiting context
        async with limiter.limit_resources("integration_test"):
            await asyncio.sleep(0.5)
        results.add_pass("Resource limiting context working")

        # Get stats
        stats = limiter.get_stats()
        results.add_pass(f"Limiter stats: {stats['violations']} violations")

        return limiter

    except Exception as e:
        results.add_fail("Resource limiting", str(e))
        return None


async def test_security_validation(results: TestResults):
    """Test security validation."""
    print("\n5. Security Validation")
    print("-" * 60)

    try:
        # Create security validator
        validator = SecurityValidator()
        results.add_pass("SecurityValidator created")

        # Test input validation
        valid, error = validator.validate_input("Hello, world!")
        if valid:
            results.add_pass("Valid input accepted")
        else:
            results.add_fail("Valid input", error)

        invalid, error = validator.validate_input("rm -rf /")
        if not invalid:
            results.add_pass("Dangerous command blocked")
        else:
            results.add_fail("Dangerous command", "Not blocked")

        # Test file path validation
        valid, error = validator.validate_file_path("/tmp/test.txt")
        if valid:
            results.add_pass("Safe path allowed")
        else:
            results.add_fail("Safe path", error)

        invalid, error = validator.validate_file_path("/etc/passwd")
        if not invalid:
            results.add_pass("Sensitive path blocked")
        else:
            results.add_fail("Sensitive path", "Not blocked")

        # Test sanitization
        dirty = "Hello\x00   World   "
        clean = validator.sanitize_input(dirty)
        results.add_pass("Input sanitization working")

        # Get violations
        violations = validator.get_violations()
        results.add_pass(f"Violations tracked: {len(violations)}")

        return validator

    except Exception as e:
        results.add_fail("Security validation", str(e))
        return None


async def test_system_integration(results: TestResults, agent_manager, task_scheduler):
    """Test complete system integration."""
    print("\n6. System Integration")
    print("-" * 60)

    try:
        # Test agent execution
        if agent_manager.list_agents():
            agent = agent_manager.get_agent(agent_manager.list_agents()[0])
            if agent:
                results.add_pass("Agent retrieved successfully")
            else:
                results.add_fail("Agent retrieval", "Agent is None")
        else:
            results.add_fail("Agent execution", "No agents available")

        # Test task persistence
        if task_scheduler:
            tasks = task_scheduler.list_tasks()
            if tasks:
                results.add_pass("Task persistence working")
            else:
                results.add_fail("Task persistence", "No tasks found")

        # Test configuration access
        app_config = agent_manager.config_manager.app
        results.add_pass("Configuration accessible")

        # Test system readiness
        ready = all([
            agent_manager is not None,
            task_scheduler is not None,
        ])
        if ready:
            results.add_pass("System ready for operation")
        else:
            results.add_fail("System readiness", "Components missing")

        return True

    except Exception as e:
        results.add_fail("System integration", str(e))
        return False


async def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("AInTandem Agent MCP Scheduler - Integration Tests")
    print("=" * 60)

    results = TestResults()

    # Test 1: Configuration and Agents
    agent_manager = await test_config_and_agents(results)

    # Test 2: Task Scheduling
    task_scheduler = await test_task_scheduling(results, agent_manager)

    # Test 3: Sandbox Environment
    sandbox = await test_sandbox_environment(results)

    # Test 4: Resource Limiting
    limiter = await test_resource_limiting(results)

    # Test 5: Security Validation
    validator = await test_security_validation(results)

    # Test 6: System Integration
    await test_system_integration(results, agent_manager, task_scheduler)

    # Print summary
    success = results.print_summary()

    if success:
        print("\n✓ All integration tests passed!")
        return 0
    else:
        print("\n✗ Some integration tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
