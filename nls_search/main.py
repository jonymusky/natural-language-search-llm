import os
import yaml
import logging
from fastapi import FastAPI, HTTPException
from typing import Optional, Dict, Any

from .services.search import SearchService
from .services.indexing import IndexingService
from .models.document import Document
from .models.api import (
    SearchRequest,
    SearchResponse,
    IndexRequest,
    IndexResponse,
    BulkIndexRequest,
    BulkIndexResponse,
    UpdateRequest
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
def load_config() -> Dict[str, Any]:
    config_path = os.getenv("CONFIG_PATH", "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Interpolate environment variables in config
    def interpolate_env(value):
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.getenv(env_var, value)
        elif isinstance(value, dict):
            return {k: interpolate_env(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [interpolate_env(v) for v in value]
        return value
    
    return interpolate_env(config)

# Initialize application
app = FastAPI(title="NLS Search API")
config = load_config()

# Initialize services with shared vector DB configuration
def init_services():
    """Initialize services with consistent vector DB configuration"""
    # Get vector size from default provider
    default_provider = config["search"]["default_provider"]
    vector_size = config["providers"][default_provider].get("vector_size", 1536)
    
    # Update vector DB config
    vector_db_config = dict(config["vector_db"])
    vector_db_config["vector_size"] = vector_size
    
    # Initialize services with shared config
    search_service = SearchService(config, vector_db_config)
    indexing_service = IndexingService(config, vector_db_config)
    
    return search_service, indexing_service

search_service, indexing_service = init_services()

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search for documents"""
    try:
        results = await search_service.search(
            query=request.text,
            provider=request.provider,
            max_results=request.max_results
        )
        return SearchResponse(results=results)
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/index", response_model=IndexResponse)
async def index(request: IndexRequest):
    """Index a single document"""
    try:
        document = Document(
            id=request.id,
            content=request.content,
            metadata=request.metadata
        )
        success = await indexing_service.index_documents([document])
        return IndexResponse(success=success)
    except Exception as e:
        logger.error(f"Indexing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/bulk-index", response_model=BulkIndexResponse)
async def bulk_index(request: BulkIndexRequest):
    """Bulk index documents from MongoDB"""
    try:
        result = await indexing_service.bulk_index_from_mongodb(
            collection_name=request.collection_name,
            aggregation_pipeline=request.aggregation_pipeline,
            id_field=request.id_field,
            content_field=request.content_field,
            metadata_fields=request.metadata_fields,
            batch_size=request.batch_size
        )
        return BulkIndexResponse(**result)
    except Exception as e:
        logger.error(f"Bulk indexing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/documents/{document_id}", response_model=IndexResponse)
async def delete_document(document_id: str):
    """Delete a document by ID"""
    try:
        success = await indexing_service.delete_document(document_id)
        return IndexResponse(success=success)
    except Exception as e:
        logger.error(f"Document deletion failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/documents/{document_id}", response_model=IndexResponse)
async def update_document(document_id: str, request: UpdateRequest):
    """Update an existing document"""
    try:
        # Create document with path parameter ID and request body content
        document = Document(
            id=document_id,
            content=request.content,
            metadata=request.metadata or {}
        )
        
        # Update document
        success = await indexing_service.update_document(document)
        return IndexResponse(success=success)
    except Exception as e:
        logger.error(f"Document update failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) 