# DB Push Review (Phase 4) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add persistent push review task model and include it in local/live schema verification.

**Architecture:** Introduce `push_review_tasks` table with explicit status machine (`pending_review/approved/rejected`) and foreign keys to `inventory_libraries`, `merchants`, and reviewer (`admin_users`).

**Tech Stack:** Python 3.12, SQLModel, SQLAlchemy, pytest, PostgreSQL

---

### Task 1: Test-first table contract

**Files:**
- Create: `tests/db/test_phase4_push_review_model.py`

**Checks:**
- Table exists in metadata
- Default status is `pending_review`
- Required FKs exist

### Task 2: Implement model and registration

**Files:**
- Create: `shared/models/push_review.py`
- Modify: `shared/models/__init__.py`
- Modify: `shared/database.py`
- Modify: `tests/db/test_postgres_live_schema.py`

**Outcome:**
- Push review schema is part of create_all and live DB checks.

### Task 3: Verification

**Run:**
- `uv run pytest tests/db/test_phase4_push_review_model.py -v`
- `uv run pytest tests/db/test_phase1_foundation_models.py tests/db/test_phase2_inventory_models.py tests/db/test_phase3_user_export_models.py tests/db/test_phase4_push_review_model.py -v`
- Live checks with `RUN_LIVE_POSTGRES_TESTS=1` and `DATABASE_URL`.
