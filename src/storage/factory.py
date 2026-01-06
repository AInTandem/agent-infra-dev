"""
Storage Factory

Factory pattern for creating storage adapters based on configuration.
"""

import logging
from typing import Dict, Any, Optional, Type

from .base_adapter import StorageAdapter
from .base_cache import CacheAdapter
from .base_vector_store import VectorStoreAdapter

logger = logging.getLogger(__name__)


# Registry for storage adapters
_STORAGE_ADAPTERS: Dict[str, Type[StorageAdapter]] = {}
_CACHE_ADAPTERS: Dict[str, Type[CacheAdapter]] = {}
_VECTOR_STORE_ADAPTERS: Dict[str, Type[VectorStoreAdapter]] = {}


def register_storage_adapter(name: str):
    """
    Decorator to register a storage adapter class.

    Usage:
        @register_storage_adapter("sqlite")
        class SQLiteAdapter(StorageAdapter):
            ...
    """
    def decorator(cls: Type[StorageAdapter]) -> Type[StorageAdapter]:
        _STORAGE_ADAPTERS[name.lower()] = cls
        logger.debug(f"Registered storage adapter: {name}")
        return cls
    return decorator


def register_cache_adapter(name: str):
    """
    Decorator to register a cache adapter class.

    Usage:
        @register_cache_adapter("redis")
        class RedisCacheAdapter(CacheAdapter):
            ...
    """
    def decorator(cls: Type[CacheAdapter]) -> Type[CacheAdapter]:
        _CACHE_ADAPTERS[name.lower()] = cls
        logger.debug(f"Registered cache adapter: {name}")
        return cls
    return decorator


def register_vector_store_adapter(name: str):
    """
    Decorator to register a vector store adapter class.

    Usage:
        @register_vector_store_adapter("qdrant")
        class QdrantAdapter(VectorStoreAdapter):
            ...
    """
    def decorator(cls: Type[VectorStoreAdapter]) -> Type[VectorStoreAdapter]:
        _VECTOR_STORE_ADAPTERS[name.lower()] = cls
        logger.debug(f"Registered vector store adapter: {name}")
        return cls
    return decorator


class StorageFactory:
    """
    Factory for creating storage adapters.

    This factory supports:
    - Storage adapters (SQLite, PostgreSQL)
    - Cache adapters (Redis, in-memory)
    - Vector store adapters (Qdrant, Milvus, Pinecone)
    """

    @staticmethod
    def create_storage(config: Dict[str, Any]) -> StorageAdapter:
        """
        Create a storage adapter from configuration.

        Config format:
        {
            "type": "sqlite" | "postgresql",
            "sqlite": {...},  # SQLite-specific config
            "postgresql": {...}  # PostgreSQL-specific config
        }

        Args:
            config: Configuration dictionary

        Returns:
            Storage adapter instance

        Raises:
            ValueError: If storage type is not registered
        """
        storage_type = config.get("type", "").lower()

        if not storage_type:
            raise ValueError("Storage type must be specified in config")

        adapter_class = _STORAGE_ADAPTERS.get(storage_type)
        if adapter_class is None:
            available = ", ".join(_STORAGE_ADAPTERS.keys())
            raise ValueError(
                f"Unknown storage type: {storage_type}. "
                f"Available types: {available}"
            )

        # Get storage-specific config
        storage_config = config.get(storage_type, {})
        merged_config = {**config, **storage_config}

        logger.info(f"Creating {storage_type} storage adapter")
        return adapter_class(merged_config)

    @staticmethod
    def create_cache(config: Optional[Dict[str, Any]]) -> Optional[CacheAdapter]:
        """
        Create a cache adapter from configuration.

        Config format:
        {
            "type": "redis" | "memory",
            "redis": {...},  # Redis-specific config
            "memory": {...}  # Memory-specific config
        }

        Args:
            config: Configuration dictionary or None

        Returns:
            Cache adapter instance or None if config is None/empty

        Raises:
            ValueError: If cache type is not registered
        """
        if not config:
            return None

        cache_type = config.get("type", "").lower()

        if not cache_type or cache_type == "none":
            return None

        adapter_class = _CACHE_ADAPTERS.get(cache_type)
        if adapter_class is None:
            available = ", ".join(_CACHE_ADAPTERS.keys())
            raise ValueError(
                f"Unknown cache type: {cache_type}. "
                f"Available types: {available}"
            )

        # Get cache-specific config
        cache_config = config.get(cache_type, {})
        merged_config = {**config, **cache_config}

        logger.info(f"Creating {cache_type} cache adapter")
        return adapter_class(merged_config)

    @staticmethod
    def create_vector_store(config: Optional[Dict[str, Any]]) -> Optional[VectorStoreAdapter]:
        """
        Create a vector store adapter from configuration.

        Config format:
        {
            "type": "qdrant" | "milvus" | "pinecone",
            "qdrant": {...},  # Qdrant-specific config
            "milvus": {...}  # Milvus-specific config
        }

        Args:
            config: Configuration dictionary or None

        Returns:
            Vector store adapter instance or None if config is None/empty

        Raises:
            ValueError: If vector store type is not registered
        """
        if not config:
            return None

        store_type = config.get("type", "").lower()

        if not store_type or store_type == "none":
            return None

        adapter_class = _VECTOR_STORE_ADAPTERS.get(store_type)
        if adapter_class is None:
            available = ", ".join(_VECTOR_STORE_ADAPTERS.keys())
            raise ValueError(
                f"Unknown vector store type: {store_type}. "
                f"Available types: {available}"
            )

        # Get vector store-specific config
        store_config = config.get(store_type, {})
        merged_config = {**config, **store_config}

        logger.info(f"Creating {store_type} vector store adapter")
        return adapter_class(merged_config)

    @staticmethod
    def list_storage_adapters() -> list[str]:
        """List registered storage adapter types."""
        return list(_STORAGE_ADAPTERS.keys())

    @staticmethod
    def list_cache_adapters() -> list[str]:
        """List registered cache adapter types."""
        return list(_CACHE_ADAPTERS.keys())

    @staticmethod
    def list_vector_store_adapters() -> list[str]:
        """List registered vector store adapter types."""
        return list(_VECTOR_STORE_ADAPTERS.keys())


# Convenience function for creating storage
def create_storage(config: Dict[str, Any]) -> StorageAdapter:
    """
    Convenience function for creating a storage adapter.

    Args:
        config: Configuration dictionary

    Returns:
        Storage adapter instance
    """
    return StorageFactory.create_storage(config)


def create_cache(config: Optional[Dict[str, Any]]) -> Optional[CacheAdapter]:
    """
    Convenience function for creating a cache adapter.

    Args:
        config: Configuration dictionary or None

    Returns:
        Cache adapter instance or None
    """
    return StorageFactory.create_cache(config)


def create_vector_store(config: Optional[Dict[str, Any]]) -> Optional[VectorStoreAdapter]:
    """
    Convenience function for creating a vector store adapter.

    Args:
        config: Configuration dictionary or None

    Returns:
        Vector store adapter instance or None
    """
    return StorageFactory.create_vector_store(config)
