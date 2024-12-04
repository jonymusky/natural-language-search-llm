# Add this function at the top of the Makefile
# Function to redact password from MongoDB URI
define redact_mongodb_uri
$(shell echo "$(1)" | sed -E 's/(:.*@)/:***@/')
endef

.PHONY: help setup install start-qdrant stop-qdrant start-mongodb stop-mongodb start-api stop clean

# Variables
PYTHON := python3
VENV := venv
PIP := $(VENV)/bin/pip
PYTHON_VENV := $(VENV)/bin/python
QDRANT_CONTAINER := qdrant
MONGODB_CONTAINER := mongodb

# Load environment variables if .env exists
ifneq (,$(wildcard .env))
    include .env
    export
endif

# Default values if not set in .env
API_PORT ?= 8000
QDRANT_HOST ?= localhost
QDRANT_PORT ?= 6333
MONGODB_HOST ?= localhost
MONGODB_PORT ?= 27017

# Derived variables
MONGODB_URI ?= mongodb://$(MONGODB_HOST):$(MONGODB_PORT)
MONGODB_URI_REDACTED = $(call redact_mongodb_uri,$(MONGODB_URI))

help:
	@echo "Available commands:"
	@echo "  make setup         - Create virtual environment and install dependencies"
	@echo "  make install      - Install Python dependencies"
	@echo "  make start-qdrant - Start Qdrant container"
	@echo "  make stop-qdrant  - Stop Qdrant container"
	@echo "  make start-mongodb- Start MongoDB container (optional - for bulk indexing)"
	@echo "  make stop-mongodb - Stop MongoDB container"
	@echo "  make start-api    - Start the NLS Search API"
	@echo "  make stop         - Stop all containers"
	@echo "  make clean        - Remove virtual environment and containers"
	@echo "  make status       - Check status of services"

setup: $(VENV)/bin/activate

$(VENV)/bin/activate:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	make install

install:
	$(PIP) install -r requirements.txt

start-qdrant:
	@echo "Starting Qdrant container..."
	@if [ ! "$$(docker ps -q -f name=$(QDRANT_CONTAINER))" ]; then \
		if [ "$$(docker ps -aq -f status=exited -f name=$(QDRANT_CONTAINER))" ]; then \
			docker rm $(QDRANT_CONTAINER); \
		fi; \
		docker run -d --name $(QDRANT_CONTAINER) \
			-p $(QDRANT_PORT):6333 \
			-p 6334:6334 \
			-v $$(pwd)/qdrant_storage:/qdrant/storage \
			qdrant/qdrant; \
		echo "Waiting for Qdrant to start..."; \
		sleep 5; \
	else \
		echo "Qdrant is already running."; \
	fi
	@echo "Checking Qdrant health..."
	@curl -s http://$(QDRANT_HOST):$(QDRANT_PORT)/healthz || echo "Failed to connect to Qdrant"

stop-qdrant:
	@echo "Stopping Qdrant container..."
	@docker stop $(QDRANT_CONTAINER) || true
	@docker rm $(QDRANT_CONTAINER) || true

start-mongodb:
	@echo "Starting MongoDB container..."
	@if [ ! "$$(docker ps -q -f name=$(MONGODB_CONTAINER))" ]; then \
		if [ "$$(docker ps -aq -f status=exited -f name=$(MONGODB_CONTAINER))" ]; then \
			docker rm $(MONGODB_CONTAINER); \
		fi; \
		docker run -d --name $(MONGODB_CONTAINER) \
			-p $(MONGODB_PORT):27017 \
			-v $$(pwd)/mongodb_data:/data/db \
			mongo; \
		echo "Waiting for MongoDB to start..."; \
		sleep 5; \
	else \
		echo "MongoDB is already running."; \
	fi

stop-mongodb:
	@echo "Stopping MongoDB container..."
	@docker stop $(MONGODB_CONTAINER) || true
	@docker rm $(MONGODB_CONTAINER) || true

start-api: start-qdrant
	@echo "Starting NLS Search API..."
	@if [ ! -f .env ]; then \
		echo "Warning: .env file not found. Copying from .env.example..."; \
		cp .env.example .env; \
	fi
	cd $$(pwd) && $(PYTHON_VENV) -m uvicorn nls_search.main:app --host $(APP_HOST) --port $(APP_PORT) --reload

stop:
	make stop-qdrant
	make stop-mongodb

clean: stop
	@echo "Cleaning up..."
	rm -rf $(VENV)
	rm -rf qdrant_storage
	rm -rf mongodb_data
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf *.egg-info

check_mongodb_connection:
	@if command -v mongosh >/dev/null 2>&1; then \
		if mongosh --quiet --eval "db.runCommand('ping').ok" "$(MONGODB_URI)" >/dev/null 2>&1; then \
			echo "✅ MongoDB is responding at $(MONGODB_URI_REDACTED)"; \
		else \
			echo "❌ MongoDB is not responding at $(MONGODB_URI_REDACTED)"; \
		fi \
	else \
		if nc -z $(MONGODB_HOST) $(MONGODB_PORT) 2>/dev/null; then \
			echo "✅ MongoDB port $(MONGODB_PORT) is open (mongosh not installed)"; \
		else \
			echo "❌ MongoDB port $(MONGODB_PORT) is not accessible"; \
		fi \
	fi

status:
	@echo "Checking services status..."
	@if [ ! -f .env ]; then \
		echo "⚠️  Warning: .env file not found. Using default values."; \
	fi
	@echo "\nConfiguration:"
	@echo "  Qdrant: $(QDRANT_HOST):$(QDRANT_PORT)"
	@echo "  MongoDB: $(MONGODB_URI_REDACTED)"
	@echo "\nQdrant Status:"
	@if [ "$$(docker ps -q -f name=$(QDRANT_CONTAINER))" ]; then \
		echo "✅ Qdrant container is running"; \
		if curl -s http://$(QDRANT_HOST):$(QDRANT_PORT)/healthz > /dev/null; then \
			echo "✅ Qdrant is responding at $(QDRANT_HOST):$(QDRANT_PORT)"; \
		else \
			echo "❌ Qdrant is not responding at $(QDRANT_HOST):$(QDRANT_PORT)"; \
		fi \
	else \
		echo "❌ Qdrant container is not running"; \
	fi
	@echo "\nMongoDB Status:"
	@echo "Checking MongoDB containers..."
	@MONGO_CONTAINER=$$(docker ps --format '{{.Names}}' | grep -E 'mongo|mongodb' || echo ""); \
	if [ ! -z "$$MONGO_CONTAINER" ]; then \
		echo "✅ Found MongoDB container: $$MONGO_CONTAINER"; \
		$(MAKE) check_mongodb_connection; \
	else \
		echo "❌ No MongoDB container found matching 'mongo' or 'mongodb'"; \
		echo "Running containers:"; \
		docker ps --format "  - {{.Names}}"; \
	fi 