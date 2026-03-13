# Merchants Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete `/merchants` management page for super admins, aligned with docs and existing dashboard styles.

**Architecture:** Add a `MerchantState` as the source of truth for merchant records, then render a state-driven `merchants_page` with KPI cards, filters, table actions, and create/edit dialogs. Gate access with `AuthState.is_super_admin`, and wire exports/routes so sidebar navigation resolves correctly.

**Tech Stack:** Reflex, Python `rx.State`, existing `template` layout, existing `card_style`, pytest component repr assertions.

---

### Task 1: Add failing tests for merchants page behavior

**Files:**
- Create: `tests/test_merchants_page.py`

**Step 1: Write failing tests**
- Add tests that assert:
  - merchants table renders from `MerchantState.filtered_merchants`.
  - merchants page uses super-admin gate (`AuthState.is_super_admin`) and warning callout.
  - create/edit modals wire open-change handlers and submit handlers.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_merchants_page.py -v`  
Expected: FAIL because merchants page/state does not exist yet.

### Task 2: Implement MerchantState

**Files:**
- Create: `test_reflex/state/merchant_state.py`
- Modify: `test_reflex/state/__init__.py`

**Step 1: Add minimal state model**
- Seed mock merchants with docs-aligned fields:
  - identity/contact
  - fee rate and wallet
  - verification/active/featured flags
  - product and sales metrics
- Add filters and search:
  - `search_query`, `filter_status`
- Add create/edit modal state and events.
- Add row action events:
  - toggle active
  - toggle featured
  - toggle verified
- Add computed vars:
  - `filtered_merchants`
  - KPI counters and totals.

**Step 2: Keep validation minimal and practical**
- Validate merchant name required.
- Validate fee rate accepts `0-1` or `0-100`.

### Task 3: Implement merchants page UI

**Files:**
- Create: `test_reflex/pages/merchants.py`

**Step 1: Build page sections**
- Header + toolbar actions
- KPI cards
- Filter row
- Table rendered via `rx.foreach(MerchantState.filtered_merchants, ...)`
- Create/edit dialogs
- Super-admin gate with fallback callout

**Step 2: Keep visual language consistent**
- Use `card_style`
- Reuse icon sizing, spacing, color_scheme conventions from `agents.py` and `finance.py`
- Match existing button/toolbar density and table layout rhythm.

### Task 4: Wire page exports and route

**Files:**
- Modify: `test_reflex/pages/__init__.py`
- Modify: `test_reflex/test_reflex.py`

**Step 1: Export `merchants_page` from pages package**
**Step 2: Add `/merchants` route in app entry**

### Task 5: Verify and regressions

**Step 1: Run targeted tests**

Run: `uv run pytest tests/test_merchants_page.py -v`  
Expected: PASS.

**Step 2: Run affected suite smoke**

Run: `uv run pytest tests/test_agents_page.py tests/test_finance_page.py tests/test_merchants_page.py -v`  
Expected: PASS.
