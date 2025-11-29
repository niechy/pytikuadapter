# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

pytikuadapter is a Python-based question bank adapter service that queries multiple question bank providers concurrently and aggregates their answers. It's a FastAPI-based REST API that supports various question types (single choice, multiple choice, fill-in-blank, true/false, Q&A) and uses a plugin architecture for extensibility.

## Development Commands

```bash
# Install dependencies
poetry install

# Run development server
python main.py

# Production with uvicorn
uvicorn main:app --host 127.0.0.1 --port 8060 --log-level info
```

## Architecture

### Core Components

1. **FastAPI Application (main.py)**
   - Entry point with lifespan management for aiohttp session and database
   - Single endpoint: `POST /v1/adapter-service/search`
   - Bearer token authentication via `Authorization` header
   - Concurrent provider queries with semaphore-based rate limiting (MAX_CONCURRENT=20)

2. **Provider Plugin System (providers/manager.py)**
   - `Providersbase`: Abstract base class with `CACHEABLE` attribute to control caching
   - `ProviderRegistry`: Auto-registration using `__init_subclass__`
   - Shared `ClientSession` across all providers

3. **Database Caching (database/)**
   - PostgreSQL with async SQLAlchemy (asyncpg driver)
   - `CacheService`: Batch query/save operations for answer caching
   - Config-aware caching: same provider with different configs = different cache entries
   - Async cache writes (non-blocking via `asyncio.create_task`)

4. **Answer Aggregation (core.py)**
   - `collect_true_answer()`: Uses Counter to find most common answer (only successful answers)
   - Choice normalization: `['A','B']` == `['B','A']` via tuple sorting

### Request Flow

1. Request arrives with query and provider list
2. Batch query cache for all providers (single DB query)
3. For uncached providers, create async tasks with semaphore protection
4. Aggregate results, async write new answers to cache
5. Return unified answer with per-provider results

### Provider Implementation

```python
from .manager import Providersbase
from model import QuestionContent, Provider, A

class YourProvider(Providersbase):
    name = "Provider Name"  # Must be unique
    CACHEABLE = True  # Set False to disable caching for this provider

    class Configs(BaseModel):
        api_key: str = Field(...)

    async def _search(self, query: QuestionContent, provider: Provider) -> A:
        config = self.Configs(**provider.config)
        # Return A with success=True/False and appropriate fields
        return A(provider=self.name, type=query.type, choice=["A"], success=True)
```

Providers auto-register when placed in `providers/` directory.

### Question Types

- `0`: Single choice → `choice: ["A"]`
- `1`: Multiple choice → `choice: ["A", "B"]`
- `2`: Fill-in-blank → `text: ["answer1", "answer2"]`
- `3`: True/False → `judgement: true/false`
- `4`: Q&A → `text: ["answer"]`

### Environment Variables

Database (PostgreSQL required):
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_ECHO`

Logging:
- `LOG_LEVEL` (default: INFO)
- `LOG_BACKUP_DAYS` (default: 30)

### Current Providers

- **Like知识库** (like.py): LLM-based, paid
- **万能题库** (wanneng.py): Direct lookup
- **言溪题库** (enncy.py)
- **everyAPI** (everyapi.py)
- **本地题库** (local.py): Local database lookup, `CACHEABLE=False`