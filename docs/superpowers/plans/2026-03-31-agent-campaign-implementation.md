# Agent Campaign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single per-agent campaign configuration that grants first-deposit bonuses per bot, shows the campaign in the user deposit flow, and keeps schema, tests, and delivery flow ready for production rollout.

**Architecture:** Keep campaign configuration as a first-class database-backed domain instead of embedding it into JSON. Use one config row per agent plus one reward-grant row per user and bot for idempotency, then reuse the existing deposit completion paths to attach reward settlement without rewriting normal deposit logic. On the admin side, extend the existing `/agents` stack rather than introducing a separate campaign center.

**Tech Stack:** Python 3.12, Reflex, SQLModel, pytest, Aiogram 3.x, SQLite/PostgreSQL runtime schema patching

---

## Planned File Map

**Persistence and schema**

- Create: `D:\Coding\Test\test-reflex\shared\models\agent_campaign.py`
  Responsibility: SQLModel definitions for `AgentCampaignConfig`, `CampaignRewardGrant`, and any small campaign enums/constants.
- Modify: `D:\Coding\Test\test-reflex\shared\models\__init__.py`
  Responsibility: register the new campaign models for metadata creation and imports.
- Modify: `D:\Coding\Test\test-reflex\shared\database.py`
  Responsibility: ensure the new models are included in `init_db()`.
- Modify: `D:\Coding\Test\test-reflex\shared\schema_patch.py`
  Responsibility: add backward-compatible PostgreSQL and SQLite creation logic, indexes, and uniqueness rules for campaign tables.
- Modify: `D:\Coding\Test\test-reflex\shared\models\balance_ledger.py`
  Responsibility: add the dedicated `campaign_bonus` ledger action.

**Campaign configuration and snapshots**

- Create: `D:\Coding\Test\test-reflex\services\agent_campaign_service.py`
  Responsibility: campaign config CRUD, active-window evaluation, summary formatting, bot-facing display formatting.
- Modify: `D:\Coding\Test\test-reflex\services\agent_service.py`
  Responsibility: include campaign summary data in agent list and detail snapshots used by the admin page.
- Modify: `D:\Coding\Test\test-reflex\services\agent_api.py`
  Responsibility: add admin API wrappers for reading and updating an agent campaign.
- Modify: `D:\Coding\Test\test-reflex\services\reflex_api.py`
  Responsibility: dispatch new `/api/v1/agents/{id}/campaign` routes.
- Modify: `D:\Coding\Test\test-reflex\services\request_security.py`
  Responsibility: restrict campaign update routes to `super_admin`.

**Reward settlement**

- Create: `D:\Coding\Test\test-reflex\services\agent_campaign_reward_service.py`
  Responsibility: one transaction-aware reward settlement entrypoint shared by chain and manual deposit flows.
- Modify: `D:\Coding\Test\test-reflex\services\finance_service.py`
  Responsibility: invoke reward settlement after manual deposit completion.
- Modify: `D:\Coding\Test\test-reflex\services\deposit_chain_service.py`
  Responsibility: invoke reward settlement after chain deposit completion.
- Modify: `D:\Coding\Test\test-reflex\services\user_service.py`
  Responsibility: expose `campaign_bonus` as a readable balance history label where needed.

**Bot-side display**

- Modify: `D:\Coding\Test\test-reflex\services\bot_side_service.py`
  Responsibility: return active campaign display data with the created deposit payload.
- Modify: `D:\Coding\Test\test-reflex\bot\handlers\menu.py`
  Responsibility: show active campaign text in the bot recharge flow before the user pays.

**Admin UI**

- Modify: `D:\Coding\Test\test-reflex\test_reflex\state\agent_state.py`
  Responsibility: load, edit, validate, and save campaign config state for the agent page.
- Modify: `D:\Coding\Test\test-reflex\test_reflex\pages\agents.py`
  Responsibility: render campaign status badges, config action, and campaign edit dialog.

**Tests**

