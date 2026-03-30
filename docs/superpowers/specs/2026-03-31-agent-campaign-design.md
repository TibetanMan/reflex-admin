# Agent Campaign Design

**Date:** 2026-03-31

**Goal:** Add a single active campaign configuration to the agent management interface so a super admin can configure first-deposit rewards per agent, expose the campaign to end users on the deposit side, and automatically grant rewards when a qualifying deposit completes.

## Confirmed Product Decisions

- Each agent has at most one current campaign configuration.
- Only super admins can configure campaigns.
- Campaign rewards are evaluated per bot, not globally and not per agent.
- A user qualifies if they have not completed a deposit for that bot before.
- Two reward components can stack on the first qualifying deposit:
  - percentage bonus, such as 5%
  - fixed bonus amount, such as 10 USDT
- Reward calculation happens when the deposit completes, not when the deposit record is created.
- Campaigns support both:
  - manual enabled or disabled status
  - optional start and end time window
- The feature must include both:
  - admin-side configuration and status display
  - end-user campaign display in the deposit flow
- Real deposit totals must remain separate from gifted bonus amounts.

## Existing Project Constraints

- Agent management is currently implemented through Reflex state and pages in `test_reflex/state/agent_state.py` and `test_reflex/pages/agents.py`.
- Agent persistence currently lives in `services/agent_service.py` and is exposed through `services/reflex_api.py`.
- Deposit completion currently updates `Deposit`, `BalanceLedger`, `User`, and `BotUserAccount` through:
  - `services/deposit_chain_service.py` for chain-confirmed deposits
  - `services/finance_service.py` for manual deposits
- The project does not currently use Alembic. Schema evolution relies on SQLModel table creation plus `shared/schema_patch.py`.

## Recommended Architecture

Use a dedicated campaign config table plus a dedicated reward grant table, then plug campaign settlement into the existing deposit completion paths.

This keeps the current UI model simple because the business rule is one current campaign per agent, while still preserving enough structure to support validation, auditing, idempotency, and future upgrades. The implementation should avoid embedding campaign state into loose JSON blobs or scattering reward logic across page state.

## Data Model

### `agent_campaign_configs`

Purpose: store the single current campaign configuration for an agent.

Suggested fields:

- `id`
- `agent_id`
- `is_enabled`
- `starts_at`
- `ends_at`
- `first_deposit_bonus_rate`
- `first_deposit_bonus_amount`
- `display_title`
- `display_subtitle`
- `updated_by`
- `created_at`
- `updated_at`

Constraints and behavior:

- `agent_id` must be unique so each agent has at most one config row.
- `first_deposit_bonus_rate` and `first_deposit_bonus_amount` default to zero.
- A config is considered active only when:
  - `is_enabled` is true
  - current time is not before `starts_at` if set
  - current time is not after `ends_at` if set
- Invalid windows such as `ends_at < starts_at` must be rejected at the service layer.

### `campaign_reward_grants`

Purpose: record granted first-deposit campaign rewards and enforce one-time eligibility per user and bot.

Suggested fields:

- `id`
- `agent_id`
- `bot_id`
- `user_id`
- `deposit_id`
- `grant_type`
- `deposit_amount`
- `rate_bonus_amount`
- `fixed_bonus_amount`
- `total_bonus_amount`
- `config_snapshot_json`
- `created_at`

Constraints and behavior:

- `grant_type` can start with a single value such as `first_deposit`.
- Add a uniqueness rule that prevents the same `user_id + bot_id + grant_type` from being granted more than once.
- `config_snapshot_json` stores the exact reward inputs used at settlement time for auditability.
- `deposit_id` should be linked to the qualifying deposit for reconciliation.

### `balance_ledgers`

Extend the existing `BalanceAction` enum with a dedicated campaign bonus action such as `campaign_bonus`.

Reason:

- real deposits and gifted rewards must remain distinguishable
- reward amounts should appear in the user balance history
- bonus amounts must not inflate `total_deposit`

## Settlement Flow

Campaign settlement must run after the normal deposit completion logic identifies a completed deposit.

### Shared settlement entrypoint

Introduce a dedicated service function, for example `apply_agent_campaign_reward_for_deposit(...)`, and call it from both:

- chain deposit completion in `services/deposit_chain_service.py`
- manual deposit completion in `services/finance_service.py`

The shared entrypoint should:

1. Resolve the bot from the completed deposit.
2. Resolve the owning agent from the bot.
3. Load the agent's current campaign config.
4. Check whether the config is active at the deposit completion time.
5. Check whether the user already has a completed-deposit campaign grant for that bot.
6. Calculate:
   - `rate_bonus = deposit_amount * configured_rate`
   - `fixed_bonus = configured_fixed_amount`
   - `total_bonus = rate_bonus + fixed_bonus`
7. If `total_bonus <= 0`, exit without creating a grant.
8. Credit the user's `BotUserAccount.balance` and aggregate `User.balance`.
9. Create:
   - a `campaign_reward_grants` record
   - a `BalanceLedger` record using `campaign_bonus`
