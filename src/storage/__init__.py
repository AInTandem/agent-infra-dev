"""
Storage Adapter Layer for Qwen Agent MCP Scheduler

This module provides abstract storage interfaces and implementations for:
- Personal Edition: SQLite-based storage
- Enterprise Edition: PostgreSQL + Redis storage
- Future: Vector databases (Qdrant, Milvus, Pinecone)
"""

from .base_adapter import StorageAdapter
from .base_cache import CacheAdapter
from .base_vector_store import VectorStoreAdapter
from .factory import StorageFactory, create_storage

__all__ = [
    "StorageAdapter",
    "CacheAdapter",
    "VectorStoreAdapter",
    "StorageFactory",
    "create_storage",
]
