# All Pages DB Integration Phase-1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make all existing Reflex pages load and mutate data from PostgreSQL only, with automatic bootstrap of default super-admin (`admin/admin123`) and empty-db seed data.

**Architecture:** Keep current Reflex app structure, but move all business reads/writes into service/repository modules backed by SQLModel sessions. States become orchestration-only adapters that call services and map results to UI shape. Startup flow initializes schema and idempotent bootstrap data before user-facing interactions.

**Tech Stack:** Reflex, SQLModel, PostgreSQL, pytest, bcrypt

---

### Task 1: Bootstrap Foundation (DB init + default super-admin + seed entrypoint)

**Files:**
- Create: `shared/bootstrap.py`
- Modify: `shared/database.py`
- Modify: `test_reflex/test_reflex.py`
- Test: `tests/test_bootstrap_super_admin.py`

**Step 1: Write failing tests**
- Assert bootstrap creates `admin` super-admin with hashed password.
- Assert repeated bootstrap is idempotent.
- Assert schema init path is called before seeding.

**Step 2: Run tests to verify RED**
- Run: `uv run pytest tests/test_bootstrap_super_admin.py -v`

**Step 3: Minimal implementation**
- Add `bootstrap_super_admin(session)` and `bootstrap_seed_if_empty(session)` helpers.
- Add `run_startup_bootstrap()` that calls schema init and bootstrap.
- Wire startup bootstrap from app entry.

**Step 4: Run tests to verify GREEN**
- Run: `uv run pytest tests/test_bootstrap_super_admin.py -v`

### Task 2: Auth Service and DB-backed Login

**Files:**
- Create: `services/auth_service.py`
- Modify: `test_reflex/state/auth.py`
- Modify: `test_reflex/pages/login.py`
- Test: `tests/test_auth_state_db_login.py`

**Step 1: Write failing tests**
- Assert login reads DB user and validates bcrypt hash.
- Assert successful login populates role/name/avatar and redirects.
- Assert invalid credentials return error.

**Step 2: Run tests to verify RED**
- Run: `uv run pytest tests/test_auth_state_db_login.py -v`

**Step 3: Minimal implementation**
- Implement `authenticate_admin(username, password)` service.
- Replace `TEST_USERS` logic in `AuthState.handle_login` with DB call.
- Keep existing state API stable for current pages.

**Step 4: Run tests to verify GREEN**
- Run: `uv run pytest tests/test_auth_state_db_login.py -v`

### Task 3: Service Skeletons for All Domains (DB-only)

**Files:**
- Create: `services/dashboard_service.py`
- Create: `services/bot_service.py`
- Create: `services/agent_service.py`
- Create: `services/merchant_service.py`
- Create: `services/inventory_service.py`
- Create: `services/order_service.py`
- Create: `services/user_service.py`
- Create: `services/finance_service.py`
- Create: `services/settings_service.py`
- Test: `tests/services/test_domain_services_db_only.py`

**Step 1: Write failing tests**
- Assert each service performs DB session-backed list/create/update actions.
- Assert DB-only mode raises explicit errors when DB is unavailable.

**Step 2: Run tests to verify RED**
- Run: `uv run pytest tests/services/test_domain_services_db_only.py -v`

**Step 3: Minimal implementation**
- Add list/query/update primitives per domain.
- Keep logic YAGNI: only fields needed by existing pages.

**Step 4: Run tests to verify GREEN**
- Run: `uv run pytest tests/services/test_domain_services_db_only.py -v`

### Task 4: Core Transaction Pages to DB (Orders/Users/Finance)

**Files:**
- Modify: `test_reflex/state/order_state.py`
- Modify: `test_reflex/state/user_state.py`
- Modify: `test_reflex/state/finance_state.py`
- Test: `tests/test_orders_users_finance_db_bridge.py`

**Step 1: Write failing tests**
- Assert list/load actions query DB services.
- Assert refund and balance adjustment write DB and audit records.

**Step 2: Run tests to verify RED**
- Run: `uv run pytest tests/test_orders_users_finance_db_bridge.py -v`

**Step 3: Minimal implementation**
- Replace hardcoded arrays with service-driven snapshots.
- Preserve existing page bindings.

**Step 4: Run tests to verify GREEN**
- Run: `uv run pytest tests/test_orders_users_finance_db_bridge.py -v`

### Task 5: Operations Pages to DB (Inventory/Push/Export)

**Files:**
- Modify: `test_reflex/state/inventory.py`
- Modify: `test_reflex/state/push_state.py`
- Modify: `services/push_queue.py`
- Modify: `services/export_task.py`
- Test: `tests/test_inventory_push_export_db_only.py`

**Step 1: Write failing tests**
- Assert inventory list/import uses DB.
- Assert push/export repositories no longer fallback to memory.

**Step 2: Run tests to verify RED**
- Run: `uv run pytest tests/test_inventory_push_export_db_only.py -v`

**Step 3: Minimal implementation**
- Remove memory fallback paths from push/export backend selectors.
- Keep polling/event APIs unchanged.

**Step 4: Run tests to verify GREEN**
- Run: `uv run pytest tests/test_inventory_push_export_db_only.py -v`

### Task 6: Management + Aggregate Pages to DB (Bots/Agents/Merchants/Settings/Dashboard/Profile)

**Files:**
- Modify: `test_reflex/state/bot_state.py`
- Modify: `test_reflex/state/agent_state.py`
- Modify: `test_reflex/state/merchant_state.py`
- Modify: `test_reflex/state/dashboard.py`
- Modify: `test_reflex/pages/settings.py`
- Modify: `test_reflex/pages/profile.py`
- Test: `tests/test_management_dashboard_db_bridge.py`

**Step 1: Write failing tests**
- Assert each state reads from corresponding DB service.
- Assert settings updates persist to `system_settings`.

**Step 2: Run tests to verify RED**
- Run: `uv run pytest tests/test_management_dashboard_db_bridge.py -v`

**Step 3: Minimal implementation**
- Replace static demo state with DB-backed loading.
- Preserve existing component contract for page rendering tests.

**Step 4: Run tests to verify GREEN**
- Run: `uv run pytest tests/test_management_dashboard_db_bridge.py -v`

### Task 7: Full Verification and Documentation

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Test: existing full suite + new DB bridge suites

**Step 1: Run regression suites**
- Run: `uv run pytest -v`

**Step 2: Run live PostgreSQL schema checks**
- Run: `$env:RUN_LIVE_POSTGRES_TESTS='1'; uv run pytest tests/db/test_postgres_live_schema.py -v`

**Step 3: Document runbook**
- Add startup/bootstrap behavior and default admin notes.

**Step 4: Final verification**
- Re-run critical page/service tests and confirm green.
