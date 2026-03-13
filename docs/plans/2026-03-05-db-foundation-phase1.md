# DB Foundation (Phase 1) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add foundational persistence models for configuration, audit, and balance ledgers without requiring a live PostgreSQL connection.

**Architecture:** Add three SQLModel tables (`system_settings`, `admin_audit_logs`, `balance_ledgers`) and register them in model exports and DB bootstrap import path. Validate schema shape via metadata-driven tests so local development can verify behavior with no running DB.

**Tech Stack:** Python 3.12, SQLModel, SQLAlchemy, pytest

---

### Task 1: Add failing schema tests first

**Files:**
- Create: `tests/db/test_phase1_foundation_models.py`

**Step 1:** Write failing tests for:
- New tables exist in `SQLModel.metadata`
- `balance_ledgers.amount/before_balance/after_balance` are `NUMERIC(18,2)`
- Unique keys for `system_settings.key` and `balance_ledgers.request_id`

**Step 2:** Run targeted pytest file and confirm failures.

### Task 2: Implement minimal models and registration

**Files:**
- Create: `shared/models/system_setting.py`
- Create: `shared/models/admin_audit_log.py`
- Create: `shared/models/balance_ledger.py`
- Modify: `shared/models/__init__.py`
- Modify: `shared/database.py`

**Step 1:** Implement minimal fields required by spec phase 1.

**Step 2:** Export/import models so metadata registration includes new tables.

**Step 3:** Re-run targeted pytest file and ensure all tests pass.

### Task 3: Regression safety run

**Files:**
- Modify: none

**Step 1:** Run relevant existing tests that touch push/inventory/settings state to ensure no regression.

**Step 2:** Summarize changes and list next phase options.
