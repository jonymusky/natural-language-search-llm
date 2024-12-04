from typing import List, Dict, Any
import httpx
import logging
from .base import BaseProvider

logger = logging.getLogger(__name__)

class OllamaProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any]):
        """Initialize Ollama provider with configuration"""
        super().__init__(config)
        self.url = config.get("url", "http://localhost:11434").rstrip("/")
        self.model = config.get("embedding_model", "nomic-embed-text")
        logger.info(f"Initialized Ollama provider with model {self.model} at {self.url}")

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embeddings using Ollama's API"""
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "model": self.model,
                    "input": text
                }
                logger.debug(f"Sending request to Ollama: {payload}")
                
                response = await client.post(
                    f"{self.url}/api/embed",
                    json=payload,
                    timeout=120.0
                )
                response.raise_for_status()
                data = response.json()
                
                logger.debug(f"Received response from Ollama: {data}")
                
                # Validate response
                if "embeddings" not in data:
                    error_msg = f"No embedding found in Ollama response: {data}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                embedding = data["embeddings"]
                logger.debug(f"Raw embedding type: {type(embedding)}, structure: {type(embedding[0]) if embedding else 'empty'}")

                # Handle multi-dimensional arrays (e.g., list of lists)
                if isinstance(embedding[0], list):
                    logger.debug("Flattening nested embedding array")
                    embedding = embedding[0]  # Take first embedding for single text input

                # Validate embedding format
                if not isinstance(embedding, list):
                    error_msg = f"Invalid embedding format. Expected list, got {type(embedding)}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                if not embedding:
                    error_msg = "Empty embedding returned"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                # Log some stats about the embedding values
                embedding_array = embedding
                min_val = min(embedding_array)
                max_val = max(embedding_array)
                avg_val = sum(embedding_array) / len(embedding_array)
                logger.debug(f"Embedding stats - size: {len(embedding_array)}, min: {min_val}, max: {max_val}, avg: {avg_val}")

                if not all(isinstance(x, (int, float)) for x in embedding):
                    error_msg = f"Invalid embedding values. All values must be numbers: {embedding}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                logger.debug(f"Validated embedding of size {len(embedding)}")
                return embedding

        except httpx.HTTPError as e:
            logger.error(f"HTTP error while generating embedding: {str(e)}")
            if e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise