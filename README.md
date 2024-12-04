# NLS Search

A powerful Natural Language Search API that provides semantic search capabilities using vector embeddings. The system supports multiple LLM providers and can be easily integrated with various data sources.

## Features

- Natural Language Search using semantic embeddings
- Multiple LLM provider support:
  - Ollama (local models)
  - OpenAI
  - Google Gemini
- Vector-based similarity search using Qdrant
- Configurable model settings per provider
- RESTful API for indexing and searching
- Bulk indexing support from MongoDB
- Automatic vector size handling
- Configurable similarity thresholds

## Requirements

- Python 3.9+
- Docker
- Make

## Quick Start

1. Setup the environment:
```bash
make setup
```

2. Configure your environment variables in `.env`:
```bash
# API Settings
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true

# Vector DB Settings
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=documents

# MongoDB Settings (optional)
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=your_database
MONGODB_COLLECTION=your_collection

# Provider Settings
DEFAULT_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_EMBEDDING_MODEL=all-minilm

# Optional Providers
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-pro
```

3. Start the services:
```bash
# Start Qdrant (required)
make start-qdrant

# Start MongoDB (optional - for bulk indexing)
make start-mongodb

# Start the API
make start-api
```

## Natural Language Search

The system uses semantic embeddings to understand the meaning of your queries and find relevant documents. Unlike traditional keyword search:

- Understands semantic meaning, not just exact matches
- Handles synonyms and related concepts
- Works with natural language questions
- Returns results ranked by semantic similarity

Example search query:
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What are the safety procedures for handling hazardous materials?",
    "max_results": 5
  }'
```

## Configuration

The system is configured through `config.yaml`:

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
  similarity_threshold: 0.3  # Adjust for stricter/looser matching
```

## API Documentation

### Endpoints

- `POST /search`: Search documents using natural language
- `POST /index`: Index a single document
- `POST /bulk-index`: Bulk index documents from MongoDB

For detailed examples and usage scenarios, check out our [Examples Guide](EXAMPLES.md).

## Troubleshooting

### Common Issues

1. **Vector Size Mismatch**
   - Error: "Vector size mismatch"
   - Solution: Ensure provider's vector_size matches Qdrant's configuration

2. **No Results Found**
   - Check similarity_threshold in config.yaml
   - Verify documents are properly indexed
   - Check provider's embedding model is working

3. **Qdrant Connection Issues**
   - Error: "Connection refused"
   - Solution: Check status with `make status`
   - Start Qdrant with `make start-qdrant`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 