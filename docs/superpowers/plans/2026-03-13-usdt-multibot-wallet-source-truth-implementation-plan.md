# USDT Multi-Bot Wallet Source of Truth Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce `wallet_addresses(bot_id)` as the only address source for all new USDT recharge creation paths, blocking creation when a bot wallet is missing.

**Architecture:** Add a single wallet-resolution helper at the service boundary and route all deposit creation paths through it. Keep API contracts unchanged and propagate business errors to bot/admin UI without fallback addresses. Preserve existing chain reconciliation/runtime behavior and validate via targeted multi-bot tests plus regression suites.

**Tech Stack:** Python 3.12, SQLModel, Reflex state/pages, pytest, uv

---

## Skills To Apply During Execution

- `@superpowers/test-driven-development`
- `@superpowers/verification-before-completion`
- `@superpowers/systematic-debugging` (only if a test fails unexpectedly)

## Scope Check

This plan covers one focused subsystem: USDT deposit address source-of-truth hardening for future records. It does not include historical backfill or schema migration.

## File Structure (Lock Before Coding)

- Create: `services/deposit_wallet_resolver.py`
  - Responsibility: single source wallet resolution by `bot_id` with strict error behavior.
- Modify: `services/bot_side_service.py`
  - Responsibility impacted: bot recharge creation path (`create_bot_deposit`) must use strict resolver, no fallback.
- Modify: `services/finance_service.py`
  - Responsibility impacted: admin manual deposit path (`create_manual_deposit`) must use strict resolver, no fallback.
- Create: `tests/services/test_deposit_wallet_resolver.py`
  - Responsibility: direct unit tests for resolver behavior.
- Modify: `tests/services/test_bot_side_service.py`
  - Responsibility: TDD coverage for strict block + multi-bot wallet mapping in bot recharge creation.
- Modify: `tests/services/test_finance_service.py`
  - Responsibility: TDD coverage for strict block in manual deposit.
- Optional Modify (only if needed for deterministic errors): `tests/api/test_phase2_http_api_bridge.py`
  - Responsibility: route-level error propagation assertion for missing wallet scenarios.

## Preflight

### Task 0: Validate Execution Workspace

**Files:**
- Modify: none
- Test: none

- [ ] **Step 1: Ensure execution isolation (recommended)**

Run: `git worktree list`
Expected: verify worktree context; if absent, create a dedicated one before implementation.

- [ ] **Step 2: Baseline smoke before changes**

Run: `uv run pytest tests/services/test_bot_side_service.py tests/services/test_finance_service.py tests/services/test_deposit_reconcile_runtime.py -q`
Expected: PASS on current baseline.

## Chunk 1: Shared Wallet Resolver

### Task 1: Add failing tests for strict wallet resolution

**Files:**
- Create: `tests/services/test_deposit_wallet_resolver.py`
- Test: `tests/services/test_deposit_wallet_resolver.py`

- [ ] **Step 1: Write failing test for success case (`bot_id` wallet exists)**

```python
from sqlmodel import select


def test_resolve_wallet_by_bot_returns_target_wallet(tmp_path):
    from services.deposit_wallet_resolver import resolve_wallet_by_bot_or_raise
    # setup DB with two wallets for two bots
    wallet = resolve_wallet_by_bot_or_raise(session, bot_id=2)
    assert int(wallet.bot_id or 0) == 2
    assert str(wallet.address) == "TRX_BOT_2"
```

- [ ] **Step 2: Write failing test for missing wallet strict-block**

```python
import pytest


def test_resolve_wallet_by_bot_raises_when_missing(tmp_path):
    from services.deposit_wallet_resolver import resolve_wallet_by_bot_or_raise
    with pytest.raises(ValueError, match="wallet"):
        resolve_wallet_by_bot_or_raise(session, bot_id=9)
```

- [ ] **Step 3: Write failing test for inactive wallet strict-block**

```python
import pytest


def test_resolve_wallet_by_bot_raises_when_inactive(tmp_path):
    from services.deposit_wallet_resolver import resolve_wallet_by_bot_or_raise
    with pytest.raises(ValueError, match="active"):
        resolve_wallet_by_bot_or_raise(session, bot_id=3)
```

- [ ] **Step 4: Run tests to verify RED**

Run: `uv run pytest tests/services/test_deposit_wallet_resolver.py -q`
Expected: FAIL with import/function-not-found errors.

### Task 2: Implement minimal resolver

**Files:**
- Create: `services/deposit_wallet_resolver.py`
- Test: `tests/services/test_deposit_wallet_resolver.py`

- [ ] **Step 1: Implement resolver with strict rules**

