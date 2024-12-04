from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class SearchRequest(BaseModel):
    """Request model for search endpoint"""
    text: str
    provider: Optional[str] = None
    max_results: Optional[int] = None

class SearchResponse(BaseModel):
    """Response model for search endpoint"""
    results: List[Dict[str, Any]]

class IndexRequest(BaseModel):
    """Request model for single document indexing"""
    id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None

class IndexResponse(BaseModel):
    """Response model for index endpoint"""
    success: bool

class BulkIndexRequest(BaseModel):
    """Request model for bulk indexing from MongoDB"""
    collection_name: str
    aggregation_pipeline: List[Dict[str, Any]]
    id_field: str = "_id"
    content_field: str = "content"
    metadata_fields: Optional[List[str]] = None
    batch_size: Optional[int] = 1000

class BulkIndexResponse(BaseModel):
    """Response model for bulk index endpoint"""
    indexed_count: int
    error_count: int
    elapsed_time: float
    rate: float
    errors: List[str] 