- Create: `D:\Coding\Test\test-reflex\tests\db\test_agent_campaign_models.py`
- Create: `D:\Coding\Test\test-reflex\tests\services\test_agent_campaign_service.py`
- Create: `D:\Coding\Test\test-reflex\tests\services\test_agent_campaign_reward_service.py`
- Create: `D:\Coding\Test\test-reflex\tests\services\test_bot_side_campaign_deposit.py`
- Create: `D:\Coding\Test\test-reflex\tests\state\test_agent_state_campaigns.py`
- Create: `D:\Coding\Test\test-reflex\tests\bot\test_menu_deposit_campaigns.py`
- Modify: `D:\Coding\Test\test-reflex\tests\services\test_finance_service.py`
- Modify: `D:\Coding\Test\test-reflex\tests\api\test_phase2_http_api_bridge.py`

### Task 1: Add Campaign Models and Runtime Schema Compatibility

**Files:**
- Create: `D:\Coding\Test\test-reflex\shared\models\agent_campaign.py`
- Modify: `D:\Coding\Test\test-reflex\shared\models\__init__.py`
- Modify: `D:\Coding\Test\test-reflex\shared\models\balance_ledger.py`
- Modify: `D:\Coding\Test\test-reflex\shared\database.py`
- Modify: `D:\Coding\Test\test-reflex\shared\schema_patch.py`
- Test: `D:\Coding\Test\test-reflex\tests\db\test_agent_campaign_models.py`

- [ ] **Step 1: Write the failing model and enum tests**

```python
from shared.models.agent_campaign import AgentCampaignConfig, CampaignRewardGrant
from shared.models.balance_ledger import BalanceAction


def test_campaign_models_are_registered_in_sqlmodel_metadata():
    assert AgentCampaignConfig.__tablename__ == "agent_campaign_configs"
    assert CampaignRewardGrant.__tablename__ == "campaign_reward_grants"


def test_balance_action_exposes_campaign_bonus():
    assert BalanceAction.CAMPAIGN_BONUS.value == "campaign_bonus"
```

- [ ] **Step 2: Run the focused DB tests to verify they fail**

Run: `uv run pytest tests/db/test_agent_campaign_models.py -v`

Expected: FAIL because the campaign models and `campaign_bonus` ledger action do not exist yet.

- [ ] **Step 3: Add the new SQLModel definitions and metadata registration**

```python
class AgentCampaignConfig(SQLModel, table=True):
    __tablename__ = "agent_campaign_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agents.id", unique=True, index=True)
    is_enabled: bool = Field(default=False)
    starts_at: Optional[datetime] = Field(default=None)
    ends_at: Optional[datetime] = Field(default=None)
    first_deposit_bonus_rate: Decimal = Field(
        sa_column=Column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"))
    )
    first_deposit_bonus_amount: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    )
    display_title: Optional[str] = Field(default=None)
    display_subtitle: Optional[str] = Field(default=None)
    updated_by: Optional[int] = Field(default=None, foreign_key="admin_users.id")
```

```python
class CampaignRewardGrant(SQLModel, table=True):
    __tablename__ = "campaign_reward_grants"
    __table_args__ = (
        UniqueConstraint("user_id", "bot_id", "grant_type", name="uq_campaign_reward_user_bot_type"),
    )
```

```python
class BalanceAction(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    REFUND = "refund"
    MANUAL = "manual"
    CAMPAIGN_BONUS = "campaign_bonus"
```

- [ ] **Step 4: Add backward-compatible schema patch logic for PostgreSQL and SQLite**

```python
_safe_exec(
    session,
    "CREATE TABLE IF NOT EXISTS agent_campaign_configs ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "agent_id INTEGER NOT NULL UNIQUE,"
    "is_enabled BOOLEAN NOT NULL DEFAULT 0,"
    "starts_at DATETIME NULL,"
    "ends_at DATETIME NULL,"
    "first_deposit_bonus_rate NUMERIC(18,4) NOT NULL DEFAULT 0.0000,"
    "first_deposit_bonus_amount NUMERIC(18,2) NOT NULL DEFAULT 0.00,"
    "display_title TEXT NULL,"
    "display_subtitle TEXT NULL,"
    "updated_by INTEGER NULL,"
    "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"
    "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
    ")",
)
```