```python
from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from shared.models.wallet import WalletAddress, WalletStatus


def resolve_wallet_by_bot_or_raise(session: Session, *, bot_id: int) -> WalletAddress:
    wallet: Optional[WalletAddress] = session.exec(
        select(WalletAddress)
        .where(WalletAddress.bot_id == int(bot_id))
        .order_by(WalletAddress.id.asc())
    ).first()
    if wallet is None:
        raise ValueError("Current bot has no configured receiving wallet.")

    status_text = str(wallet.status.value if hasattr(wallet.status, "value") else wallet.status)
    if status_text != WalletStatus.ACTIVE.value:
        raise ValueError("Current bot wallet is not active.")
    return wallet
```

- [ ] **Step 2: Run tests to verify GREEN**

Run: `uv run pytest tests/services/test_deposit_wallet_resolver.py -q`
Expected: PASS.

- [ ] **Step 3: Commit chunk**

```bash
git add services/deposit_wallet_resolver.py tests/services/test_deposit_wallet_resolver.py
git commit -m "test+feat: add strict wallet resolver by bot id"
```

## Chunk 2: Bot-Side Deposit Creation Hardening

### Task 3: Add failing tests for bot recharge path strictness

**Files:**
- Modify: `tests/services/test_bot_side_service.py`
- Test: `tests/services/test_bot_side_service.py`

- [ ] **Step 1: Add failing test (missing bot wallet blocks creation)**

```python
import pytest


def test_create_bot_deposit_blocks_when_target_bot_wallet_missing(tmp_path):
    from services.bot_side_service import create_bot_deposit
    # setup bot exists, user exists, but no wallet for bot_id=2
    with pytest.raises(ValueError, match="wallet"):
        create_bot_deposit(user_id=1, amount=9.9, bot_id=2, session_factory=session_factory)
```

- [ ] **Step 2: Add failing test (must not fallback to first wallet)**

```python
import pytest


def test_create_bot_deposit_does_not_fallback_to_other_bot_wallet(tmp_path):
    from services.bot_side_service import create_bot_deposit
    # setup wallet only for bot_id=1; request bot_id=2
    with pytest.raises(ValueError, match="wallet"):
        create_bot_deposit(user_id=1, amount=9.9, bot_id=2, session_factory=session_factory)
```

- [ ] **Step 3: Add failing test (multi-bot uses correct wallet per bot)**

```python

def test_create_bot_deposit_uses_wallet_address_of_requested_bot(tmp_path):
    from services.bot_side_service import create_bot_deposit
    dep1 = create_bot_deposit(user_id=1, amount=10, bot_id=1, session_factory=session_factory)
    dep2 = create_bot_deposit(user_id=1, amount=11, bot_id=2, session_factory=session_factory)
    assert dep1["to_address"] == "TRX_WALLET_BOT_1"
    assert dep2["to_address"] == "TRX_WALLET_BOT_2"
```

- [ ] **Step 4: Run tests to verify RED**

Run: `uv run pytest tests/services/test_bot_side_service.py -k "deposit and wallet" -q`
Expected: FAIL on new expectations.

### Task 4: Implement minimal bot-side changes

**Files:**
- Modify: `services/bot_side_service.py`
- Test: `tests/services/test_bot_side_service.py`

- [ ] **Step 1: Replace fallback wallet/address logic in `create_bot_deposit`**

```python
from services.deposit_wallet_resolver import resolve_wallet_by_bot_or_raise

# inside create_bot_deposit(...)
wallet = resolve_wallet_by_bot_or_raise(session, bot_id=int(bot.id or 0))
to_address = str(wallet.address).strip()
if not to_address:
    raise ValueError("Current bot has no configured receiving wallet.")
```

- [ ] **Step 2: Remove legacy fallback behavior**

Delete behavior that:
- picks first wallet globally when bot wallet missing
- falls back to `bot.usdt_address`

- [ ] **Step 3: Run focused tests to verify GREEN**

Run: `uv run pytest tests/services/test_bot_side_service.py -k "deposit" -q`
Expected: PASS.

- [ ] **Step 4: Commit chunk**

```bash
git add services/bot_side_service.py tests/services/test_bot_side_service.py
git commit -m "test+feat: enforce bot wallet source for bot-side deposits"
```

## Chunk 3: Finance Manual Deposit Hardening

### Task 5: Add failing tests for manual deposit strictness

**Files:**
- Modify: `tests/services/test_finance_service.py`
- Test: `tests/services/test_finance_service.py`

- [ ] **Step 1: Add failing test (manual deposit blocks without bot wallet)**

```python
import pytest


def test_create_manual_deposit_blocks_when_bot_wallet_missing(tmp_path):
    from services.finance_service import create_manual_deposit
    # setup user->bot mapping where bot has no wallet
    with pytest.raises(ValueError, match="wallet"):
        create_manual_deposit(
            user_identifier="123456789",
            amount="10.00",
            remark="manual",
            operator_username="admin",
            session_factory=session_factory,
        )
```

