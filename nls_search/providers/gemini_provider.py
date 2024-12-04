from typing import List, Dict, Any
import google.generativeai as genai
import logging
from .base import BaseProvider

logger = logging.getLogger(__name__)

class GeminiProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any]):
        """Initialize Gemini provider with configuration"""
        super().__init__(config)
        genai.configure(api_key=config["api_key"])
        self.model = config.get("model", "embedding-001")
        logger.info(f"Initialized Gemini provider with model {self.model}")

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embeddings using Google's Gemini API"""
        try:
            model = genai.GenerativeModel(self.model)
            embedding = model.embed_content(text)
            logger.debug(f"Generated embedding of size {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise