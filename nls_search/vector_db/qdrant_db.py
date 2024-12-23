from typing import Dict, Any, List
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from qdrant_client.models import Distance, VectorParams, OptimizersConfigDiff
from .base import VectorDB
from ..models.document import Document

class QdrantConnectionError(Exception):
    """Raised when unable to connect to Qdrant"""
    pass

class QdrantDB(VectorDB):
    def __init__(self, config: Dict[str, Any]):
        try:
            self.client = QdrantClient(
                host=config["host"],
                port=config["port"],
                timeout=60,  # Increase timeout for larger operations
                prefer_grpc=False  # Use HTTP API
            )
            self.collection_name = config["collection_name"]
            self.vector_size = config.get("vector_size", 1536)  # Default to OpenAI's size
            
            # Ensure collection exists
            self._ensure_collection()
        except ResponseHandlingException as e:
            if "[Errno 61] Connection refused" in str(e):
                raise QdrantConnectionError(
                    "Could not connect to Qdrant. Make sure Qdrant is running and accessible. "
                    "You can start Qdrant using Docker with: "
                    "docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant"
                ) from e
            raise

    @property
    def vector_size(self) -> int:
        """Get the vector size for this database"""
        return self._vector_size

    @vector_size.setter
    def vector_size(self, size: int):
        """Set the vector size for this database"""
        self._vector_size = size

    def _ensure_collection(self):
        """Ensure the collection exists and has the correct configuration"""
        try:
            # Try to get collection info
            try:
                collection_info = self.client.get_collection(self.collection_name)
                print(f"Found existing collection '{self.collection_name}'")
                
                # Collection exists, verify vector size
                if hasattr(collection_info, 'config') and hasattr(collection_info.config, 'params'):
                    existing_size = collection_info.config.params.vectors.size
                    if existing_size != self.vector_size:
                        # Delete and recreate with correct size
                        print(f"Vector size mismatch ({existing_size} != {self.vector_size}), recreating collection...")
                        self.client.delete_collection(self.collection_name)
                        self._create_collection()
                else:
                    print("Warning: Could not verify vector size, proceeding with existing collection")
            
            except (UnexpectedResponse, ResponseHandlingException):
                # Collection doesn't exist, create it
                print(f"Creating new collection '{self.collection_name}'")
                self._create_collection()
                
        except Exception as e:
            raise QdrantConnectionError(f"Error accessing Qdrant: {str(e)}")

    def _create_collection(self):
        """Create a new collection with the specified configuration"""
        print(f"Creating collection with vector size: {self.vector_size}")
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE
            ),
            optimizers_config=OptimizersConfigDiff(
                default_segment_number=2
            )
        )
        print(f"Created collection '{self.collection_name}' with vector size {self.vector_size}")

    async def add_document(self, document: Document) -> bool:
        """Add a document to Qdrant"""
        try:
            if not document.embedding:
                raise ValueError("Document must have an embedding")
            
            if len(document.embedding) != self.vector_size:
                raise ValueError(
                    f"Vector dimension mismatch: Got {len(document.embedding)}, "
                    f"expected {self.vector_size}"
                )

            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=document.id,
                        vector=document.embedding,
                        payload={
                            "content": document.content,
                            "metadata": document.metadata
                        }
                    )
                ]
            )
            return True

        except Exception as e:
            raise QdrantConnectionError(f"Error adding document to Qdrant: {str(e)}")

    async def update_document(self, document: Document) -> bool:
        """Update a document in Qdrant"""
        return await self.add_document(document)

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document from Qdrant"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[document_id]
                )
            )
            return True
        except Exception as e:
            raise QdrantConnectionError(f"Error deleting document from Qdrant: {str(e)}")

    async def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0
    ) -> List[Document]:
        """Search for similar documents in Qdrant"""
        try:
            if len(query_vector) != self.vector_size:
                raise ValueError(
                    f"Query vector dimension mismatch: Got {len(query_vector)}, "
                    f"expected {self.vector_size}"
                )

            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold
            )
            
            documents = []
            for hit in search_results:
                doc = Document(
                    id=hit.id,
                    content=hit.payload["content"],
                    metadata=hit.payload["metadata"],
                    embedding=None  # Qdrant doesn't return vectors by default
                )
                documents.append(doc)
            
            return documents
        except UnexpectedResponse as e:
            raise QdrantConnectionError(f"Error searching in Qdrant: {str(e)}")
        except Exception as e:
            raise QdrantConnectionError(f"Error searching in Qdrant: {str(e)}") 