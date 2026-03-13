# Export Task Persistence (Phase 6) Implementation Plan

> Status update (2026-03-07): runtime backend policy is DB-only.  
> `memory` backend remains available only for explicit test injection.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Persist order/user export lifecycle to `export_tasks` so task status and files are traceable beyond in-memory state.

**Architecture:** Add a repository abstraction in `services` with both in-memory and SQLModel adapters, mirroring the push queue pattern. Keep current UI behavior intact, but replace transient task IDs and status/progress bookkeeping with `ExportTask` create/update operations in `OrderState` and `UserState`.

**Tech Stack:** Python 3.12, SQLModel, SQLAlchemy, pytest, Reflex state events

---

### Task 1: Add failing repository tests

**Files:**
- Create: `tests/services/test_export_task_repository.py`
- Create: `tests/services/test_export_task_backend_selection.py`

**Checks:**
- In-memory repository can create/get/update export tasks.
- SQLModel repository can create/get/update tasks against SQLite test DB.
- Backend auto-selection defaults to memory and can switch to DB when `EXPORT_TASK_BACKEND=db`.

### Task 2: Implement export task repository service

**Files:**
- Create: `services/export_task.py`

**Outcome:**
- `InMemoryExportTaskRepository` + `SqlModelExportTaskRepository`
- Function API: `create_export_task`, `update_export_task`, `get_export_task`
- Backend switch helpers:
  - `set_export_task_repository`
  - `use_in_memory_export_task_repository`
  - `use_database_export_task_repository`
  - `get_export_task_backend_name`
  - `ensure_export_task_repository_from_env`

### Task 3: Add failing state-integration tests

**Files:**
- Create: `tests/test_order_state_export_persistence.py`
- Create: `tests/test_user_state_export_persistence.py`

**Checks:**
- `OrderState.export_orders` creates `ExportTask`.
- `OrderState.run_export_task` updates `ExportTask` progress/final status.
- `UserState.export_users` creates and updates `ExportTask`.

### Task 4: Wire order/user export flows to persistence

**Files:**
- Modify: `test_reflex/state/order_state.py`
- Modify: `test_reflex/state/user_state.py`

**Outcome:**
- Order export task ID comes from repository (instead of random UUID).
- Processing/completed/failed states sync into `export_tasks`.
- User export writes pending/processing/completed/failed updates into `export_tasks`.

### Task 5: Verification

**Run:**
- `uv run pytest tests/services/test_export_task_repository.py tests/services/test_export_task_backend_selection.py -v`
- `uv run pytest tests/test_order_state_export_persistence.py tests/test_user_state_export_persistence.py -v`
- `uv run pytest tests/services/test_order_export.py tests/test_orders_page.py tests/test_push_page.py tests/test_push_state_seed.py -v`
- Optional live DB smoke:
  - `RUN_LIVE_POSTGRES_TESTS=1`
  - `DATABASE_URL=postgresql+asyncpg://postgres:qAz1.2.3@192.168.31.72:5432/reflex`
  - `uv run pytest tests/db/test_postgres_live_schema.py -v`
