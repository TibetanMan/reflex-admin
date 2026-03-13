# DB User Source + Export Task (Phase 3) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add user multi-bot source mapping and unified export task models, then verify schema against live PostgreSQL.

**Architecture:** Add two new tables (`user_bot_sources`, `export_tasks`) with explicit status/type enums and unique constraint on (`user_id`, `bot_id`). Keep runtime logic unchanged for now and validate schema locally plus live DB smoke tests.

**Tech Stack:** Python 3.12, SQLModel, SQLAlchemy, pytest, PostgreSQL

---

### Task 1: Test-first schema contract

**Files:**
- Create: `tests/db/test_phase3_user_export_models.py`

**Checks:**
- New tables are registered
- (`user_id`, `bot_id`) unique constraint exists
- Export progress columns exist
- Export defaults: `status=pending`, `type=order`

### Task 2: Implement models and registration

**Files:**
- Create: `shared/models/user_export.py`
- Modify: `shared/models/__init__.py`
- Modify: `shared/database.py`

**Outcome:**
- `UserBotSource` and `ExportTask` become part of metadata and DB bootstrap import chain.

### Task 3: Live PostgreSQL verification

**Files:**
- Create: `tests/db/test_postgres_live_schema.py`

**Run condition:**
- `RUN_LIVE_POSTGRES_TESTS=1`
- `DATABASE_URL=postgresql+asyncpg://...`

**Checks:**
- `create_all(checkfirst)` can run against live DB
- Required tables are present
- Numeric precision and unique constraints stay correct