10. Commit atomically with idempotency protection.

### Qualification rules

A user qualifies only if this is their first completed deposit for the specific bot. The reward record is the final anti-duplication source of truth.

The system must not reinterpret qualification based on front-end state or display text.

### Statistics rules

For a deposit of `100` with `5%` rate bonus and `10` fixed bonus:

- deposited amount stays `100`
- rewarded amount is `15`
- balance increase is `115`
- `total_deposit` increases by `100`, not `115`

## Admin Experience

The campaign UI should be embedded into the existing agent management page rather than implemented as a separate campaign center.

### Agent list

Extend each agent row with compact campaign visibility:

- campaign status badge
- display of `rate + fixed amount`
- time-window status such as active, disabled, upcoming, or expired

This gives super admins immediate visibility without opening every row.

### Campaign editor

Add a dedicated action in the agent row, such as `活动配置`, that opens a modal or drawer containing a single campaign form for that agent.

Form fields:

- enabled toggle
- campaign title
- campaign subtitle or short description
- start time
- end time
- first-deposit rate bonus
- first-deposit fixed bonus amount

The editor should include a live example preview, such as:

- `首充 100 USDT，到账 115 USDT`

Validation rules:

- rate and fixed amount cannot be negative
- end time cannot be earlier than start time
- a completely zero reward config is allowed only if the admin intentionally wants a display-only placeholder; otherwise prefer warning the admin before save

## End-User Display

The user side should display the current bot's active campaign in the deposit flow.

Initial scope:

- show campaign title
- show campaign subtitle or rule text
- show time window
- show reward summary text, such as `首次充值赠送 5% + 10 USDT`

Display rules:

- show only when the current bot's owning agent has an active campaign
- hide expired, disabled, or not-yet-started campaigns
- do not use front-end display data as the settlement source of truth

The user-facing payload should be derived from a backend formatter that already resolves the current bot and active campaign.

## API and Service Surface

Recommended additions:

- agent campaign snapshot formatter in the agent service layer
- create or update campaign config endpoint under the existing agent route family
- optional read endpoint for end-user deposit views that returns the active campaign for a bot

Example backend shape for admin snapshots:

```json
{
  "agent_id": 3,
  "campaign": {
    "is_enabled": true,
    "status": "active",
    "starts_at": "2026-04-01 00:00",
    "ends_at": "2026-04-30 23:59",
    "first_deposit_bonus_rate": 0.05,
    "first_deposit_bonus_amount": 10.0,
    "display_title": "首充活动",
    "display_subtitle": "首次充值即可获得双重赠送"
  }
}
```

The exact route naming should follow the existing `/api/v1/agents` conventions in `services/reflex_api.py`.

## Migration and Compatibility

Because the project currently depends on `SQLModel.metadata.create_all(...)` plus runtime patching, schema rollout must include:

- model registration in `shared/models/__init__.py`
- new model imports in `shared/database.py`
- patch logic in `shared/schema_patch.py` for PostgreSQL and SQLite
- indexes and uniqueness rules created in a backward-compatible way

This design intentionally avoids requiring a new migration framework as part of the same feature.

## Error Handling and Safety

- Campaign bonus granting must be idempotent.
- Duplicate processing of the same deposit must not create duplicate rewards.
- If a campaign is missing, disabled, expired, or not yet active, the deposit completes normally with no reward.
- If bonus creation hits an already-existing unique grant, the service should treat it as an already-applied reward and exit safely.
- The campaign subsystem must not corrupt normal deposit completion.

Preferred operational rule:

- normal deposit completion remains the primary path
- campaign reward application is an attached, safe, transaction-aware step

## Testing Strategy

### Service tests

Add focused tests for:

- active window evaluation
- disabled campaign rejection
- first completed deposit for a bot grants reward
- second completed deposit for the same bot does not grant reward
- different bot under the same agent can still qualify
- reward amount uses `rate + fixed`
- zero-total reward safely skips grant creation
- duplicate grant attempts remain idempotent

### Deposit flow tests

Cover both:

- chain deposit completion path
- manual deposit completion path

Verify:

- deposit amount updates `total_deposit`
- campaign bonus updates balance only
- reward ledger action is distinct from deposit ledger action

### Front-end state and page tests

Cover:

- agent row campaign summary formatting
- campaign editor load and save
- validation of time windows and numeric inputs
- example preview rendering
- empty-state rendering when no campaign exists

## Out of Scope

- multiple concurrent campaigns per agent
- campaign targeting by registration date or user segments
- rank, ladder, or threshold promotions
- agent self-service campaign editing
- historical campaign browsing UI

## Implementation Direction

The next step after this spec is to write a concrete implementation plan that covers:

- model additions
- schema patch updates
- agent service and API changes
- deposit settlement integration
- admin UI and state updates
- end-user campaign payload and display wiring
- automated tests
