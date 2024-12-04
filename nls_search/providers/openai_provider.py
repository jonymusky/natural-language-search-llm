from typing import List, Dict, Any
import openai
import logging
from .base import BaseProvider

logger = logging.getLogger(__name__)

class OpenAIProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenAI provider with configuration"""
        super().__init__(config)
        openai.api_key = config["api_key"]
        self.model = config.get("model", "text-embedding-3-small")
        logger.info(f"Initialized OpenAI provider with model {self.model}")

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI's API"""
        try:
            response = await openai.embeddings.create(
                model=self.model,
                input=text
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding of size {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise 