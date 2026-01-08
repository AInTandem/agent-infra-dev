"""
Storage Adapter Layer for AInTandem Agent MCP Scheduler

This module provides abstract storage interfaces and implementations for:
- Personal Edition: SQLite-based storage
- Enterprise Edition: PostgreSQL + Redis storage
- Future: Vector databases (Qdrant, Milvus, Pinecone)
"""

from .base_adapter import StorageAdapter
from .base_cache import CacheAdapter
from .base_vector_store import VectorStoreAdapter
from .factory import StorageFactory, create_storage

# Import adapters to register them with the factory
# These imports trigger the @register_* decorators
from . import sqlite_adapter  # noqa: F401
from . import postgres_adapter  # noqa: F401
from . import redis_cache  # noqa: F401

__all__ = [
    "StorageAdapter",
    "CacheAdapter",
    "VectorStoreAdapter",
    "StorageFactory",
    "create_storage",
]
