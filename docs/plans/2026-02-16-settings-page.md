# Settings Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade `/settings` with configurable default USDT address (with second confirmation), USDT API config, BINS API config, and Telegram push/rate controls.

**Architecture:** Extend `SettingsState` as the single source of truth for editable settings and confirmation-flow state. Keep persistence mocked in-state for now and expose explicit save events returning toast feedback. Compose page sections as card blocks and add an alert confirmation dialog for USDT address updates.

**Tech Stack:** Reflex (`rx.State`, `rx.alert_dialog`, `rx.switch`, `rx.input`, `rx.select`), pytest component `repr` assertions, state event unit tests.

---

### Task 1: Add failing tests for settings state and page wiring

**Files:**
- Create: `tests/test_settings_page.py`

**Step 1: Write failing tests**
- Add tests for:
  - default USDT address change requires confirmation before commit.
  - confirm action applies pending address and closes confirm modal.
  - settings page contains required sections and confirmation dialog wiring.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_settings_page.py -v`  
Expected: FAIL because current settings state/page do not include the new behavior.

### Task 2: Implement settings state behavior

**Files:**
- Modify: `test_reflex/pages/settings.py`

**Step 1: Add state fields**
- Add editable fields for:
  - default USDT address and draft/pending value.
  - USDT API endpoint/key/timeout.
  - BINS API endpoint/key/timeout.
  - Telegram push enable, bot token, chat id, push interval/rate, retries.

**Step 2: Add events**
- Add setters for each field.
- Add `request_default_usdt_address_change`, `cancel_default_usdt_address_change`, `confirm_default_usdt_address_change`.
- Add save events for API and Telegram sections with validation + toast feedback.

### Task 3: Implement settings page UI sections

**Files:**
- Modify: `test_reflex/pages/settings.py`

**Step 1: Build section blocks**
- Default USDT address section with input + “save” button.
- USDT query API section.
- BINS query API section.
- Telegram push section (enable switch + rate/retry/token/chat fields).

**Step 2: Add confirmation dialog**
- Add `rx.alert_dialog` bound to state modal boolean.
- Show old/new address summary and confirm/cancel actions.

### Task 4: Verify and regression checks

**Step 1: Run targeted tests**

Run: `uv run pytest tests/test_settings_page.py -v`  
Expected: PASS.

**Step 2: Run related smoke tests**

Run: `uv run pytest tests/test_finance_page.py tests/test_agents_page.py tests/test_merchants_page.py tests/test_settings_page.py -v`  
Expected: PASS.
