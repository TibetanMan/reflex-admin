"""Runtime schema patch helpers for environments without migrations."""

from __future__ import annotations

from sqlmodel import text

from shared.database import get_db_session


def _safe_exec(session, sql: str) -> None:
    try:
        session.exec(text(sql))
        session.commit()
    except Exception:
        session.rollback()


def apply_runtime_schema_patches() -> None:
    session = get_db_session()
    try:
        dialect = session.bind.dialect.name if session.bind is not None else ""
        if dialect == "postgresql":
            _safe_exec(
                session,
                "DO $$ BEGIN "
                "ALTER TYPE balanceaction ADD VALUE IF NOT EXISTS 'campaign_bonus'; "
                "EXCEPTION WHEN duplicate_object THEN NULL; "
                "END $$;",
            )
            _safe_exec(session, "ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT")
            _safe_exec(
                session,
                "ALTER TABLE inventory_libraries "
                "ADD COLUMN IF NOT EXISTS is_bot_enabled BOOLEAN NOT NULL DEFAULT TRUE",
            )
            _safe_exec(
                session,
                "ALTER TABLE order_items "
                "ADD COLUMN IF NOT EXISTS purchase_mode VARCHAR(32)",
            )
            _safe_exec(
                session,
                "ALTER TABLE order_items "
                "ADD COLUMN IF NOT EXISTS purchase_filter_json TEXT",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_inventory_libraries_bot_enabled "
                "ON inventory_libraries (is_bot_enabled)",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_product_items_library_status_bin "
                "ON product_items (inventory_library_id, status, bin_number)",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_product_items_library_status_created "
                "ON product_items (inventory_library_id, status, created_at)",
            )
            _safe_exec(
                session,
                "CREATE TABLE IF NOT EXISTS bot_user_accounts ("
                "id SERIAL PRIMARY KEY,"
                "user_id INTEGER NOT NULL REFERENCES users(id),"
                "bot_id INTEGER NOT NULL REFERENCES bot_instances(id),"
                "balance NUMERIC(18,2) NOT NULL DEFAULT 0.00,"
                "total_deposit NUMERIC(18,2) NOT NULL DEFAULT 0.00,"
                "total_spent NUMERIC(18,2) NOT NULL DEFAULT 0.00,"
                "order_count INTEGER NOT NULL DEFAULT 0,"
                "is_banned BOOLEAN NOT NULL DEFAULT FALSE,"
                "ban_reason TEXT NULL,"
                "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "last_active_at TIMESTAMP NULL,"
                "CONSTRAINT uq_bot_user_accounts_user_bot UNIQUE (user_id, bot_id)"
                ")",
            )
            _safe_exec(
                session,
                "ALTER TABLE bot_user_accounts ADD COLUMN IF NOT EXISTS is_banned BOOLEAN NOT NULL DEFAULT FALSE",
            )
            _safe_exec(
                session,
                "ALTER TABLE bot_user_accounts ADD COLUMN IF NOT EXISTS ban_reason TEXT",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_bot_user_accounts_user_id "
                "ON bot_user_accounts (user_id)",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_bot_user_accounts_bot_id "
                "ON bot_user_accounts (bot_id)",
            )
            _safe_exec(
                session,
                "ALTER TABLE cart_items ADD COLUMN IF NOT EXISTS bot_id INTEGER",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_cart_items_bot_id ON cart_items (bot_id)",
            )
            _safe_exec(
                session,
                "UPDATE cart_items c SET bot_id = u.from_bot_id "
                "FROM users u WHERE c.user_id = u.id AND c.bot_id IS NULL",
            )
            _safe_exec(
                session,
                "UPDATE cart_items SET bot_id = (SELECT id FROM bot_instances ORDER BY id ASC LIMIT 1) "
                "WHERE bot_id IS NULL",
            )
            _safe_exec(
                session,
                "CREATE TABLE IF NOT EXISTS agent_campaign_configs ("
                "id SERIAL PRIMARY KEY,"
                "agent_id INTEGER NOT NULL UNIQUE REFERENCES agents(id),"
                "is_enabled BOOLEAN NOT NULL DEFAULT FALSE,"
                "starts_at TIMESTAMP NULL,"
                "ends_at TIMESTAMP NULL,"
                "first_deposit_bonus_rate NUMERIC(18,4) NOT NULL DEFAULT 0.0000,"
                "first_deposit_bonus_amount NUMERIC(18,2) NOT NULL DEFAULT 0.00,"
                "display_title TEXT NULL,"
                "display_subtitle TEXT NULL,"
                "updated_by INTEGER NULL REFERENCES admin_users(id),"
                "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                ")",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs "
                "ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT FALSE",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs "
                "ADD COLUMN IF NOT EXISTS starts_at TIMESTAMP",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs "
                "ADD COLUMN IF NOT EXISTS ends_at TIMESTAMP",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs "
                "ADD COLUMN IF NOT EXISTS first_deposit_bonus_rate NUMERIC(18,4) NOT NULL DEFAULT 0.0000",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs "
                "ADD COLUMN IF NOT EXISTS first_deposit_bonus_amount NUMERIC(18,2) NOT NULL DEFAULT 0.00",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs "
                "ADD COLUMN IF NOT EXISTS display_title TEXT",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs "
                "ADD COLUMN IF NOT EXISTS display_subtitle TEXT",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs "
                "ADD COLUMN IF NOT EXISTS updated_by INTEGER",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs "
                "ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs "
                "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
            )
            _safe_exec(
                session,
                "CREATE TABLE IF NOT EXISTS campaign_reward_grants ("
                "id SERIAL PRIMARY KEY,"
                "campaign_config_id INTEGER NULL REFERENCES agent_campaign_configs(id),"
                "user_id INTEGER NOT NULL REFERENCES users(id),"
                "bot_id INTEGER NOT NULL REFERENCES bot_instances(id),"
                "grant_type VARCHAR(64) NOT NULL,"
                "reward_amount NUMERIC(18,2) NOT NULL DEFAULT 0.00,"
                "granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "operator_id INTEGER NULL REFERENCES admin_users(id),"
                "remark TEXT NULL,"
                "CONSTRAINT uq_campaign_reward_user_bot_type UNIQUE (user_id, bot_id, grant_type)"
                ")",
            )
            _safe_exec(
                session,
                "ALTER TABLE campaign_reward_grants "
                "ADD COLUMN IF NOT EXISTS campaign_config_id INTEGER",
            )
            _safe_exec(
                session,
                "ALTER TABLE campaign_reward_grants "
                "ADD COLUMN IF NOT EXISTS reward_amount NUMERIC(18,2) NOT NULL DEFAULT 0.00",
            )
            _safe_exec(
                session,
                "ALTER TABLE campaign_reward_grants "
                "ADD COLUMN IF NOT EXISTS granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
            )
            _safe_exec(
                session,
                "ALTER TABLE campaign_reward_grants "
                "ADD COLUMN IF NOT EXISTS operator_id INTEGER",
            )
            _safe_exec(
                session,
                "ALTER TABLE campaign_reward_grants "
                "ADD COLUMN IF NOT EXISTS remark TEXT",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_campaign_reward_grants_campaign_config_id "
                "ON campaign_reward_grants (campaign_config_id)",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_campaign_reward_grants_user_id "
                "ON campaign_reward_grants (user_id)",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_campaign_reward_grants_bot_id "
                "ON campaign_reward_grants (bot_id)",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_campaign_reward_grants_grant_type "
                "ON campaign_reward_grants (grant_type)",
            )
        else:
            # SQLite dev/test fallback.
            _safe_exec(
                session,
                "ALTER TABLE inventory_libraries "
                "ADD COLUMN is_bot_enabled BOOLEAN NOT NULL DEFAULT 1",
            )
            _safe_exec(
                session,
                "CREATE TABLE IF NOT EXISTS bot_user_accounts ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "user_id INTEGER NOT NULL,"
                "bot_id INTEGER NOT NULL,"
                "balance NUMERIC(18,2) NOT NULL DEFAULT 0.00,"
                "total_deposit NUMERIC(18,2) NOT NULL DEFAULT 0.00,"
                "total_spent NUMERIC(18,2) NOT NULL DEFAULT 0.00,"
                "order_count INTEGER NOT NULL DEFAULT 0,"
                "is_banned BOOLEAN NOT NULL DEFAULT 0,"
                "ban_reason TEXT NULL,"
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "last_active_at DATETIME NULL,"
                "UNIQUE(user_id, bot_id)"
                ")",
            )
            _safe_exec(
                session,
                "ALTER TABLE bot_user_accounts ADD COLUMN is_banned BOOLEAN NOT NULL DEFAULT 0",
            )
            _safe_exec(
                session,
                "ALTER TABLE bot_user_accounts ADD COLUMN ban_reason TEXT",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_bot_user_accounts_user_id ON bot_user_accounts (user_id)",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_bot_user_accounts_bot_id ON bot_user_accounts (bot_id)",
            )
            _safe_exec(
                session,
                "ALTER TABLE cart_items ADD COLUMN bot_id INTEGER",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_cart_items_bot_id ON cart_items (bot_id)",
            )
            _safe_exec(
                session,
                "UPDATE cart_items SET bot_id = (SELECT from_bot_id FROM users WHERE users.id = cart_items.user_id) "
                "WHERE bot_id IS NULL",
            )
            _safe_exec(
                session,
                "UPDATE cart_items SET bot_id = (SELECT id FROM bot_instances ORDER BY id ASC LIMIT 1) "
                "WHERE bot_id IS NULL",
            )
            _safe_exec(
                session,
                "CREATE TABLE IF NOT EXISTS agent_campaign_configs ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "agent_id INTEGER NOT NULL,"
                "is_enabled BOOLEAN NOT NULL DEFAULT 0,"
                "starts_at DATETIME NULL,"
                "ends_at DATETIME NULL,"
                "first_deposit_bonus_rate NUMERIC(18,4) NOT NULL DEFAULT 0.0000,"
                "first_deposit_bonus_amount NUMERIC(18,2) NOT NULL DEFAULT 0.00,"
                "display_title TEXT NULL,"
                "display_subtitle TEXT NULL,"
                "updated_by INTEGER NULL,"
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "UNIQUE(agent_id)"
                ")",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs ADD COLUMN is_enabled BOOLEAN NOT NULL DEFAULT 0",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs ADD COLUMN starts_at DATETIME",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs ADD COLUMN ends_at DATETIME",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs "
                "ADD COLUMN first_deposit_bonus_rate NUMERIC(18,4) NOT NULL DEFAULT 0.0000",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs "
                "ADD COLUMN first_deposit_bonus_amount NUMERIC(18,2) NOT NULL DEFAULT 0.00",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs ADD COLUMN display_title TEXT",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs ADD COLUMN display_subtitle TEXT",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs ADD COLUMN updated_by INTEGER",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            )
            _safe_exec(
                session,
                "ALTER TABLE agent_campaign_configs ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            )
            _safe_exec(
                session,
                "CREATE TABLE IF NOT EXISTS campaign_reward_grants ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "campaign_config_id INTEGER NULL,"
                "user_id INTEGER NOT NULL,"
                "bot_id INTEGER NOT NULL,"
                "grant_type TEXT NOT NULL,"
                "reward_amount NUMERIC(18,2) NOT NULL DEFAULT 0.00,"
                "granted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "operator_id INTEGER NULL,"
                "remark TEXT NULL,"
                "UNIQUE(user_id, bot_id, grant_type)"
                ")",
            )
            _safe_exec(
                session,
                "ALTER TABLE campaign_reward_grants ADD COLUMN campaign_config_id INTEGER",
            )
            _safe_exec(
                session,
                "ALTER TABLE campaign_reward_grants ADD COLUMN reward_amount NUMERIC(18,2) NOT NULL DEFAULT 0.00",
            )
            _safe_exec(
                session,
                "ALTER TABLE campaign_reward_grants ADD COLUMN granted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            )
            _safe_exec(
                session,
                "ALTER TABLE campaign_reward_grants ADD COLUMN operator_id INTEGER",
            )
            _safe_exec(
                session,
                "ALTER TABLE campaign_reward_grants ADD COLUMN remark TEXT",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_campaign_reward_grants_campaign_config_id "
                "ON campaign_reward_grants (campaign_config_id)",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_campaign_reward_grants_user_id "
                "ON campaign_reward_grants (user_id)",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_campaign_reward_grants_bot_id "
                "ON campaign_reward_grants (bot_id)",
            )
            _safe_exec(
                session,
                "CREATE INDEX IF NOT EXISTS ix_campaign_reward_grants_grant_type "
                "ON campaign_reward_grants (grant_type)",
            )
    finally:
        session.close()
