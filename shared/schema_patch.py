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
    finally:
        session.close()
