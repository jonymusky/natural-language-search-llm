from typing import List, Dict, Any, Optional
from bson import Decimal128
import httpx
import logging
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import Distance, VectorParams, UpdateCollection
from qdrant_client.models import PointStruct, CollectionStatus

from ..models.document import Document
from .base import VectorDB

logger = logging.getLogger(__name__)

class QdrantDB(VectorDB):
    def _do_init(self, config: Dict[str, Any]):
        """Initialize Qdrant client and collection"""
        self.collection_name = config.get("collection_name", "documents")
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 6333)
        
        # Initialize client with timeout and compatibility settings
        self.client = QdrantClient(
            host=self.host, 
            port=self.port,
            timeout=60,
            prefer_grpc=False,
            https=False
        )
        logger.info(f"Initializing Qdrant connection to {self.host}:{self.port}")
        
        # Check if collection exists and create if needed
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Collection '{self.collection_name}' not found, creating...")
                self._create_collection()
            else:
                # Get collection info using raw HTTP request
                try:
                    response = httpx.get(
                        f"http://{self.host}:{self.port}/collections/{self.collection_name}",
                        timeout=5.0
                    )
                    response.raise_for_status()
                    collection_info = response.json()
                    existing_vector_size = collection_info["result"]["config"]["params"]["vectors"]["size"]
                    
                    if existing_vector_size != self._vector_size:
                        logger.warning(
                            f"Collection '{self.collection_name}' exists with different vector size "
                            f"({existing_vector_size} != {self._vector_size}). Recreating..."
                        )
                        self._create_collection()
                    else:
                        logger.info(f"Using existing collection '{self.collection_name}' with vector size {self._vector_size}")
                except Exception as e:
                    logger.error(f"Error getting collection info: {str(e)}")
                    logger.info("Recreating collection...")
                    self._create_collection()
                    
        except Exception as e:
            logger.error(f"Error checking collection: {str(e)}")
            logger.info("Attempting to create collection...")
            self._create_collection()
    
    def _create_collection(self):
        """Create Qdrant collection with proper configuration"""
        logger.info(f"Creating collection '{self.collection_name}' with vector size {self._vector_size}")
        
        # Delete if exists
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted existing collection '{self.collection_name}'")
        except Exception as e:
            logger.debug(f"Error deleting collection (may not exist): {str(e)}")
        
        # Create new collection with basic configuration
        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self._vector_size,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created collection '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Error creating collection: {str(e)}")
            raise
        
        # Wait for collection to be ready using raw HTTP request
        import time
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                response = httpx.get(
                    f"http://{self.host}:{self.port}/collections/{self.collection_name}",
                    timeout=5.0
                )
                response.raise_for_status()
                collection_info = response.json()
                
                if collection_info.get("result", {}).get("status") == "green":
                    logger.info(f"Collection '{self.collection_name}' is ready")
                    return
                
                logger.info(f"Collection status: {collection_info.get('result', {}).get('status')}, waiting...")
            except Exception as e:
                logger.warning(f"Error checking collection status (attempt {attempt + 1}/{max_attempts}): {str(e)}")
            time.sleep(1)
        
        raise RuntimeError(f"Collection '{self.collection_name}' not ready after {max_attempts} attempts")

    async def add_document(self, document: Document) -> bool:
        """Add a document to Qdrant"""
        try:
            # Validate embedding
            if not document.embedding:
                raise ValueError("Document has no embedding")
            if len(document.embedding) != self._vector_size:
                raise ValueError(f"Document embedding size {len(document.embedding)} does not match collection vector size {self._vector_size}")
            if not all(isinstance(x, (int, float)) for x in document.embedding):
                raise ValueError("Document embedding contains non-numeric values")
            
            logger.debug(f"Adding document {document.id} with embedding size {len(document.embedding)}")
            
            # Convert metadata values to JSON-serializable format
            metadata = document.metadata
            if isinstance(metadata, dict):
                def convert_value(v):
                    from bson import ObjectId
                    if isinstance(v, ObjectId):
                        return str(v)
                    elif isinstance(v, Decimal128):
                        return float(v.to_decimal())  # Convert Decimal128 to float                    
                    elif isinstance(v, list):
                        return [convert_value(x) for x in v]
                    elif isinstance(v, dict):
                        return {k: convert_value(v) for k, v in v.items()}
                    return v
                
                metadata = {k: convert_value(v) for k, v in metadata.items()}
            
            # Create point with proper structure
            point = PointStruct(
                id=str(document.id),  # Ensure ID is string
                vector=document.embedding,
                payload={
                    "content": document.content,
                    "metadata": metadata
                }
            )
            
            # Add point to collection
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
                wait=True  # Ensure point is added before returning
            )
            return True
        except Exception as e:
            logger.error(f"Error adding document to Qdrant: {str(e)}")
            raise

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
            logger.error(f"Error deleting document from Qdrant: {str(e)}")
            raise

    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID from Qdrant"""
        try:
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[document_id]
            )
            
            if not points:
                return None
                
            point = points[0]
            return Document(
                id=str(point.id),
                content=point.payload["content"],
                metadata=point.payload.get("metadata", {}),
            )
            
        except Exception as e:
            logger.error(f"Error retrieving document from Qdrant: {str(e)}")
            raise

    async def search(
        self,
        query_vector: List[float],
        limit: Optional[int] = 10,
        score_threshold: Optional[float] = 0.0
    ) -> List[Document]:
        """Search for similar documents in Qdrant"""
        try:
            logger.debug(f"Searching Qdrant with vector of size {len(query_vector)}")
            logger.debug(f"Search parameters: limit={limit}, score_threshold={score_threshold}")
            
            # Get collection info for debugging
            try:
                collection_info = self.client.get_collection(self.collection_name)
                count = collection_info.points_count
                logger.info(f"Collection '{self.collection_name}' has {count} documents")
            except Exception as e:
                logger.warning(f"Could not get collection info: {str(e)}")
            
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold
            )
            
            logger.debug(f"Raw search results: {results}")
            
            documents = []
            for result in results:
                doc = Document(
                    id=str(result.id),
                    content=result.payload["content"],
                    metadata=result.payload.get("metadata", {}),
                    score=float(result.score) if result.score is not None else None
                )
                documents.append(doc)
                logger.debug(f"Found document: id={doc.id}, score={doc.score}")
            
            # Sort by score in descending order
            documents.sort(key=lambda x: x.score if x.score is not None else 0.0, reverse=True)
            return documents
            
        except Exception as e:
            logger.error(f"Error searching in Qdrant: {str(e)}")
            raise 