- [ ] **Step 5: Re-run the focused DB tests**

Run: `uv run pytest tests/db/test_agent_campaign_models.py -v`

Expected: PASS

- [ ] **Step 6: Commit the schema foundation**

```bash
git add shared/models/agent_campaign.py shared/models/__init__.py shared/models/balance_ledger.py shared/database.py shared/schema_patch.py tests/db/test_agent_campaign_models.py
git commit -m "feat: add agent campaign schema foundation"
```

### Task 2: Build Campaign Config Services and Admin API Routes

**Files:**
- Create: `D:\Coding\Test\test-reflex\services\agent_campaign_service.py`
- Modify: `D:\Coding\Test\test-reflex\services\agent_service.py`
- Modify: `D:\Coding\Test\test-reflex\services\agent_api.py`
- Modify: `D:\Coding\Test\test-reflex\services\reflex_api.py`
- Modify: `D:\Coding\Test\test-reflex\services\request_security.py`
- Test: `D:\Coding\Test\test-reflex\tests\services\test_agent_campaign_service.py`
- Test: `D:\Coding\Test\test-reflex\tests\api\test_phase2_http_api_bridge.py`

- [ ] **Step 1: Write the failing campaign service tests**

```python
def test_upsert_agent_campaign_persists_single_config_row(tmp_path):
    row = upsert_agent_campaign_config(
        agent_id=1,
        actor_username="admin",
        is_enabled=True,
        starts_at="2026-04-01 00:00:00",
        ends_at="2026-04-30 23:59:59",
        first_deposit_bonus_rate=Decimal("0.05"),
        first_deposit_bonus_amount=Decimal("10.00"),
        display_title="首充活动",
        display_subtitle="首次充值即可得奖励",
        session_factory=session_factory,
    )
    assert row["status"] == "active"
```

```python
def test_upsert_agent_campaign_rejects_invalid_time_window(tmp_path):
    with pytest.raises(ValueError, match="end"):
        upsert_agent_campaign_config(... starts_at="2026-04-30 00:00:00", ends_at="2026-04-01 00:00:00")
```

```python
def test_get_active_campaign_for_bot_formats_display_payload(tmp_path):
    payload = get_active_campaign_for_bot(bot_id=1, now=datetime(2026, 4, 10, 10, 0, 0), session_factory=session_factory)
    assert payload["summary"] == "首次充值赠送 5% + 10 USDT"
```

- [ ] **Step 2: Run the focused campaign service tests to verify they fail**

Run: `uv run pytest tests/services/test_agent_campaign_service.py -v`

Expected: FAIL because the campaign config service does not exist yet.

- [ ] **Step 3: Implement the campaign service with one-row-per-agent upsert behavior**

```python
def upsert_agent_campaign_config(...):
    row = session.exec(
        select(AgentCampaignConfig).where(AgentCampaignConfig.agent_id == int(agent_id))
    ).first()
    if row is None:
        row = AgentCampaignConfig(agent_id=int(agent_id))
    row.is_enabled = bool(is_enabled)
    row.starts_at = starts_at_value
    row.ends_at = ends_at_value
    row.first_deposit_bonus_rate = rate_value
    row.first_deposit_bonus_amount = fixed_value
    row.display_title = str(display_title or "").strip() or None
    row.display_subtitle = str(display_subtitle or "").strip() or None
```

```python
def campaign_status_text(row: AgentCampaignConfig, *, now: datetime) -> str:
    if not row.is_enabled:
        return "disabled"
    if row.starts_at and now < row.starts_at:
        return "upcoming"
    if row.ends_at and now > row.ends_at:
        return "expired"
    return "active"
```

- [ ] **Step 4: Extend the agent snapshot and HTTP bridge**

```python
# services/agent_service.py
return {
    ...
    "campaign": get_agent_campaign_summary(agent_id=int(agent.id or 0), session=session),
}
```

```python
# services/agent_api.py
def update_agent_campaign_config(*, agent_id: int, actor_username: str, ...):
    return request_json("PATCH", f"/api/v1/agents/{int(agent_id)}/campaign", payload)
```

```python
# services/reflex_api.py
if m == "PATCH" and matched_campaign:
    return upsert_agent_campaign_config_service(agent_id=agent_id, actor_username=str(body.get("actor_username") or ""), ...)
```

```python
# services/request_security.py
RoutePolicy("PATCH", re.compile(r"^/api/v1/agents/\d+/campaign$"), require_auth=True, required_role="super_admin")
```

- [ ] **Step 5: Extend the bridge tests for the new route**

```python
def test_reflex_dispatch_routes_agent_campaign_update(monkeypatch):
    monkeypatch.setattr(module, "upsert_agent_campaign_config_service", lambda **kwargs: {"agent_id": kwargs["agent_id"], "status": "active"})
    row = module.dispatch_request(
        "PATCH",
        "/api/v1/agents/21/campaign",
        {"actor_username": "admin", "is_enabled": True, "first_deposit_bonus_rate": 0.05, "first_deposit_bonus_amount": 10},
    )
    assert row["status"] == "active"
```

- [ ] **Step 6: Re-run the focused service and bridge tests**

Run: `uv run pytest tests/services/test_agent_campaign_service.py tests/api/test_phase2_http_api_bridge.py -k "agent_campaign or agents" -v`

Expected: PASS

- [ ] **Step 7: Commit the campaign config service layer**

```bash
git add services/agent_campaign_service.py services/agent_service.py services/agent_api.py services/reflex_api.py services/request_security.py tests/services/test_agent_campaign_service.py tests/api/test_phase2_http_api_bridge.py
git commit -m "feat: add agent campaign config services"
```

### Task 3: Integrate First-Deposit Reward Settlement into Deposit Completion

**Files:**
- Create: `D:\Coding\Test\test-reflex\services\agent_campaign_reward_service.py`
- Modify: `D:\Coding\Test\test-reflex\services\finance_service.py`
- Modify: `D:\Coding\Test\test-reflex\services\deposit_chain_service.py`
- Modify: `D:\Coding\Test\test-reflex\services\user_service.py`
- Test: `D:\Coding\Test\test-reflex\tests\services\test_agent_campaign_reward_service.py`
- Test: `D:\Coding\Test\test-reflex\tests\services\test_finance_service.py`

- [ ] **Step 1: Write the failing reward service tests**

```python
def test_apply_campaign_reward_for_first_bot_deposit_creates_grant_and_bonus_ledger(tmp_path):
    result = apply_agent_campaign_reward_for_deposit(deposit_id=1, session_factory=session_factory)
    assert result["granted"] is True
    assert result["bonus_amount"] == 15.00
```

```python
def test_apply_campaign_reward_is_idempotent_for_same_user_and_bot(tmp_path):
    first = apply_agent_campaign_reward_for_deposit(deposit_id=1, session_factory=session_factory)
    second = apply_agent_campaign_reward_for_deposit(deposit_id=1, session_factory=session_factory)
    assert first["granted"] is True
    assert second["granted"] is False
```

```python
def test_second_completed_deposit_same_bot_gets_no_bonus(tmp_path):
    assert apply_agent_campaign_reward_for_deposit(deposit_id=2, session_factory=session_factory)["granted"] is False
```

- [ ] **Step 2: Run the focused reward tests to verify they fail**

Run: `uv run pytest tests/services/test_agent_campaign_reward_service.py -v`

Expected: FAIL because the reward settlement service does not exist yet.

- [ ] **Step 3: Implement the shared reward settlement entrypoint**

```python
def apply_agent_campaign_reward_for_deposit(*, deposit_id: int, session_factory: Optional[Callable[[], Session]] = None) -> dict[str, Any]:
    deposit = session.get(Deposit, int(deposit_id))
    if deposit is None or _status_text(deposit.status) != DepositStatus.COMPLETED.value:
        return {"granted": False, "reason": "deposit_not_completed"}

    campaign = get_active_campaign_for_bot(bot_id=int(deposit.bot_id), now=deposit.completed_at or deposit.updated_at or _now(), session=session)
    if not campaign:
        return {"granted": False, "reason": "campaign_inactive"}

    existing = session.exec(
        select(CampaignRewardGrant)
        .where(CampaignRewardGrant.user_id == int(deposit.user_id))
        .where(CampaignRewardGrant.bot_id == int(deposit.bot_id))
        .where(CampaignRewardGrant.grant_type == "first_deposit")
    ).first()
    if existing is not None:
        return {"granted": False, "reason": "already_granted"}
```

- [ ] **Step 4: Hook reward settlement into manual and chain completion**

```python
# services/finance_service.py
session.commit()
session.refresh(deposit)
reward = apply_agent_campaign_reward_for_deposit(deposit_id=int(deposit.id or 0), session_factory=session_factory)
```

```python
# services/deposit_chain_service.py
deposit.status = DepositStatus.COMPLETED
session.add(deposit)
session.flush()
apply_agent_campaign_reward_for_deposit(deposit_id=int(deposit.id or 0), session=session)
```

```python
# services/user_service.py
_ACTION_TO_LABEL = {
    ...
    BalanceAction.CAMPAIGN_BONUS.value: "活动赠送",
}
```

- [ ] **Step 5: Extend manual deposit integration tests**

```python
def test_create_manual_deposit_applies_agent_campaign_bonus(tmp_path):
    payload = create_manual_deposit(...)
    user = session.exec(select(User).where(User.telegram_id == 123456789)).first()
    assert float(user.balance) == 40.50
    assert float(user.total_deposit) == 25.50
```

- [ ] **Step 6: Re-run the focused reward and finance tests**

Run: `uv run pytest tests/services/test_agent_campaign_reward_service.py tests/services/test_finance_service.py -k "campaign or manual_deposit" -v`

Expected: PASS

- [ ] **Step 7: Commit the settlement integration**

```bash
git add services/agent_campaign_reward_service.py services/finance_service.py services/deposit_chain_service.py services/user_service.py tests/services/test_agent_campaign_reward_service.py tests/services/test_finance_service.py
git commit -m "feat: apply agent campaign rewards on deposit completion"
```

### Task 4: Expose Active Campaign in the Bot Deposit Flow

**Files:**
- Modify: `D:\Coding\Test\test-reflex\services\bot_side_service.py`
- Modify: `D:\Coding\Test\test-reflex\bot\handlers\menu.py`
- Test: `D:\Coding\Test\test-reflex\tests\services\test_bot_side_campaign_deposit.py`
- Test: `D:\Coding\Test\test-reflex\tests\bot\test_menu_deposit_campaigns.py`

- [ ] **Step 1: Write the failing bot-side payload tests**

```python
def test_create_bot_deposit_returns_active_campaign_summary(tmp_path):
    row = create_bot_deposit(user_id=1, amount=Decimal("100.00"), bot_id=1, session_factory=session_factory)
    assert row["campaign"]["summary"] == "首次充值赠送 5% + 10 USDT"
```

```python
@pytest.mark.asyncio
async def test_recharge_message_mentions_campaign_bonus(monkeypatch):
    ...
    sent_text = message.answer_photo.await_args.kwargs["caption"]
    assert "首次充值赠送 5% + 10 USDT" in sent_text
```

- [ ] **Step 2: Run the focused bot-side tests to verify they fail**

Run: `uv run pytest tests/services/test_bot_side_campaign_deposit.py tests/bot/test_menu_deposit_campaigns.py -v`

Expected: FAIL because the create-deposit payload does not include campaign display data and the bot message does not render it.

- [ ] **Step 3: Return campaign display data from `create_bot_deposit`**

```python
campaign = get_active_campaign_for_bot(bot_id=int(bot.id or 0), now=_now(), session=session)
return {
    "id": int(deposit.id or 0),
    "deposit_no": str(deposit.deposit_no),
    ...
    "campaign": campaign,
}
```

- [ ] **Step 4: Render the campaign text in the recharge caption**

