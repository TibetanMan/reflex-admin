# DB Inventory Chain (Phase 2) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add inventory-library and import-task persistence schema required by the inventory page and importer pipeline.

**Architecture:** Introduce normalized inventory-level tables (`inventory_libraries`, `inventory_import_tasks`, `inventory_import_line_errors`) and connect row-level `product_items` through `inventory_library_id`. Validate schema contract via metadata tests before any live PostgreSQL migration.

**Tech Stack:** Python 3.12, SQLModel, SQLAlchemy, pytest

---

### Task 1: Write failing schema tests

**Files:**
- Create: `tests/db/test_phase2_inventory_models.py`

**Checks:**
- New tables are present in `SQLModel.metadata`
- Library price fields use `NUMERIC(18,2)`
- Import task status default is `pending`
- `product_items.inventory_library_id` exists and has FK

### Task 2: Implement schema and registration

**Files:**
- Create: `shared/models/inventory.py`
- Modify: `shared/models/product.py`
- Modify: `shared/models/__init__.py`
- Modify: `shared/database.py`

**Outcome:**
- New inventory models exported and included in DB bootstrap imports.
- Product row model now references inventory library.

### Task 3: Verification

**Files:**
- Modify: none

**Run:**
- `uv run pytest tests/db/test_phase2_inventory_models.py -v`
- Selected regression suite for inventory/push/settings/finance/orders.
