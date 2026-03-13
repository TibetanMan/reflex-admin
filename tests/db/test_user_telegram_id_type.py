from __future__ import annotations

from sqlalchemy import BigInteger

from shared.models.user import User


def test_user_telegram_id_uses_bigint():
    column_type = User.__table__.c.telegram_id.type
    assert isinstance(column_type, BigInteger)
