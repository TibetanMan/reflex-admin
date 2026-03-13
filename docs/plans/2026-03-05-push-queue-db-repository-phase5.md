# Push Queue DB Repository (Phase 5) Implementation Plan

> Status update (2026-03-07): runtime backend policy is DB-only.  
> `memory` backend remains available only for explicit test injection.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Introduce a SQLModel-backed push queue repository while preserving the current in-memory default behavior.

**Architecture:** Keep `InMemoryPushQueueRepository` as the default adapter and add `SqlModelPushQueueRepository` for persistence. Expose explicit switch helpers so runtime and tests can opt into DB mode safely.

**Tech Stack:** Python 3.12, SQLModel, SQLAlchemy, pytest

---

### Task 1: Add failing DB-repository tests

**Files:**
- Create: `tests/services/test_push_queue_db_repository.py`

**Checks:**
- Review dedup + approve flow works in DB repository
- Campaign queue + process + audit flow works in DB repository

### Task 2: Implement SQLModel repository and backend switches

**Files:**
- Modify: `services/push_queue.py`
- Modify: `shared/models/push_review.py`

**Outcome:**
- New `SqlModelPushQueueRepository`
- New switch helpers: `set_push_queue_repository`, `use_in_memory_push_repository`, `use_database_push_repository`
- Env-based default selection via `PUSH_QUEUE_BACKEND` (`memory` default)

### Task 3: Verification

**Run:**
- `uv run pytest tests/services/test_push_queue_db_repository.py -v`
- `uv run pytest tests/services/test_push_queue.py tests/services/test_push_queue_db_repository.py tests/test_push_page.py tests/test_inventory_push_bridge.py -v`
- DB schema regressions + optional live PostgreSQL checks.

### Task 4: Live DB compatibility migration (existing `push_review_tasks`)

**SQL (idempotent):**
- Add missing snapshot columns: `inventory_id`, `inventory_name`, `merchant_name`, `reviewed_by_name`
- Relax legacy constraints: drop `NOT NULL` from `inventory_library_id`, `merchant_id`

**Purpose:**
- Ensure DB repository can persist review tasks even before full inventory/merchant FK chain is fully landed in UI workflow.

