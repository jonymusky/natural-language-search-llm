from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type
import logging

from ..models.document import Document

logger = logging.getLogger(__name__)

class VectorDB(ABC):
    _instance = None
    _initialized = False
    _vector_size = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(VectorDB, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config: Dict[str, Any]):
        # Set vector size first
        VectorDB._vector_size = config.get("vector_size", 1536)
        logger.info(f"VectorDB vector size set to: {self._vector_size}")
        
        # Only initialize once
        if not self._initialized:
            self._do_init(config)
            self._initialized = True
            logger.info("VectorDB initialization completed")
    
    def _do_init(self, config: Dict[str, Any]):
        """Actual initialization logic to be implemented by subclasses"""
        pass
    
    @property
    def vector_size(self) -> int:
        if self._vector_size is None:
            raise ValueError("Vector size not initialized")
        return self._vector_size
    
    @abstractmethod
    async def add_document(self, document: Document) -> bool:
        """Add a document to the vector database"""
        pass

    @abstractmethod
    async def update_document(self, document: Document) -> bool:
        """Update a document in the vector database"""
        pass

    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document from the vector database"""
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        limit: Optional[int] = 10,
        score_threshold: Optional[float] = 0.0
    ) -> List[Document]:
        """Search for similar documents"""
        pass

    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID"""
        pass

_vector_db_registry: Dict[str, Type[VectorDB]] = {}