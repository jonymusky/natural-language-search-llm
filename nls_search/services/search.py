from typing import List, Optional, Dict, Any
import logging

from ..models.document import Document
from ..providers import get_provider
from ..vector_db import get_vector_db

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, config: Dict[str, Any], vector_db_config: Dict[str, Any]):
        self.config = config
        self.default_provider = config["search"]["default_provider"]
        self.max_results = config["search"]["max_results"]
        self.similarity_threshold = config["search"]["similarity_threshold"]
        
        logger.info(f"Initializing SearchService with default provider: {self.default_provider}")
        self.vector_db = get_vector_db(vector_db_config)
        logger.info(f"Vector DB initialized with size {self.vector_db.vector_size}")

    async def search(
        self,
        query: str,
        provider: Optional[str] = None,
        max_results: Optional[int] = None
    ) -> List[Dict]:
        """
        Search for documents using natural language queries
        """
        # Preprocess the query
        query = query.strip()
        if not query:
            raise ValueError("Search query cannot be empty")

        # Use default provider if none specified
        provider_name = provider or self.default_provider
        logger.info(f"Processing natural language search: '{query}' with provider: {provider_name}")
        
        # Validate provider
        if provider_name not in self.config["providers"]:
            logger.error(f"Unknown provider requested: {provider_name}")
            raise ValueError(f"Unknown provider: {provider_name}")
        if not self.config["providers"][provider_name].get("enabled", False):
            logger.error(f"Requested provider '{provider_name}' is not enabled")
            raise ValueError(f"Provider '{provider_name}' is not enabled")
        
        # Get the provider and generate embedding
        llm_provider = get_provider(provider_name, self.config["providers"])
        logger.debug(f"Generating semantic embedding for query: '{query}'")
        query_embedding = await llm_provider.generate_embedding(query)
        
        # Log embedding details
        logger.debug(f"Generated embedding size: {len(query_embedding)}")
        
        # Verify vector size
        if len(query_embedding) != self.vector_db.vector_size:
            error_msg = (
                f"Vector size mismatch: Provider '{provider_name}' generated "
                f"embedding of size {len(query_embedding)}, but vector DB expects {self.vector_db.vector_size}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Search in vector database
        logger.debug(f"Performing semantic search with limit={max_results or self.max_results} and threshold={self.similarity_threshold}")
        try:
            results = await self.vector_db.search(
                query_embedding,
                limit=max_results or self.max_results,
                score_threshold=self.similarity_threshold
            )
            logger.info(f"Search completed successfully. Found {len(results)} semantically relevant results")
            # Convert Document objects to dictionaries and sort by relevance
            return sorted([doc.to_dict() for doc in results], key=lambda x: x.get('score', 0), reverse=True)
        except Exception as e:
            logger.error(f"Error searching in vector DB: {str(e)}")
            raise