- [ ] **Step 2: Add failing test (no fallback to bot.usdt_address)**

```python
import pytest


def test_create_manual_deposit_does_not_fallback_to_bot_usdt_address(tmp_path):
    from services.finance_service import create_manual_deposit
    # bot.usdt_address exists but wallet row absent
    with pytest.raises(ValueError, match="wallet"):
        create_manual_deposit(...)
```

- [ ] **Step 3: Run tests to verify RED**

Run: `uv run pytest tests/services/test_finance_service.py -k "manual_deposit and wallet" -q`
Expected: FAIL on new wallet constraints.

### Task 6: Implement minimal finance changes

**Files:**
- Modify: `services/finance_service.py`
- Test: `tests/services/test_finance_service.py`

- [ ] **Step 1: Resolve wallet strictly by bot id during manual deposit**

```python
from services.deposit_wallet_resolver import resolve_wallet_by_bot_or_raise

# inside create_manual_deposit(...)
wallet = resolve_wallet_by_bot_or_raise(session, bot_id=int(bot.id or 0))

deposit = Deposit(
    ...,
    to_address=str(wallet.address),
    ...,
)
```

- [ ] **Step 2: Remove legacy wallet fallback logic**

Delete behavior that:
- searches first wallet globally when bot wallet is missing.

- [ ] **Step 3: Run focused tests to verify GREEN**

Run: `uv run pytest tests/services/test_finance_service.py -k "manual_deposit" -q`
Expected: PASS.

- [ ] **Step 4: Commit chunk**

```bash
git add services/finance_service.py tests/services/test_finance_service.py
git commit -m "test+feat: enforce bot wallet source for manual deposits"
```

## Chunk 4: Route, State, and Regression Verification

### Task 7: Verify API and state error propagation via tests

**Files:**
- Modify: `tests/api/test_phase2_http_api_bridge.py` (only if missing case)
- Modify: `tests/test_finance_state_db_bridge.py` (only if missing case)
- Test: same files

- [ ] **Step 1: Add failing route/state tests only where coverage gap exists**

```python
def test_finance_manual_deposit_route_propagates_wallet_error(...):
    ...


def test_finance_state_manual_deposit_surfaces_service_error(...):
    ...
```

- [ ] **Step 2: Run targeted tests to verify RED**

Run: `uv run pytest tests/api/test_phase2_http_api_bridge.py tests/test_finance_state_db_bridge.py -q`
Expected: FAIL before minimal fix if new assertions were added.

- [ ] **Step 3: Apply minimal fixes only if needed**

Keep route/state interfaces unchanged; adjust only error surface expectations.

- [ ] **Step 4: Re-run targeted tests to verify GREEN**

Run: `uv run pytest tests/api/test_phase2_http_api_bridge.py tests/test_finance_state_db_bridge.py -q`
Expected: PASS.

- [ ] **Step 5: Commit chunk (if code changed)**

```bash
git add tests/api/test_phase2_http_api_bridge.py tests/test_finance_state_db_bridge.py
git commit -m "test: cover wallet-missing error propagation"
```

### Task 8: Full verification before completion

**Files:**
- Modify: none
- Test: existing suites

- [ ] **Step 1: Compile critical modules**

Run: `uv run python -m py_compile services/deposit_wallet_resolver.py services/bot_side_service.py services/finance_service.py bot/handlers/menu.py`
Expected: no output, exit code 0.

- [ ] **Step 2: Run core regression set**

Run:
`uv run pytest tests/services/test_deposit_wallet_resolver.py tests/services/test_bot_side_service.py tests/services/test_finance_service.py tests/services/test_deposit_reconcile_runtime.py tests/test_app_startup_bootstrap.py tests/api/test_phase2_http_api_bridge.py tests/test_finance_page.py tests/test_finance_state_db_bridge.py tests/bot/test_runtime_lifespan.py tests/bot/test_menu_catalog_mapping.py -q`
Expected: all PASS.

- [ ] **Step 3: Optional broad safety run**

Run: `uv run pytest -q`
Expected: PASS (or document unrelated pre-existing failures).

- [ ] **Step 4: Final commit**

```bash
git add services/deposit_wallet_resolver.py services/bot_side_service.py services/finance_service.py tests/services/test_deposit_wallet_resolver.py tests/services/test_bot_side_service.py tests/services/test_finance_service.py tests/api/test_phase2_http_api_bridge.py tests/test_finance_state_db_bridge.py
git commit -m "feat: enforce wallet_addresses as only source for future USDT deposits"
```

## Done Definition

- New USDT deposits always use `wallet_addresses(bot_id)`.
- Missing bot wallet blocks deposit creation (bot-side + manual finance).
- No fallback to first wallet, bot field address, or settings default address.
- Multi-bot tests prove address isolation.
- Existing reconcile/runtime behavior remains green.
