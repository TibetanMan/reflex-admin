# Bot Account Isolation and Bots Metrics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Isolate balances and cart state per bot for the same Telegram user and make Bots page revenue/user metrics update from real sales data.

**Architecture:** Keep `users` as global identity and add a bot-scoped account model (`bot_user_accounts`) for funds and usage stats. Route bot-side balance/checkout/cart through the account context `(user_id, bot_id)` and recalculate bots snapshot metrics from accounts and orders.

**Tech Stack:** Python, SQLModel, Reflex service layer, pytest.

---

### Task 1: Add failing tests for isolation and metrics

**Files:**
- Modify: `tests/services/test_bot_side_service.py`
- Modify: `tests/bot/test_runtime_context.py`

1. Add tests for per-bot account balance isolation and bot-scoped cart behavior.
2. Add test proving bots snapshot revenue/users changes after checkout.
3. Add runtime test proving same Telegram user on two tokens creates two bot accounts.
4. Run targeted tests and confirm RED.

### Task 2: Add bot user account model and schema wiring

**Files:**
- Create: `shared/models/bot_user_account.py`
- Modify: `shared/models/__init__.py`
- Modify: `shared/database.py`
- Modify: `shared/schema_patch.py`

1. Add new SQLModel table and constraints.
2. Ensure table is imported into model registry and init path.
3. Add runtime schema patch for environments without migrations.

### Task 3: Implement bot-scoped account and cart logic

**Files:**
- Modify: `services/bot_side_service.py`
- Modify: `services/bot_side_api.py`
- Modify: `services/reflex_api.py`
- Modify: `bot/runtime_context.py`
- Modify: `bot/handlers/start.py`
- Modify: `bot/handlers/menu.py`

1. Add account ensure/load helpers and replace direct `user.balance` usage.
2. Add `cart_items.bot_id` support and include bot context in cart APIs.
3. Add `bot_id` support for balance/order listing endpoints and client wrappers.
4. Ensure runtime identity creates bot account for `(user, bot)`.

### Task 4: Implement Bots snapshot metric recompute

**Files:**
- Modify: `services/bot_service.py`

1. Recompute users/orders/revenue per bot from accounts + orders when listing bots.
2. Keep output payload shape stable for existing state/page layer.

### Task 5: GREEN and regression verification

**Files:**
- Modify tests if assertions need exact numeric alignment.

1. Run focused tests for changed modules.
2. Run broader regression tests for bots page and bot services.
3. Fix regressions and rerun until all selected suites pass.
