from typing import List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
import time

from ..models.document import Document
from ..providers import get_provider
from ..vector_db import get_vector_db

logger = logging.getLogger(__name__)

class IndexingService:
    def __init__(self, config: Dict[str, Any], vector_db_config: Dict[str, Any]):
        self.config = config
        self.default_provider = config["search"]["default_provider"]
        
        # Initialize vector DB
        self.vector_db = get_vector_db(vector_db_config)
        logger.info(f"Vector DB initialized with size {self.vector_db.vector_size}")
        
        # Initialize MongoDB connection with retry
        self.mongo_client = None
        self.mongo_db = None
        self._init_mongodb()

    def _init_mongodb(self):
        """Initialize MongoDB connection with configuration"""
        try:
            self.mongo_client = AsyncIOMotorClient(
                self.config["mongodb"]["uri"],
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
                maxPoolSize=50,
                retryWrites=True
            )
            self.mongo_db = self.mongo_client[self.config["mongodb"]["database"]]
            logger.info(f"MongoDB connection initialized to {self.config['mongodb']['database']}")
        except Exception as e:
            logger.error(f"Error initializing MongoDB connection: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def _ensure_mongodb_connection(self):
        """Ensure MongoDB connection is alive"""
        try:
            await self.mongo_client.admin.command('ping')
            logger.debug("MongoDB connection verified")
        except (ConnectionFailure, ServerSelectionTimeoutError):
            logger.warning("Lost MongoDB connection, attempting to reconnect...")
            self._init_mongodb()
            await self.mongo_client.admin.command('ping')
            logger.info("MongoDB reconnection successful")

    async def index_documents(self, documents: List[Document]) -> bool:
        """Index a list of documents"""
        provider = get_provider(self.default_provider, self.config["providers"])
        logger.info(f"Indexing {len(documents)} documents using provider '{self.default_provider}'")

        for doc in documents:
            try:
                if not doc.embedding:
                    doc.embedding = await provider.generate_embedding(doc.content)
                await self.vector_db.add_document(doc)
                logger.debug(f"Successfully indexed document {doc.id}")
            except Exception as e:
                logger.error(f"Error indexing document {doc.id}: {str(e)}")
                raise

        return True

    async def bulk_index_from_mongodb(
        self,
        collection_name: str,
        aggregation_pipeline: List[Dict[str, Any]],
        id_field: str = "_id",
        content_field: str = "content",
        metadata_fields: List[str] = None,
        batch_size: int = 1000
    ) -> Dict[str, Any]:
        """Bulk index documents from MongoDB aggregation"""
        start_time = time.time()
        logger.info(f"Starting bulk indexing from collection '{collection_name}'")
        logger.info(f"Configuration: id_field='{id_field}', content_field='{content_field}', metadata_fields={metadata_fields}")
        logger.info(f"Aggregation pipeline: {aggregation_pipeline}")
        
        await self._ensure_mongodb_connection()
        
        provider = get_provider(self.default_provider, self.config["providers"])
        collection = self.mongo_db[collection_name]
        
        # Initialize counters
        indexed_count = 0
        error_count = 0
        errors = []
        batch = []
        total_docs = await collection.count_documents({})
        
        logger.info(f"Found {total_docs} documents to process")
        
        try:
            # Process documents in batches
            cursor = collection.aggregate(aggregation_pipeline)
            
            async for doc in cursor:
                try:
                    # Log raw document for debugging
                    logger.debug(f"Processing document: {doc}")
                    
                    # Extract document fields
                    raw_id = doc.get(id_field)
                    doc_id = str(raw_id) if raw_id is not None else ""
                    content = doc.get(content_field)
                    
                    if not content:
                        error_msg = f"Missing content field '{content_field}' for document: {doc}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        error_count += 1
                        continue
                    
                    # Extract metadata if specified
                    metadata = {}
                    if metadata_fields:
                        metadata = {
                            field: doc.get(field)
                            for field in metadata_fields
                            if field in doc
                        }
                        logger.debug(f"Extracted metadata: {metadata}")
                    
                    # Create document object with UUID-based ID
                    try:
                        document = Document(
                            id=doc_id,  # Document model will convert MongoDB ObjectId to UUID
                            content=content,
                            metadata=metadata
                        )
                        logger.debug(f"Created document with ID: {document.id} (original: {doc_id})")
                    except Exception as e:
                        error_msg = f"Error creating document with ID {doc_id}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        error_count += 1
                        continue
                    
                    try:
                        # Generate embedding with retry
                        for attempt in range(3):
                            try:
                                embedding = await provider.generate_embedding(content)
                                logger.debug(f"Generated embedding of size {len(embedding)} for document {doc_id}")
                                document.embedding = embedding
                                break
                            except Exception as e:
                                if attempt == 2:  # Last attempt
                                    raise
                                logger.warning(f"Embedding generation failed for document {doc_id}, attempt {attempt + 1}/3: {str(e)}")
                                await asyncio.sleep(1 * (attempt + 1))
                        
                        batch.append(document)
                        
                        # Process batch if it reaches the size limit
                        if len(batch) >= batch_size:
                            logger.info(f"Processing batch of {len(batch)} documents")
                            await self._process_batch(batch)
                            indexed_count += len(batch)
                            elapsed_time = time.time() - start_time
                            rate = indexed_count / elapsed_time
                            progress = (indexed_count / total_docs) * 100 if total_docs > 0 else 0
                            
                            logger.info(
                                f"Progress: {indexed_count}/{total_docs} ({progress:.1f}%) - "
                                f"Rate: {rate:.1f} docs/sec - "
                                f"Errors: {error_count}"
                            )
                            batch = []
                            
                    except Exception as e:
                        error_msg = f"Error processing document {doc_id}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        error_count += 1
                        continue
                    
                except Exception as e:
                    error_msg = f"Error processing document: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    error_count += 1
                    continue
            
            # Process remaining documents
            if batch:
                logger.info(f"Processing final batch of {len(batch)} documents")
                await self._process_batch(batch)
                indexed_count += len(batch)
            
            elapsed_time = time.time() - start_time
            final_rate = indexed_count / elapsed_time if elapsed_time > 0 else 0
            
            logger.info(
                f"Bulk indexing completed in {elapsed_time:.1f} seconds:\n"
                f"- Total processed: {indexed_count}\n"
                f"- Average rate: {final_rate:.1f} docs/sec\n"
                f"- Errors: {error_count}"
            )
            
            if errors:
                logger.warning(f"First few errors encountered: {errors[:5]}")
            
        except Exception as e:
            error_msg = f"Error in bulk indexing: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        return {
            "indexed_count": indexed_count,
            "error_count": error_count,
            "elapsed_time": elapsed_time,
            "rate": final_rate,
            "errors": errors
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def _process_batch(self, batch: List[Document]):
        """Helper method to process a batch of documents with retry"""
        logger.debug(f"Processing batch of {len(batch)} documents")
        for doc in batch:
            await self.vector_db.add_document(doc)

    async def update_document(self, document_id: str, document: Document) -> bool:
        """Update an existing document"""
        logger.info(f"Updating document {document_id}")
        provider = get_provider(self.default_provider, self.config["providers"])

        if not document.embedding:
            document.embedding = await provider.generate_embedding(document.content)

        await self.vector_db.update_document(document)
        logger.debug(f"Successfully updated document {document_id}")
        return True

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document from the database"""
        logger.info(f"Deleting document {document_id}")
        await self.vector_db.delete_document(document_id)
        logger.debug(f"Successfully deleted document {document_id}")
        return True 