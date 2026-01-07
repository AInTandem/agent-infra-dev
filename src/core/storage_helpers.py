"""
Storage helper functions for creating adapters from configuration.
"""

import logging
from typing import Any, Dict, Optional

from storage.factory import StorageFactory, create_storage, create_cache
from .config import ConfigManager

logger = logging.getLogger(__name__)


async def create_storage_from_config(
    config_manager: Optional[ConfigManager] = None
) -> Optional[Any]:
    """
    Create a storage adapter from configuration.

    Args:
        config_manager: Configuration manager instance

    Returns:
        StorageAdapter instance or None (if using file-based storage)
    """
    if config_manager is None:
        config_manager = ConfigManager()

    storage_config = config_manager.storage
    storage_type = storage_config.get("storage", {}).get("type", "file")

    # File-based storage (default, backward compatible)
    if storage_type == "file":
        logger.info("Using file-based storage for tasks")
        return None

    # Database storage
    try:
        storage = create_storage(storage_config.get("storage", {}))
        await storage.initialize()
        logger.info(f"Initialized {storage_type} storage adapter")
        return storage
    except Exception as e:
        logger.error(f"Failed to create storage adapter: {e}")
        raise


async def create_cache_from_config(
    config_manager: Optional[ConfigManager] = None
) -> Optional[Any]:
    """
    Create a cache adapter from configuration.

    Args:
        config_manager: Configuration manager instance

    Returns:
        CacheAdapter instance or None (if caching is disabled)
    """
    if config_manager is None:
        config_manager = ConfigManager()

    storage_config = config_manager.storage
    cache_config = storage_config.get("cache")

    # No cache configured
    if not cache_config:
        logger.info("Cache is disabled")
        return None

    # Cache type "none" or not enabled
    cache_type = cache_config.get("type", "none")
    if cache_type == "none" or not cache_config.get("enabled", True):
        logger.info("Cache is disabled")
        return None

    try:
        cache = create_cache(cache_config)
        if cache:
            await cache.initialize()
            logger.info(f"Initialized {cache_type} cache adapter")
        return cache
    except Exception as e:
        logger.error(f"Failed to create cache adapter: {e}")
        # Return None to continue without cache
        return None


async def create_adapters_from_config(
    config_manager: Optional[ConfigManager] = None
) -> tuple[Optional[Any], Optional[Any]]:
    """
    Create both storage and cache adapters from configuration.

    Args:
        config_manager: Configuration manager instance

    Returns:
        Tuple of (storage_adapter, cache_adapter)
    """
    if config_manager is None:
        config_manager = ConfigManager()

    storage = await create_storage_from_config(config_manager)
    cache = await create_cache_from_config(config_manager)

    return storage, cache
