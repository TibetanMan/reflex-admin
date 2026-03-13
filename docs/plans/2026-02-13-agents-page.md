# Agents Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete `/agents` management page for super admins, aligned with docs and existing dashboard visual language.

**Architecture:** Add a new `AgentState` as the single source of truth for agents, then render a state-driven `agents_page` with cards, filters, table, and create/edit dialogs. Gate the full page with `AuthState.is_super_admin` and wire route/export so sidebar navigation works.

**Tech Stack:** Reflex, Python state management (`rx.State`), existing `template` layout, existing `card_style`.

---

### Task 1: Create failing tests for agents page behaviors

**Files:**
- Create: `tests/test_agents_page.py`
- Test: `tests/test_agents_page.py`

**Step 1: Write failing tests**

```python
def test_agents_page_is_state_driven_and_not_static():
    ...
```

```python
def test_agents_page_has_super_admin_gate():
    ...
```

```python
def test_agent_modals_wire_open_change_and_submit_handlers():
    ...
```

**Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_agents_page.py -v`  
Expected: FAIL (page/state not implemented yet)

### Task 2: Implement AgentState

**Files:**
- Create: `test_reflex/state/agent_state.py`
- Modify: `test_reflex/state/__init__.py`

**Step 1: Write minimal state implementation**
- Seed mock agent rows with fields required by docs (`name`, `bot_token`, `profit_rate`, `usdt_address`, `is_active`, `is_verified`, metrics)
- Add filters (`search_query`, `filter_status`)
- Add events for create/edit/toggle (`open_create_modal`, `save_new_agent`, `open_edit_modal`, `save_edit_agent`, `toggle_agent_status`)
- Add computed list (`filtered_agents`) and metrics (`total_agents`, `active_agents`, `verified_agents`, `total_agent_profit`)

**Step 2: Verify with tests**

Run: `uv run pytest tests/test_agents_page.py -v`

### Task 3: Implement Agents page UI

**Files:**
- Create: `test_reflex/pages/agents.py`

**Step 1: Build page sections**
- Stats cards
- Filters row
- State-driven table via `rx.foreach(AgentState.filtered_agents, ...)`
- Create/Edit dialogs
- Super-admin gate via `rx.cond(AuthState.is_super_admin, ...)`

**Step 2: Keep visual consistency**
- Use `template`
- Use `card_style`
- Use same icon, spacing, button/toolbar patterns as `users/orders/finance`

**Step 3: Verify targeted tests**

Run: `uv run pytest tests/test_agents_page.py -v`

### Task 4: Wire routing and exports

**Files:**
- Modify: `test_reflex/pages/__init__.py`
- Modify: `test_reflex/test_reflex.py`

**Step 1: Export `agents_page` in pages module**

**Step 2: Add `/agents` route**

**Step 3: Verify route-related render**

Run: `uv run pytest tests/test_agents_page.py -v`

### Task 5: Final verification

**Files:**
- Test only

**Step 1: Run full test suite**

Run: `uv run pytest -v`  
Expected: PASS (no regressions)

**Step 2: Summarize implemented capabilities and docs mapping**