```python
campaign = payload.get("campaign") or {}
campaign_block = ""
if campaign:
    campaign_block = (
        f"🎁 当前活动：{campaign.get('title') or '首充活动'}\n"
        f"{campaign.get('summary')}\n"
    )
caption = (
    f"{campaign_block}"
    f"【钱包地址(TRC-20)】：\n{to_address}\n\n"
    ...
)
```

- [ ] **Step 5: Re-run the focused bot-side tests**

Run: `uv run pytest tests/services/test_bot_side_campaign_deposit.py tests/bot/test_menu_deposit_campaigns.py -v`

Expected: PASS

- [ ] **Step 6: Commit the user-facing campaign display**

```bash
git add services/bot_side_service.py bot/handlers/menu.py tests/services/test_bot_side_campaign_deposit.py tests/bot/test_menu_deposit_campaigns.py
git commit -m "feat: show active campaign in bot deposit flow"
```

### Task 5: Extend Agent Admin State and Page for Campaign Management

**Files:**
- Modify: `D:\Coding\Test\test-reflex\test_reflex\state\agent_state.py`
- Modify: `D:\Coding\Test\test-reflex\test_reflex\pages\agents.py`
- Modify: `D:\Coding\Test\test-reflex\services\agent_api.py`
- Test: `D:\Coding\Test\test-reflex\tests\state\test_agent_state_campaigns.py`
- Test: `D:\Coding\Test\test-reflex\tests\test_agents_page_campaigns.py`

- [ ] **Step 1: Write the failing state tests**

```python
def test_open_campaign_modal_prefills_existing_agent_campaign(monkeypatch):
    state.open_campaign_modal(7)
    assert state.campaign_agent_id == 7
    assert state.campaign_enabled is True
    assert state.campaign_bonus_rate == "0.0500"
    assert state.campaign_bonus_amount == "10.00"
```

```python
def test_save_campaign_calls_api_with_normalized_payload(monkeypatch):
    captured = {}
    monkeypatch.setattr(agent_state_module, "update_agent_campaign_config", lambda **kwargs: captured.update(kwargs) or {"status": "active"})
    state.save_campaign_config("admin")
    assert captured["actor_username"] == "admin"
```

- [ ] **Step 2: Write the failing page rendering tests**

```python
def test_agents_page_contains_campaign_management_labels():
    source = inspect.getsource(agents_page_module)
    assert "活动配置" in source
    assert "首充赠送比例" in source
    assert "固定赠送金额" in source
```

- [ ] **Step 3: Run the focused agent state and page tests to verify they fail**

Run: `uv run pytest tests/state/test_agent_state_campaigns.py tests/test_agents_page_campaigns.py -v`

Expected: FAIL because the page and state have no campaign fields, actions, or labels.

- [ ] **Step 4: Add dedicated campaign modal state and API wiring**

```python
campaign_agent_id: Optional[int] = None
show_campaign_modal: bool = False
campaign_enabled: bool = False
campaign_title: str = ""
campaign_subtitle: str = ""
campaign_starts_at: str = ""
campaign_ends_at: str = ""
campaign_bonus_rate: str = ""
campaign_bonus_amount: str = ""
```

```python
def save_campaign_config(self, actor_username: str):
    rate = self._parse_campaign_rate(self.campaign_bonus_rate)
    fixed = self._parse_campaign_amount(self.campaign_bonus_amount)
    update_agent_campaign_config(
        agent_id=int(self.campaign_agent_id),
        actor_username=actor_username,
        is_enabled=bool(self.campaign_enabled),
        display_title=self.campaign_title.strip(),
        display_subtitle=self.campaign_subtitle.strip(),
        starts_at=self.campaign_starts_at.strip(),
        ends_at=self.campaign_ends_at.strip(),
        first_deposit_bonus_rate=rate,
        first_deposit_bonus_amount=fixed,
    )
```

- [ ] **Step 5: Render campaign summary and editor UI in the agent page**

```python
rx.table.column_header_cell("活动")
```

```python
rx.tooltip(
    rx.icon_button(
        rx.icon("gift", size=14),
        variant="ghost",
        size="1",
        on_click=lambda: with_focus_blur(AgentState.open_campaign_modal(agent["id"])),
    ),
    content="活动配置",
)
```

