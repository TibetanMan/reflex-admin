# 2026-03-13 USDT Multi-Bot Wallet Source Design

## 1. Context

This spec defines a strict, future-facing rule for USDT deposit flows in a multi-bot system.

Confirmed decisions from product owner:
- Address source of truth: `wallet_addresses` only (matched by `bot_id`).
- Missing wallet behavior: strict block (do not create deposit).
- Historical scope: future records only (no backfill migration for legacy deposits).

The goal is to ensure every USDT recharge operation (bot-side and admin-side) resolves addresses from the same authoritative source and cannot cross-map addresses between bots.

## 2. Problem Statement

Current code paths still contain fallback behaviors that can violate bot isolation:
- Fallback to first wallet row when the target bot wallet is missing.
- Fallback to `bot_instances.usdt_address` for deposit target address.

These fallbacks can create wrong `to_address` values under multi-bot deployments and cause potential reconciliation/accounting mismatch.

## 3. Goals

- Enforce `wallet_addresses(bot_id)` as the only address source for new deposits.
- Guarantee that new deposit rows are bot-consistent:
  - `deposits.bot_id` and `deposits.to_address` always belong to the same bot.
- Keep UI and API behavior aligned with backend constraints.
- Preserve existing chain reconciliation and auto-polling behavior while removing cross-bot ambiguity.

## 4. Non-Goals

- No historical full backfill or retroactive data correction.
- No schema redesign for wallet/deposit tables.
- No unrelated refactor of catalog/order flows.

## 5. Source-of-Truth Rule

For any new deposit creation:
1. Resolve active wallet by `bot_id` from `wallet_addresses`.
2. If wallet does not exist, fail fast with business error.
3. Never fallback to:
   - any other wallet row,
   - `bot_instances.usdt_address`,
   - `settings.default_usdt_address`.

## 6. Target Architecture Boundaries

### 6.1 Bot-side recharge flow

Entry: bot menu -> `create_bot_deposit`.

Required behavior:
- Runtime identity resolves current `bot_id`.
- Address resolver fetches wallet for that `bot_id` only.
- Missing wallet => reject request, no deposit row, no QR payload.

### 6.2 Admin manual deposit flow

Entry: finance page -> `create_manual_deposit`.

Required behavior:
- Resolve user and effective bot.
- Resolve wallet by that bot id.
- Missing wallet => reject request and keep balances unchanged.

### 6.3 Chain reconciliation flow

Entry:
- bot-side `get_bot_deposit(..., sync_onchain=True)`
- finance `reconcile_finance_deposits`
- runtime `run_deposit_reconcile_lifespan`

Required behavior:
- Match transfers by deposit fields (`to_address`, `amount`, optional tx hint).
- Persist tx hash for successful matches.
- Credit balance and wallet metrics using deposit bot context.
- Keep existing duplicate tx protections.

## 7. Cross-Layer Change List

### 7.1 Service layer

Primary files:
- `services/bot_side_service.py`
- `services/finance_service.py`
- `services/deposit_chain_service.py` (validation consistency only)

Design change:
- Introduce one shared rule implementation (`resolve_wallet_by_bot_or_raise`) and use it in all deposit creation paths.
- Remove all wallet/address fallback logic for new deposit creation.

### 7.2 API dispatcher and clients

Primary files:
- `services/reflex_api.py`
- `services/bot_side_api.py`
- `services/finance_api.py`

Design change:
- Keep route shapes unchanged.
- Ensure business errors are surfaced cleanly to state/page layers.

### 7.3 Page/State behavior

Primary files:
- `bot/handlers/menu.py`
- `test_reflex/state/finance_state.py`
- `test_reflex/pages/finance.py`

Design change:
- No new UI controls required.
- On missing-wallet failures, display explicit actionable message instead of silent fallback behavior.

### 7.4 ORM/DB

Primary models:
- `shared/models/wallet.py`
- `shared/models/deposit.py`
- `shared/models/bot_instance.py`

Design stance:
- Keep schema as-is.
- Enforce correctness at service boundary for future records.

## 8. Error Handling Contract

Business errors:
- Bot recharge creation: "Current bot has no configured receiving wallet."
- Manual deposit: "Target bot has no configured receiving wallet."

Operational errors:
- Tronscan/network errors should not mutate completed records.
- Reconcile summary should reflect actual updates; no false success.

## 9. Test Strategy

### 9.1 New/updated service tests

- `create_bot_deposit`:
  - succeeds when wallet exists for target bot.
  - fails when target bot wallet missing.
  - proves no fallback to first wallet or bot field address.

- `create_manual_deposit`:
  - same success/fail matrix as above.

- multi-bot isolation:
  - bot A deposit cannot use bot B wallet address.

### 9.2 API bridge tests

- `/api/v1/bot/deposits/create` returns error on missing wallet.
- `/api/v1/finance/manual-deposit` returns error on missing wallet.
- `/api/v1/finance/deposits/reconcile` remains functional.

### 9.3 UI/state bridge tests

- finance state surfaces manual deposit errors.
- bot menu recharge path surfaces strict-block message.

### 9.4 Regression suite

Re-run existing deposit/runtime/finance/api test groups used in previous iteration.

## 10. Acceptance Criteria

- Every newly created USDT deposit has `to_address` from `wallet_addresses` for the same `bot_id`.
- Missing bot wallet blocks creation in both bot-side and admin-side recharge entry points.
- Chain sync still persists successful `tx_hash` and updates ledger/wallet/user balances correctly.
- No cross-bot address mixing in multi-bot test scenarios.

## 11. Rollout Notes

- This is a behavior hardening change for future records only.
- Existing historical deposits remain untouched.
- Operators should ensure each active bot has an assigned wallet before enabling recharge traffic.
