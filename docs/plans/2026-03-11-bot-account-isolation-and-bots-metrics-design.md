# Bot Account Isolation and Bots Metrics Design

**Date:** 2026-03-11

## Goal

Fix three production issues in bot runtime and admin bots page:
1. same Telegram user mixing balances across different bots;
2. each bot revenue stays 0 in Bots page;
3. total revenue and total users in Bots page do not change.

## Confirmed Decisions

- Use identity/account split model.
- Keep `users` as global Telegram identity.
- Add bot-scoped account table for isolated balance and cumulative stats.
- Bots page user metric uses account count (same Telegram user in two bots counts as 2).
- Data migration strategy for existing `users.balance`:
  - primary target: `users.from_bot_id`;
  - fallback: earliest transaction bot;
  - fallback: default bot.

## Data Model

Add `bot_user_accounts` table:
- `id`
- `user_id` (FK users.id)
- `bot_id` (FK bot_instances.id)
- `balance` numeric(18,2)
- `total_deposit` numeric(18,2)
- `total_spent` numeric(18,2)
- `order_count` int
- `last_active_at` datetime nullable
- `created_at`, `updated_at`
- unique constraint `(user_id, bot_id)`
- indexes on `bot_id`, `user_id`

## Runtime and Service Behavior

- Runtime identity creation keeps global user behavior.
- Add account ensure logic on runtime identity:
  - ensure account for `(user_id, bot_id)` exists.
- Bot-side balance/debit/credit reads and writes account data only.
- Cart operations become bot scoped via `cart_items.bot_id`.
- Bot-side APIs accept bot context and avoid cross-bot fallback.

## Bots Metrics

Bots page snapshot is recalculated from source data:
- `users`: count of `bot_user_accounts` for each bot;
- `orders`: count of orders by bot;
- `revenue`: sum of completed order amount by bot.

This removes dependency on stale denormalized counters.

## Compatibility and Migration

- Keep legacy fields on `users` and `bot_instances` for compatibility.
- Introduce runtime patch helpers for environments without migrations.
- Add idempotent backfill step for account rows and cart `bot_id`.

## Error Handling

- Explicit failures for missing bot account and insufficient account balance.
- Prevent cart/order/deposit cross-bot access.

## Verification

- Add tests for per-bot balance isolation, cart isolation, and bot metrics refresh.
- Add runtime identity test for same Telegram user across two bot tokens.
