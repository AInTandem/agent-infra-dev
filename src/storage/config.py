"""
Storage Configuration Models

Pydantic models for storage configuration validation.
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class StorageType(str, Enum):
    """Supported storage types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class CacheType(str, Enum):
    """Supported cache types."""
    REDIS = "redis"
    MEMORY = "memory"
    NONE = "none"


class VectorStoreType(str, Enum):
    """Supported vector store types."""
    QDRANT = "qdrant"
    MILVUS = "milvus"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    CHROMA = "chroma"
    NONE = "none"


class SQLiteConfig(BaseModel):
    """SQLite storage configuration."""
    path: str = Field(default="./storage/data.db", description="Path to SQLite database file")
    pool_size: int = Field(default=5, ge=1, le=20, description="Connection pool size")
    enable_wal: bool = Field(default=True, description="Enable WAL mode for better concurrency")
    journal_mode: str = Field(default="WAL", description="Journal mode (WAL, DELETE, TRUNCATE, etc.)")

    @field_validator("journal_mode")
    @classmethod
    def validate_journal_mode(cls, v: str) -> str:
        valid_modes = ["DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"]
        v = v.upper()
        if v not in valid_modes:
            raise ValueError(f"journal_mode must be one of {valid_modes}")
        return v


class PostgreSQLConfig(BaseModel):
    """PostgreSQL storage configuration."""
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    database: str = Field(default="qwen_agent", description="Database name")
    user: str = Field(default="qwen", description="Database user")
    password: str = Field(default="", description="Database password")
    pool_size: int = Field(default=20, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(default=40, ge=0, le=100, description="Max overflow connections")
    pool_recycle: int = Field(default=3600, ge=0, description="Connection recycle time in seconds")
    echo: bool = Field(default=False, description="Echo SQL statements")
    ssl_mode: Optional[str] = Field(default=None, description="SSL mode (require, verify-ca, verify-full)")


class RedisConfig(BaseModel):
    """Redis cache configuration."""
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Redis password")
    pool_size: int = Field(default=10, ge=1, le=50, description="Connection pool size")
    socket_timeout: float = Field(default=5.0, ge=0.1, description="Socket timeout in seconds")
    socket_connect_timeout: float = Field(default=5.0, ge=0.1, description="Connection timeout")
    decode_responses: bool = Field(default=True, description="Decode responses to strings")
    ssl: bool = Field(default=False, description="Use SSL connection")


class MemoryCacheConfig(BaseModel):
    """In-memory cache configuration."""
    max_size: int = Field(default=1000, ge=1, description="Maximum number of items")
    default_ttl: int = Field(default=300, ge=0, description="Default TTL in seconds")


class QdrantConfig(BaseModel):
    """Qdrant vector store configuration."""
    url: Optional[str] = Field(default=None, description="Qdrant server URL")
    host: Optional[str] = Field(default=None, description="Qdrant host (for gRPC)")
    port: Optional[int] = Field(default=None, ge=1, le=65535, description="Qdrant port")
    api_key: Optional[str] = Field(default=None, description="Qdrant API key")
    grpc_port: Optional[int] = Field(default=None, description="Qdrant gRPC port")
    prefer_grpc: bool = Field(default=False, description="Prefer gRPC over HTTP")
    timeout: float = Field(default=5.0, ge=0.1, description="Request timeout")
    https: bool = Field(default=False, description="Use HTTPS")


class MilvusConfig(BaseModel):
    """Milvus vector store configuration."""
    host: str = Field(default="localhost", description="Milvus host")
    port: int = Field(default=19530, ge=1, le=65535, description="Milvus port")
    user: Optional[str] = Field(default=None, description="Milvus user")
    password: Optional[str] = Field(default=None, description="Milvus password")
    database: str = Field(default="default", description="Milvus database name")
    timeout: float = Field(default=10.0, ge=0.1, description="Request timeout")


class PineconeConfig(BaseModel):
    """Pinecone vector store configuration."""
    api_key: str = Field(..., description="Pinecone API key")
    environment: str = Field(..., description="Pinecone environment")
    project_name: Optional[str] = Field(default=None, description="Pinecone project name")


class CacheConfig(BaseModel):
    """Cache configuration."""
    type: CacheType = Field(default=CacheType.NONE, description="Cache backend type")
    redis: Optional[RedisConfig] = Field(default=None, description="Redis configuration")
    memory: Optional[MemoryCacheConfig] = Field(default=None, description="Memory cache configuration")
    enabled: bool = Field(default=True, description="Enable caching")

    @field_validator("redis")
    @classmethod
    def validate_redis_config(cls, v: Optional[RedisConfig], info) -> Optional[RedisConfig]:
        if info.data.get("type") == CacheType.REDIS and v is None:
            return RedisConfig()  # Use defaults
        return v

    @field_validator("memory")
    @classmethod
    def validate_memory_config(cls, v: Optional[MemoryCacheConfig], info) -> Optional[MemoryCacheConfig]:
        if info.data.get("type") == CacheType.MEMORY and v is None:
            return MemoryCacheConfig()  # Use defaults
        return v


class VectorStoreConfig(BaseModel):
    """Vector store configuration."""
    type: VectorStoreType = Field(default=VectorStoreType.NONE, description="Vector store type")
    qdrant: Optional[QdrantConfig] = Field(default=None, description="Qdrant configuration")
    milvus: Optional[MilvusConfig] = Field(default=None, description="Milvus configuration")
    pinecone: Optional[PineconeConfig] = Field(default=None, description="Pinecone configuration")
    default_collection: str = Field(default="qwen_agent", description="Default collection name")
    embedding_model: str = Field(default="text-embedding-ada-002", description="Embedding model name")

    @field_validator("qdrant")
    @classmethod
    def validate_qdrant_config(cls, v: Optional[QdrantConfig], info) -> Optional[QdrantConfig]:
        if info.data.get("type") == VectorStoreType.QDRANT and v is None:
            return QdrantConfig()  # Use defaults
        return v


class StorageConfig(BaseModel):
    """Complete storage configuration."""
    model_config = {"populate_by_name": True}

    type: StorageType = Field(default=StorageType.SQLITE, description="Storage backend type")
    sqlite: Optional[SQLiteConfig] = Field(default=None, description="SQLite configuration")
    postgresql: Optional[PostgreSQLConfig] = Field(default=None, description="PostgreSQL configuration")

    cache: Optional[CacheConfig] = Field(default=None, description="Cache configuration")
    vector_store: Optional[VectorStoreConfig] = Field(default=None, description="Vector store configuration")

    @field_validator("sqlite")
    @classmethod
    def validate_sqlite_config(cls, v: Optional[SQLiteConfig], info) -> Optional[SQLiteConfig]:
        if info.data.get("type") == StorageType.SQLITE and v is None:
            return SQLiteConfig()  # Use defaults
        return v

    @field_validator("postgresql")
    @classmethod
    def validate_postgres_config(cls, v: Optional[PostgreSQLConfig], info) -> Optional[PostgreSQLConfig]:
        if info.data.get("type") == StorageType.POSTGRESQL and v is None:
            return PostgreSQLConfig()  # Use defaults
        return v


# Model rebuild for forward references
StorageConfig.model_rebuild()
CacheConfig.model_rebuild()
VectorStoreConfig.model_rebuild()


def load_storage_config(config_dict: Dict[str, Any]) -> StorageConfig:
    """
    Load and validate storage configuration.

    Args:
        config_dict: Raw configuration dictionary

    Returns:
        Validated StorageConfig model
    """
    return StorageConfig(**config_dict)


def load_cache_config(config_dict: Optional[Dict[str, Any]]) -> Optional[CacheConfig]:
    """
    Load and validate cache configuration.

    Args:
        config_dict: Raw configuration dictionary or None

    Returns:
        Validated CacheConfig model or None
    """
    if not config_dict:
        return None
    return CacheConfig(**config_dict)


def load_vector_store_config(config_dict: Optional[Dict[str, Any]]) -> Optional[VectorStoreConfig]:
    """
    Load and validate vector store configuration.

    Args:
        config_dict: Raw configuration dictionary or None

    Returns:
        Validated VectorStoreConfig model or None
    """
    if not config_dict:
        return None
    return VectorStoreConfig(**config_dict)
