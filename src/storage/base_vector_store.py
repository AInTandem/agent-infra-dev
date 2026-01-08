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
Vector Store Adapter Abstract Base Class

Defines the interface for vector database implementations.
Designed for future RAG (Retrieval Augmented Generation) support.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union


class VectorStoreAdapter(ABC):
    """
    Abstract base class for vector store adapters.

    All vector store implementations (Qdrant, Milvus, Pinecone, etc.) must
    inherit from this class and implement all abstract methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the vector store adapter.

        Args:
            config: Configuration dictionary for the vector store
        """
        self.config = config
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the vector store backend.

        This should establish connections and create collections.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close the vector store connection and cleanup resources.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the vector store is accessible.

        Returns:
            True if healthy, False otherwise
        """
        pass

    # Collection Management

    @abstractmethod
    async def create_collection(
        self,
        name: str,
        vector_size: int,
        distance: str = "cosine"
    ) -> bool:
        """
        Create a new collection.

        Args:
            name: Collection name
            vector_size: Size of embedding vectors
            distance: Distance metric (cosine, euclid, dot)

        Returns:
            True if created, False if already exists
        """
        pass

    @abstractmethod
    async def delete_collection(self, name: str) -> bool:
        """
        Delete a collection.

        Args:
            name: Collection name

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def list_collections(self) -> List[str]:
        """
        List all collections.

        Returns:
            List of collection names
        """
        pass

    @abstractmethod
    async def collection_exists(self, name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            name: Collection name

        Returns:
            True if exists, False otherwise
        """
        pass

    # Document Operations

    @abstractmethod
    async def add_documents(
        self,
        collection: str,
        documents: List[str],
        embeddings: Optional[List[List[float]]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents to vector store.

        Args:
            collection: Collection name
            documents: List of document texts
            embeddings: Optional pre-computed embeddings
            metadata: Optional metadata for each document
            ids: Optional document IDs

        Returns:
            List of document IDs
        """
        pass

    @abstractmethod
    async def get_documents(
        self,
        collection: str,
        ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get documents by IDs.

        Args:
            collection: Collection name
            ids: List of document IDs

        Returns:
            List of documents with metadata
        """
        pass

    @abstractmethod
    async def delete_documents(
        self,
        collection: str,
        ids: List[str]
    ) -> int:
        """
        Delete documents by IDs.

        Args:
            collection: Collection name
            ids: List of document IDs

        Returns:
            Number of deleted documents
        """
        pass

    @abstractmethod
    async def update_documents(
        self,
        collection: str,
        documents: List[Dict[str, Any]]
    ) -> int:
        """
        Update documents in collection.

        Args:
            collection: Collection name
            documents: List of documents with id and updated fields

        Returns:
            Number of updated documents
        """
        pass

    # Search Operations

    @abstractmethod
    async def search(
        self,
        collection: str,
        query: str,
        query_embedding: Optional[List[float]] = None,
        limit: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.

        Args:
            collection: Collection name
            query: Query text (will be embedded if query_embedding not provided)
            query_embedding: Optional pre-computed query embedding
            limit: Maximum number of results
            filter: Optional metadata filter
            score_threshold: Minimum similarity score

        Returns:
            List of search results with scores
        """
        pass

    @abstractmethod
    async def hybrid_search(
        self,
        collection: str,
        query: str,
        text_query: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        limit: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        alpha: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining vector and keyword search.

        Args:
            collection: Collection name
            query: Query text
            text_query: Optional specific text query for keyword search
            query_embedding: Optional pre-computed query embedding
            limit: Maximum number of results
            filter: Optional metadata filter
            alpha: Balance between vector (0) and keyword (1) search

        Returns:
            List of search results with combined scores
        """
        pass

    # Batch Operations

    @abstractmethod
    async def upsert_documents(
        self,
        collection: str,
        documents: List[Dict[str, Any]]
    ) -> int:
        """
        Insert or update documents.

        Args:
            collection: Collection name
            documents: List of documents with id field

        Returns:
            Number of upserted documents
        """
        pass

    # Utility Methods

    def is_initialized(self) -> bool:
        """
        Check if the vector store has been initialized.

        Returns:
            True if initialized, False otherwise
        """
        return self._initialized

    @abstractmethod
    async def count_documents(self, collection: str) -> int:
        """
        Count documents in a collection.

        Args:
            collection: Collection name

        Returns:
            Number of documents
        """
        pass

    @abstractmethod
    async def clear_collection(self, collection: str) -> bool:
        """
        Clear all documents from a collection.

        Args:
            collection: Collection name

        Returns:
            True if cleared, False if collection doesn't exist
        """
        pass

    # Advanced Operations (Optional)

    async def recommend(
        self,
        collection: str,
        positive_ids: List[str],
        negative_ids: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recommend similar documents based on positive/negative examples.

        Args:
            collection: Collection name
            positive_ids: List of positive example IDs
            negative_ids: Optional list of negative example IDs
            limit: Maximum number of results

        Returns:
            List of recommended documents
        """
        raise NotImplementedError("Recommend not implemented")

    async def bulk_import(
        self,
        collection: str,
        documents: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """
        Bulk import documents in batches.

        Args:
            collection: Collection name
            documents: List of documents to import
            batch_size: Number of documents per batch

        Returns:
            Number of imported documents
        """
        raise NotImplementedError("Bulk import not implemented")
