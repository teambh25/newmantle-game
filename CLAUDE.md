# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Korean word guessing game API (similar to Semantle). FastAPI backend with Redis as the sole data store, fronted by Nginx with SSL.

## Commands

```bash
# Run all containers
sudo docker-compose up -d

# Run tests
docker-compose run --rm --entrypoint "" fastapi python -m pytest

# Lint & format (from fastapi/ directory)
cd fastapi && ruff check --fix && ruff format

# Run a single test
docker-compose run --rm --entrypoint "" fastapi python -m pytest tests/unit/game/test_service.py -v
```

## Architecture

```
Client -> Nginx (SSL) -> FastAPI (port 8080) -> Redis
```

- **No database** - Redis-only with AOF persistence. Data auto-expires via TTL (2 days).
- **4 Docker services**: fastapi, redis, nginx, certbot (auto-renewal)

### Code Structure (`fastapi/app/`)

Layered architecture: **Routers -> Services -> Repositories**
- `features/game/` - Game endpoints (v1 legacy at `/quizzes/`, v2 at `/v2/quizzes/`)
- `features/admin/` - Quiz CRUD (HTTP Basic Auth protected)
- `cores/` - Config (pydantic Settings), Redis pool, auth, logging, lifespan events
- `dependencies/` - FastAPI `Depends()` wiring for services, repos, Redis client
- `schemas/` - Pydantic request/response models
- `utils.py` - Hangul validation, initial consonant extraction, date/timezone helpers

### Redis Key Patterns

- `quiz:{date}:answers` (string) - Answer JSON (word, tag, description)
- `quiz:{date}:scores` (hash) - word -> `{score}|{rank}`
- `quiz:{date}:ranking` (hash) - rank -> `{word}|{score}`

### Key Conventions

- **Timezone**: Seoul (KST, UTC+9) via `ZoneInfo`. Game log rotation at 15:00 UTC (= midnight KST).
- **Korean text**: Answers must be pure Hangul (가-힣). `utils.py` handles validation and initial consonant extraction.
- **API versioning**: v1 returns simple responses; v2 returns answer metadata on correct guess / give-up.
- **Exception flow**: Custom `BaseAppException` hierarchy -> exception handlers in `exceptions/handlers.py`.
- **Logging**: Loguru with two sinks - `logs/app.log` (weekly) and `logs/game/{date}.log` (daily).
- **Tests**: pytest + pytest-asyncio + pytest-mock. Tests are in `fastapi/tests/unit/`.

##

- **v1 is finalized and currently in production. Do not app/features/game/v1 modify this version**
- Please write all comments in **English instead of Korean**.