```python
rx.text("首充赠送比例", size="2", weight="medium")
rx.text("固定赠送金额", size="2", weight="medium")
rx.text(AgentState.campaign_preview_text, size="2", color=rx.color("gray", 11))
```

- [ ] **Step 6: Re-run the focused agent UI tests**

Run: `uv run pytest tests/state/test_agent_state_campaigns.py tests/test_agents_page_campaigns.py -v`

Expected: PASS

- [ ] **Step 7: Commit the admin UI**

```bash
git add test_reflex/state/agent_state.py test_reflex/pages/agents.py services/agent_api.py tests/state/test_agent_state_campaigns.py tests/test_agents_page_campaigns.py
git commit -m "feat: add agent campaign management ui"
```

### Task 6: Run Regression Checks and Push the Completed Branch

**Files:**
- Modify: `D:\Coding\Test\test-reflex\docs\superpowers\specs\2026-03-31-agent-campaign-design.md` only if implementation revealed a spec mismatch
- Modify: `D:\Coding\Test\test-reflex\docs\superpowers\plans\2026-03-31-agent-campaign-implementation.md` only if the task checklist needs execution notes

- [ ] **Step 1: Run the focused regression suite**

Run:

```bash
uv run pytest tests/db/test_agent_campaign_models.py tests/services/test_agent_campaign_service.py tests/services/test_agent_campaign_reward_service.py tests/services/test_finance_service.py tests/services/test_bot_side_campaign_deposit.py tests/state/test_agent_state_campaigns.py tests/test_agents_page_campaigns.py tests/bot/test_menu_deposit_campaigns.py tests/api/test_phase2_http_api_bridge.py -v
```

Expected: PASS

- [ ] **Step 2: Run a broader safety pass across existing affected suites**

Run:

```bash
uv run pytest tests/services/test_bot_service.py tests/services/test_finance_service.py tests/bot/test_start_handler.py tests/bot/test_runtime_commands.py tests/state/test_inventory_state.py tests/api/test_phase2_http_api_bridge.py -v
```

Expected: PASS, or explicitly capture any unrelated pre-existing failures before proceeding.

- [ ] **Step 3: Manual smoke-check list**

```text
1. Open /agents as super admin and confirm each row shows campaign status summary.
2. Open campaign config for an agent, save 5% + 10 USDT with a valid time window, refresh, and confirm values persist.
3. In the bot recharge flow, create a deposit and confirm the campaign text appears before payment.
4. Complete a first deposit for that bot and confirm:
   - user balance increases by deposit + bonus
   - user total_deposit increases only by the real deposit amount
   - balance history contains a separate campaign bonus entry
5. Complete a second deposit for the same bot and confirm no extra campaign grant is created.
6. Complete a first deposit for a different bot under the same agent and confirm it can still qualify.
```

- [ ] **Step 4: Create the final implementation commit**

```bash
git add shared/models/agent_campaign.py shared/models/__init__.py shared/models/balance_ledger.py shared/database.py shared/schema_patch.py
git add services/agent_campaign_service.py services/agent_campaign_reward_service.py services/agent_service.py services/agent_api.py services/reflex_api.py services/request_security.py services/finance_service.py services/deposit_chain_service.py services/user_service.py services/bot_side_service.py
git add test_reflex/state/agent_state.py test_reflex/pages/agents.py bot/handlers/menu.py
git add tests/db/test_agent_campaign_models.py tests/services/test_agent_campaign_service.py tests/services/test_agent_campaign_reward_service.py tests/services/test_finance_service.py tests/services/test_bot_side_campaign_deposit.py tests/state/test_agent_state_campaigns.py tests/test_agents_page_campaigns.py tests/bot/test_menu_deposit_campaigns.py tests/api/test_phase2_http_api_bridge.py
git commit -m "feat: add per-agent first deposit campaigns"
```

- [ ] **Step 5: Push to GitHub**

Run: `git push origin HEAD`

Expected: the current branch publishes to the configured remote without bundling unrelated local-only files.
