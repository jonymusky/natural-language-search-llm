# NLS Search API Examples

## Natural Language Search

Search for documents using natural language queries:

```bash
# Basic natural language search
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What are the safety procedures for chemical handling?",
    "max_results": 5
  }'

# Search with specific provider
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show me documentation about error handling",
    "provider": "ollama",
    "max_results": 3
  }'
```

Response:
```json
{
  "results": [
    {
      "id": "doc1",
      "content": "Chemical safety procedures require proper PPE including...",
      "metadata": {
        "category": "safety",
        "department": "laboratory"
      },
      "score": 0.89
    }
  ]
}
```

## Document Indexing

### Index Single Document

```bash
curl -X POST "http://localhost:8000/index" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "unique_doc_id",
    "content": "This is the document content that will be searchable using natural language queries.",
    "metadata": {
      "category": "documentation",
      "author": "John Doe",
      "date": "2024-03-03"
    }
  }'
```

Response:
```json
{
  "success": true
}
```

### Bulk Index from MongoDB

Index multiple documents from a MongoDB collection:

```bash
curl -X POST "http://localhost:8000/bulk-index" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "documents",
    "aggregation_pipeline": [
      {"$match": {"status": "active"}},
      {"$limit": 1000}
    ],
    "id_field": "_id",
    "content_field": "text",
    "metadata_fields": ["category", "author", "tags"],
    "batch_size": 100
  }'
```

Response:
```json
{
  "indexed_count": 150,
  "error_count": 0,
  "elapsed_time": 25.5,
  "rate": 5.88,
  "errors": []
}
```

### Delete Document

Delete a document by its ID:

```bash
curl -X DELETE "http://localhost:8000/documents/{document_id}" \
  -H "Content-Type: application/json"
```

Response:
```json
{
  "success": true
}
```

### Update Document

Update an existing document:

```bash
curl -X PUT "http://localhost:8000/documents/{document_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Updated document content that will be re-embedded and searchable.",
    "metadata": {
      "category": "documentation",
      "author": "Jane Doe",
      "last_updated": "2024-03-04"
    }
  }'
```

Response:
```json
{
  "success": true
}
```

Note: When updating a document, the system will:
1. Generate new embeddings for the updated content
2. Replace the old document's embeddings and metadata
3. Maintain the same document ID

## Natural Language Query Examples

Here are some example queries that demonstrate the semantic search capabilities:

```bash
# Conceptual search
curl -X POST "http://localhost:8000/search" \
  -d '{
    "text": "What are best practices for data security?",
    "max_results": 5
  }'

# Question-based search
curl -X POST "http://localhost:8000/search" \
  -d '{
    "text": "How do I handle customer complaints?",
    "max_results": 3
  }'

# Topic exploration
curl -X POST "http://localhost:8000/search" \
  -d '{
    "text": "Tell me about project management methodologies",
    "max_results": 5
  }'
```

The system will understand these queries semantically and return relevant documents, even if they don't contain the exact words but cover the same concepts.

## Configuration Examples

### config.yaml
```yaml
vector_db:
  type: qdrant
  vector_size: 384  # Matches Ollama's all-minilm model

providers:
  ollama:
    enabled: true
    url: ${OLLAMA_URL}
    model: ${OLLAMA_MODEL}
    embedding_model: ${OLLAMA_EMBEDDING_MODEL}
    vector_size: 384

search:
  default_provider: ${DEFAULT_PROVIDER}
  max_results: 10
  similarity_threshold: 0.3  # Lower values = more results but potentially less relevant
```

### Environment Variables (.env)
```bash
# API Settings
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true

# Vector DB
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=documents

# Provider Settings
DEFAULT_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_EMBEDDING_MODEL=all-minilm
```

## Error Handling

The API returns clear error messages:

```json
{
  "detail": "Vector size mismatch: Provider 'ollama' generated embedding of size 384, but vector DB expects 768"
}
```

```json
{
  "detail": "Search query cannot be empty"
}
```

## Best Practices

1. **Natural Language Queries**
   - Use complete sentences or questions
   - Be specific but natural in your queries
   - Include relevant context

2. **Document Indexing**
   - Provide meaningful content for embedding
   - Include relevant metadata
   - Use batch processing for large datasets

3. **Configuration**
   - Match vector sizes between provider and database
   - Adjust similarity threshold based on needs
   - Monitor and tune based on results