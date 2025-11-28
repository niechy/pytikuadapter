# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

pytikuadapter is a Python-based question bank adapter service that queries multiple question bank providers concurrently and aggregates their answers. It's a FastAPI-based REST API that supports various question types (single choice, multiple choice, fill-in-blank, true/false, Q&A) and uses a plugin architecture for extensibility.

## Development Commands

### Environment Setup
```bash
# Install dependencies using Poetry
poetry install

# Activate virtual environment
poetry shell
```

### Running the Application
```bash
# Development mode (from main.py)
python main.py

# Production mode with uvicorn
uvicorn main:app --host 127.0.0.1 --port 8060 --log-level info

# Multi-worker production
uvicorn demo:app --host 0.0.0.0 --port 8060 --workers 4 --log-level info
```

### Testing Individual Providers
```bash
# Run demo.py to test provider implementations
python demo.py
```

## Architecture

### Core Components

1. **FastAPI Application (main.py)**
   - Entry point with lifespan management for aiohttp session
   - Single endpoint: `POST /v1/adapter-service/search`
   - Bearer token authentication via `Authorization` header
   - Concurrent provider queries with semaphore-based rate limiting (MAX_CONCURRENT=20)
   - Exception handling for ClientResponseError and ValidationError

2. **Provider Plugin System (providers/manager.py)**
   - `Providersbase`: Abstract base class for all provider adapters
   - `ProviderRegistry`: Auto-registration system using `__init_subclass__`
   - `ProvidersManager`: High-level interface to access registered providers
   - Shared `ClientSession` across all providers (initialized in lifespan)

3. **Data Models (model.py)**
   - `QuestionContent`: Question with content, options, and type (0-4)
   - `Provider`: Provider name, priority, and config dict
   - `QuestionRequest`: Query + list of providers to use
   - `A`: Individual provider answer (choice/judgement/text based on type)
   - `UnifiedAnswer`: Aggregated answer with multiple representations
   - `Res`: Final response structure

4. **Answer Aggregation (core.py)**
   - `collect_true_answer()`: Uses Counter to find most common answer across providers
   - `construct_res()`: Builds unified response with answer keys, indices, and text
   - Handles all 5 question types with appropriate formatting

### Provider Implementation Pattern

To add a new provider, create a file in `providers/` following this structure:

```python
from .manager import Providersbase
from model import QuestionContent, Provider, A
from pydantic import BaseModel, Field

class YourProvider(Providersbase):
    name = "Your Provider Name"  # Must be unique

    class Configs(BaseModel):
        # Define required/optional config parameters
        api_key: str = Field(..., description="API key")

    async def _search(self, query: QuestionContent, provider: Provider):
        config = self.Configs(**provider.config)
        # Make HTTP request using self.session
        # Return A(provider=self.name, choice/text/judgement=..., type=...)
```

The provider will be auto-registered via `providers/__init__.py` which dynamically imports all modules.

### Question Types

- `0`: Single choice (returns `choice` list with one element)
- `1`: Multiple choice (returns `choice` list with multiple elements)
- `2`: Fill-in-blank (returns `text` list)
- `3`: True/False (returns `judgement` boolean)
- `4`: Q&A (returns `text` list)

### Request Flow

1. Request arrives at `/v1/adapter-service/search` with query and provider list
2. For each provider, create async task with semaphore protection
3. `ProvidersManager.get_adapter_achieve()` retrieves provider instance
4. Call `adapter.search()` which wraps `_search()` with error handling
5. `asyncio.gather()` collects all results (including exceptions)
6. Filter successful responses, aggregate with `collect_true_answer()`
7. Return `Res` with unified answer and individual provider answers

### Concurrency Control

- Semaphore limits concurrent provider requests to 20 (MAX_CONCURRENT)
- All tasks created immediately with `asyncio.create_task()`
- Actual execution controlled by semaphore in `_call_adapter()`
- Shared aiohttp ClientSession for connection pooling

## Important Implementation Notes

- Provider `_search()` methods should raise exceptions on errors (caught by `search()` wrapper)
- The `type` field in responses may differ from query type (e.g., Like provider detects single vs multiple choice)
- Answer aggregation uses tuple sorting for choice normalization: `['A','B']` == `['B','A']`
- All providers share a single ClientSession initialized in FastAPI lifespan
- The `providers/__init__.py` auto-imports all provider modules for registration

## API Request Example

```json
{
  "query": {
    "content": "Question text here",
    "options": ["Option A", "Option B", "Option C"],
    "type": 0
  },
  "providers": [
    {
      "name": "Like知识库",
      "config": {
        "key": "your-api-key",
        "llm_model": "deepseek-v3.2"
      }
    }
  ]
}
```

## Current Providers

- **Like知识库** (providers/like.py): Paid service using LLM-based question answering
- **万能题库** (providers/wanneng.py): Free/paid service with direct question lookup

Additional providers mentioned in readme.md are not yet implemented.