#!/usr/bin/env python3
"""
Quick integration test for AgentManager with Cache Adapter.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import ConfigManager
from core.agent_manager import AgentManager
from storage.factory import StorageFactory
from storage.redis_cache import MemoryCacheAdapter


async def test_agent_manager_without_cache():
    """Test AgentManager without cache (backward compatibility)."""
    print("=" * 60)
    print("Test 1: AgentManager without Cache (Backward Compatibility)")
    print("=" * 60)

    config = ConfigManager()
    manager = AgentManager(config)

    await manager.initialize()
    print("✓ Initialized AgentManager without cache")

    # Verify cache is not available
    assert not manager.has_cache
    print("✓ Confirmed cache is not available")

    # Get cache stats
    stats = await manager.get_cache_stats()
    print(f"✓ Cache stats: {stats}")

    print()


async def test_agent_manager_with_cache():
    """Test AgentManager with MemoryCache."""
    print("=" * 60)
    print("Test 2: AgentManager with MemoryCache")
    print("=" * 60)

    # Create cache adapter
    cache = MemoryCacheAdapter({
        "max_size": 1000,
        "default_ttl": 300
    })
    await cache.initialize()
    print("✓ Initialized MemoryCache")

    # Create manager with cache
    config = ConfigManager()
    manager = AgentManager(config, cache_adapter=cache)

    await manager.initialize()
    print("✓ Initialized AgentManager with cache")

    # Verify cache is available
    assert manager.has_cache
    print("✓ Confirmed cache is available")

    # Test cache key generation
    cache_key = manager._generate_cache_key("test_agent", "Hello", {"arg": "value"})
    print(f"✓ Generated cache key: {cache_key}")

    # Test cache operations
    await cache.set(cache_key, ["response1", "response2"])
    cached = await cache.get(cache_key)
    print(f"✓ Cache set and get: {cached}")

    # Get cache stats
    stats = await manager.get_cache_stats()
    print(f"✓ Cache stats: {stats}")

    # Test clearing cache
    count = await manager.clear_agent_cache("test_agent")
    print(f"✓ Cleared {count} cache entries for test_agent")

    # Verify cleared
    stats_after = await manager.get_cache_stats()
    print(f"✓ Cache stats after clear: {stats_after}")

    await cache.close()
    print("✓ Closed cache")

    print()


async def main():
    """Run all integration tests."""
    print()
    print("AgentManager Cache Adapter Integration Tests")
    print()

    await test_agent_manager_without_cache()
    await test_agent_manager_with_cache()

    print("=" * 60)
    print("All Integration Tests Passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
