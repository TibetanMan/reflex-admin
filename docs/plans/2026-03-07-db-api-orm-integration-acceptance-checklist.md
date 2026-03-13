# DB/API/ORM Integration Acceptance Checklist (2026-03-07)

This checklist reconciles the current implementation against:

- `docs/plans/2026-03-06-all-pages-db-integration-design.md`
- `docs/db_api_orm_integration_spec.md`

## 1. Design Acceptance (Section 7.2) Status

1. `All page data comes from PostgreSQL` -> **Done**
- Evidence: state bridge tests cover all page domains:
  - `tests/test_management_dashboard_db_bridge.py`
  - `tests/test_order_state_db_bridge.py`
  - `tests/test_user_state_db_bridge.py`
  - `tests/test_finance_state_db_bridge.py`
  - `tests/test_settings_profile_inventory_db_bridge.py`
  - `tests/test_table_page_db_bridge.py`
  - `tests/test_inventory_push_bridge.py`
- Evidence: UI action bindings and side effects are enforced:
  - `tests/test_page_action_bindings.py`
  - `tests/test_key_action_side_effects.py`

2. `Default super admin admin/admin123 can log in` -> **Done**
- Evidence:
  - `tests/test_bootstrap_super_admin.py` validates bootstrap creation and password hashing.
  - `tests/test_auth_state_db_login.py` validates login state path via DB auth service.
- Runtime smoke: `authenticate_admin("admin", "admin123")` returns `admin/super_admin`.

3. `Critical actions are auditable and traceable` -> **Done (core flows)**
- Evidence:
  - Orders refund writes balance ledger + admin audit:
    - `tests/services/test_order_service.py`
  - User ban/balance adjustment writes audit + ledger with idempotent `request_id`:
    - `tests/services/test_user_service.py`
  - Finance manual deposit persists deposit + balance ledger:
    - `tests/services/test_finance_service.py`
  - Settings persistence to `system_settings`:
    - `tests/services/test_settings_service.py`

4. `Full test suite passes` -> **Done**
- Latest run: `244 passed, 2 skipped` (`uv run pytest -q`, 2026-03-08).

5. `Startup fails explicitly on DB failure, no memory fallback` -> **Done**
- Evidence:
  - Startup strict mode is now default:
    - `test_reflex/test_reflex.py` (`_run_startup_bootstrap_with_guard` defaults strict to `"1"`).
  - Runtime backend env is forced to DB:
    - `test_reflex/test_reflex.py` (`_sync_runtime_backend_env`).
  - Export/push env-based `memory` backend is blocked outside test context:
    - `services/export_task.py`
    - `services/push_queue.py`
  - Tests:
    - `tests/test_app_startup_bootstrap.py`
    - `tests/services/test_export_task_backend_selection.py`
    - `tests/services/test_push_queue_backend_selection.py`
  - DB init error messaging remains explicit and actionable:
    - `tests/test_database_init_errors.py`

## 2. Live PostgreSQL Verification

Status: **Done** using:

- `DATABASE_URL=postgresql+asyncpg://postgres:qAz1.2.3@192.168.31.72:5432/reflex`
- `RUN_LIVE_POSTGRES_TESTS=1`

Evidence:

- `uv run pytest -q tests/db/test_postgres_live_schema.py` -> `2 passed`.

Notes:

- `127.0.0.1:5432` failed password auth in current environment.
- Host IP `192.168.31.72` is confirmed working.

## 3. Spec-Level API Coverage (from db_api_orm_integration_spec.md)

Status: **Done for route parity (spec section 5 + 6 endpoints)**.

Completed (implemented in `services/reflex_api.py` and tested by `tests/api/test_phase2_http_api_bridge.py`):

- Auth: `POST /api/v1/auth/login`
- Auth/session: `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `POST /api/v1/auth/logout`, `POST /api/v1/auth/refresh`
- Dashboard: `GET /api/v1/dashboard/summary`, `GET /api/v1/dashboard/recent-orders`, `GET /api/v1/dashboard/recent-deposits`, `GET /api/v1/dashboard/top-categories`, `GET /api/v1/dashboard/bot-status`
- Bots/Agents/Merchants: CRUD/status endpoints + detail routes (`GET /{id}`)
- Inventory: list/import/price/status/delete + options + import-task detail + library items
- Orders: list + detail + refund + refresh-status + export create route alias
- Users: list + detail + status + ban + balance-adjustments + deposit/purchase records + export create route alias
- Finance: deposits/wallets/manual-deposit + `/finance/deposits/manual` alias + wallet detail
- Push: reviews approve/list + campaigns/process/cancel + audits/reset + `/push/queue/poll` alias
- Settings: get + update endpoints
- Profile: get + patch + password update
- Export tasks: ensure/create/list/update/snapshot/download + `/exports/{id}` aliases
- Bot-side: full spec section 6 route set (`/api/v1/bot/*`, 13 endpoints)

Remaining (non-route standards from spec sections 2/3/10):

1. Unified response envelope (`code/message/data`) is not adopted across all routes.
2. JWT/refresh-token security model is not fully implemented; current auth tokens are lightweight service payloads.
3. Full RBAC + row-level data-domain enforcement is not yet centralized in dispatcher/service guards.

Model-level ORM/DB optimization from spec section 4.3: **Done**.

- Amount persistence columns now use `NUMERIC(18,2)` in the core money domains (`users`, `agents`, `merchants`, `categories`, `cart_items`, `bot_instances`, `orders`, `order_items`, `deposits`, `wallet_addresses`, `product_items`).
- Spec-recommended FK upgrades are in place for `orders.bot_id`, `deposits.bot_id`, `wallet_addresses.bot_id`.
- High-frequency composite indexes are in place for orders/deposits/product_items/push_message_tasks.
- Structural regression coverage:
  - `tests/db/test_phase5_orm_db_optimizations.py`

## 4. Conclusion

Mainline objective "all existing pages DB-connected and DB-only runtime" is complete and verified.

Route-level spec parity is complete. Remaining work is primarily **non-functional governance alignment** (security, RBAC, response contract), not page DB integration, schema optimization, or route coverage.
