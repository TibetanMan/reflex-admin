# Message Push Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a super-admin-only message push center in sidebar core features, with inventory-review workflow, bot/library linkage, global markdown push, queued dispatch, and database-ready backend interfaces.

**Architecture:** Introduce a dedicated push domain with three layers: `services/push_queue.py` as the backend-facing queue/redundancy abstraction (in-memory for now but DB-ready), `test_reflex/state/push_state.py` as orchestration and permission gate, and `test_reflex/pages/push.py` as the super-admin UI. Inventory import flow will register pending review tasks and redirect to the push page for approval.

**Tech Stack:** Reflex pages/states, SQLModel schema definitions for persistence readiness, in-memory repository adapter, pytest repr/state/service tests.

---

### Task 1: Add failing tests for push page, queue service, and inventory bridge

**Files:**
- Create: `tests/test_push_page.py`
- Create: `tests/services/test_push_queue.py`
- Create: `tests/test_inventory_push_bridge.py`

**Step 1: Write failing tests**
- Push page:
  - super-admin gate exists.
  - review table binds to state queue.
  - compose area binds inventory/bot options and push handlers.
  - sidebar core menu contains push route entry.
- Queue service:
  - inventory review task deduplicates.
  - campaign enqueue deduplicates by dedup key.
  - queue processing writes sent status and audit traces.
- Inventory bridge:
  - successful import registers pending push review record.
  - successful import returns redirect to `/push`.

**Step 2: Run tests to verify failures**

Run:
- `uv run pytest tests/test_push_page.py -v`
- `uv run pytest tests/services/test_push_queue.py -v`
- `uv run pytest tests/test_inventory_push_bridge.py -v`

Expected: FAIL before implementation.

### Task 2: Build backend-ready push domain and queue/redundancy layer

**Files:**
- Create: `services/push_queue.py`
- Create: `shared/models/push_message.py`
- Modify: `shared/models/__init__.py`
- Modify: `shared/database.py`

**Step 1: Add SQLModel persistence schemas (prepared, not wired)**
- `PushMessageTask` table:
  - scope/status/priority/partition/retry/failover fields
  - content fields (ad text + markdown)
  - target dimensions (inventory ids, bot ids, global push)
  - auditing fields (created_by/approved_by timestamps)
- `PushMessageAuditLog` table:
  - action trail for review/approval/queue/process outcomes.

**Step 2: Add queue service abstraction**
- Repository protocol + in-memory adapter.
- APIs:
  - register inventory review
  - list review queue
  - enqueue push campaign
  - process queue batch (with retry/failover markers)
  - list push records
  - list audit logs
  - reset storage (for tests)
- Redundancy/dedup strategy:
  - deterministic dedup key (scope + targets + content hash)
  - retry counters + max retry
  - failover channel flag.

### Task 3: Implement push state and push page UI with strict permissions

**Files:**
- Create: `test_reflex/state/push_state.py`
- Create: `test_reflex/pages/push.py`
- Modify: `test_reflex/state/__init__.py`
- Modify: `test_reflex/pages/__init__.py`

**Step 1: PushState orchestration**
- Inventory/Bot linked options.
- Review queue + push record projections.
- Global push toggle + markdown/ad content.
- Queue/approval actions guarded by role argument check (`super_admin` only).
- Provide backend interface methods wrapping queue service.

**Step 2: Push page composition**
- Header + KPI cards (pending/queued/sent/failed).
- Pending review table with approve-and-fill workflow.
- Compose panel:
  - select inventory and bots
  - global push toggle
  - markdown/ad text editor
  - redundancy and queue config
- Queue records table + process queue action.
- `AuthState.is_super_admin` gate and deny callout.

### Task 4: Wire sidebar route and inventory auto-redirect workflow

**Files:**
- Modify: `test_reflex/components/sidebar.py`
- Modify: `test_reflex/test_reflex.py`
- Modify: `test_reflex/state/inventory.py`

**Step 1: Route and navigation**
- Add `/push` page route registration.
- Add push entry under sidebar “核心功能” (super-admin visible only).

**Step 2: Inventory -> push auto workflow**
- On successful inventory import:
  - register pending review task in push queue service.
  - redirect to `/push` for immediate super-admin review.

### Task 5: Verification

**Step 1: Run new targeted tests**
- `uv run pytest tests/test_push_page.py tests/services/test_push_queue.py tests/test_inventory_push_bridge.py -v`

Expected: PASS.

**Step 2: Run affected regression suite**
- `uv run pytest tests/test_finance_page.py tests/test_agents_page.py tests/test_merchants_page.py tests/test_settings_page.py tests/test_push_page.py tests/services/test_push_queue.py tests/test_inventory_push_bridge.py -v`

Expected: PASS.
