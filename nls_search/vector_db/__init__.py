from typing import Dict, Any
import logging

from .base import VectorDB
from .qdrant import QdrantDB

logger = logging.getLogger(__name__)

def get_vector_db(config: Dict[str, Any]) -> VectorDB:
    """Get vector database instance based on configuration"""
    db_type = config.get("type", "qdrant").lower()
    
    if db_type == "qdrant":
        logger.info("Initializing Qdrant vector database")
        return QdrantDB(config)
    else:
        raise ValueError(f"Unsupported vector database type: {db_type}") 