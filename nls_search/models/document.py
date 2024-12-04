from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
import uuid
from bson import ObjectId

class Document(BaseModel):
    """Document model for indexing and searching"""
    id: str
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    score: Optional[float] = None

    @validator('id')
    def validate_id(cls, v):
        """Ensure ID is a valid UUID string or can be converted to one"""
        try:
            # Try to parse as UUID first
            uuid.UUID(str(v))
            return str(v)
        except ValueError:
            # Check if it's a MongoDB ObjectId
            if len(str(v)) == 24 and ObjectId.is_valid(str(v)):
                # Create a deterministic UUID from the ObjectId
                return str(uuid.uuid5(uuid.NAMESPACE_OID, str(v)))
            # For any other string, use DNS namespace
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(v)))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary format"""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "score": self.score
        }

    class Config:
        arbitrary_types_allowed = True
        extra = 'allow'
        json_encoders = {
            ObjectId: str
        }

class SearchQuery(BaseModel):
    """Search query model"""
    text: str
    provider: Optional[str] = None
    max_results: Optional[int] = 10
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)    

class BulkIndexConfig(BaseModel):
    """Configuration for bulk indexing from MongoDB"""
    collection_name: str
    aggregation_pipeline: List[Dict[str, Any]]
    id_field: str = "_id"
    content_field: str
    metadata_fields: Optional[List[str]] = Field(default_factory=list)
    batch_size: Optional[int] = 1000