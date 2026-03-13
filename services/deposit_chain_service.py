"""USDT (TRC20) chain reconciliation services based on Tronscan."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Callable, Optional

import requests
from sqlmodel import Session, select

from shared.database import get_db_session
from shared.models.balance_ledger import BalanceAction, BalanceLedger
from shared.models.bot_user_account import BotUserAccount
from shared.models.deposit import Deposit, DepositMethod, DepositStatus
from shared.models.system_setting import SystemSetting
from shared.models.user import User
from shared.models.wallet import WalletAddress


USDT_TRC20_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
DEFAULT_TRONSCAN_TRANSFER_API = "https://apilist.tronscanapi.com/api/transfer/trc20"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _money(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _status_text(value: Any) -> str:
    return str(value.value if hasattr(value, "value") else value or "")


def _json_payload(text: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        data = json.loads(text or "{}")
    except json.JSONDecodeError:
        return dict(fallback)
    if not isinstance(data, dict):
        return dict(fallback)
    merged = dict(fallback)
    merged.update(data)
    return merged


def _usdt_query_settings(session: Session) -> dict[str, Any]:
    fallback = {
        "api_url": DEFAULT_TRONSCAN_TRANSFER_API,
        "api_key": "",
        "timeout_seconds": 8,
        "trc20_id": USDT_TRC20_CONTRACT,
    }
    row = session.exec(
        select(SystemSetting).where(SystemSetting.key == "settings.usdt_query_api")
    ).first()
    if row is None:
        return fallback
    payload = _json_payload(str(row.value_json or "{}"), fallback)
    payload["api_url"] = str(payload.get("api_url") or DEFAULT_TRONSCAN_TRANSFER_API).strip()
    payload["api_key"] = str(payload.get("api_key") or "").strip()
    timeout = int(payload.get("timeout_seconds") or 8)
    payload["timeout_seconds"] = max(1, min(timeout, 60))
    payload["trc20_id"] = str(payload.get("trc20_id") or USDT_TRC20_CONTRACT).strip()
    return payload


def _parse_amount(raw_amount: Any, decimals: int) -> Decimal:
    text = str(raw_amount or "").strip()
    if not text:
        return Decimal("0.00")

    try:
        if "." in text:
            value = Decimal(text)
        else:
            value = Decimal(text) / (Decimal(10) ** max(int(decimals), 0))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")
    return _money(value)


def _to_naive_datetime(timestamp_ms: Any) -> Optional[datetime]:
    try:
        value = int(timestamp_ms)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).replace(tzinfo=None)


def _optional_int(value: Any) -> Optional[int]:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def query_usdt_inbound_transfers(
    *,
    session: Session,
    to_address: str,
    start_at: Optional[datetime],
    request_get: Optional[Callable[..., Any]] = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Query inbound USDT TRC20 transfer rows for a target address via Tronscan."""
    address_text = str(to_address or "").strip()
    if not address_text:
        return []

    settings = _usdt_query_settings(session)
    api_url = str(settings.get("api_url") or DEFAULT_TRONSCAN_TRANSFER_API).strip()
    api_key = str(settings.get("api_key") or "").strip()
    timeout = int(settings.get("timeout_seconds") or 8)
    trc20_id = str(settings.get("trc20_id") or USDT_TRC20_CONTRACT).strip() or USDT_TRC20_CONTRACT

    if not api_url:
        return []

    # Include a short lookback window to tolerate clock skew between systems.
    start_timestamp = (
        int((start_at - timedelta(minutes=5)).timestamp() * 1000) if start_at is not None else 0
    )
    fetch = request_get or requests.get
    params = {
        "address": address_text,
        "trc20Id": trc20_id,
        "direction": 2,
        "sort": "-timestamp",
        "start": 0,
        "limit": max(1, min(int(limit), 200)),
        "db_version": 1,
    }
    if start_timestamp > 0:
        params["start_timestamp"] = start_timestamp
    headers = {"accept": "application/json"}
    if api_key:
        headers["TRON-PRO-API-KEY"] = api_key

    try:
        response = fetch(
            api_url,
            params=params,
            headers=headers,
            timeout=max(1, min(timeout, 60)),
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return []

    raw_rows: list[Any] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("token_transfers"), list):
            raw_rows = list(payload.get("token_transfers") or [])
        elif isinstance(payload.get("data"), list):
            raw_rows = list(payload.get("data") or [])

    items: list[dict[str, Any]] = []
    for raw in raw_rows:
        if not isinstance(raw, dict):
            continue
        tx_hash = str(raw.get("hash") or raw.get("transaction_id") or "").strip()
        to_value = str(raw.get("to_address") or raw.get("to") or raw.get("toAddress") or "").strip()
        if not tx_hash or not to_value:
            continue

        decimals = raw.get("decimals")
        if decimals in (None, ""):
            token_info = raw.get("tokenInfo")
            if isinstance(token_info, dict):
                decimals = token_info.get("tokenDecimal")
        try:
            decimals_value = int(decimals or 6)
        except (TypeError, ValueError):
            decimals_value = 6

        amount_value = _parse_amount(raw.get("amount"), decimals_value)
        confirmed_raw = raw.get("confirmed")
        confirmed = bool(
            confirmed_raw is True
            or str(confirmed_raw).strip() == "1"
            or str(confirmed_raw).strip().lower() == "true"
        )
        contract_ret = str(raw.get("contract_ret") or raw.get("finalResult") or "").strip()
        block_number = _optional_int(raw.get("block"))
        timestamp = _to_naive_datetime(raw.get("block_ts") or raw.get("block_timestamp") or raw.get("timestamp"))

        items.append(
            {
                "tx_hash": tx_hash,
                "to_address": to_value,
                "from_address": str(raw.get("from_address") or raw.get("from") or raw.get("fromAddress") or "").strip(),
                "amount": amount_value,
                "confirmed": confirmed,
                "contract_ret": contract_ret,
                "block_number": block_number,
                "timestamp": timestamp,
            }
        )

    items.sort(key=lambda row: row.get("timestamp") or datetime.min)
    return items


def _completed_hashes(session: Session) -> set[str]:
    rows = list(
        session.exec(
            select(Deposit.tx_hash)
            .where(Deposit.status == DepositStatus.COMPLETED)
            .where(Deposit.tx_hash.is_not(None))
        ).all()
    )
    return {
        str(item[0] if isinstance(item, tuple) else item or "").strip()
        for item in rows
        if str(item[0] if isinstance(item, tuple) else item or "").strip()
    }


def _is_success_transfer(transfer: dict[str, Any]) -> bool:
    contract_ret = str(transfer.get("contract_ret") or "").strip().upper()
    return bool(transfer.get("confirmed")) and contract_ret in {"SUCCESS", "SUCCESSFUL", "OK", ""}


def _pick_transfer_for_deposit(
    *,
    deposit: Deposit,
    transfers: list[dict[str, Any]],
    used_hashes: set[str],
) -> Optional[dict[str, Any]]:
    amount_expected = _money(deposit.amount)
    to_address = str(deposit.to_address or "").strip()
    tx_hint = str(deposit.tx_hash or "").strip()
    created_at = deposit.created_at

    for transfer in transfers:
        tx_hash = str(transfer.get("tx_hash") or "").strip()
        if not tx_hash:
            continue
        if tx_hash in used_hashes and tx_hash != tx_hint:
            continue
        if tx_hint and tx_hash != tx_hint:
            continue
        if str(transfer.get("to_address") or "").strip() != to_address:
            continue
        if _money(transfer.get("amount") or 0) != amount_expected:
            continue
        ts = transfer.get("timestamp")
        if created_at and isinstance(ts, datetime) and ts < (created_at - timedelta(minutes=5)):
            continue
        return transfer
    return None


def _apply_confirming_deposit(
    *,
    deposit: Deposit,
    transfer: dict[str, Any],
    now: datetime,
) -> None:
    deposit.status = DepositStatus.CONFIRMING
    deposit.tx_hash = str(transfer.get("tx_hash") or deposit.tx_hash or "").strip() or None
    deposit.from_address = str(transfer.get("from_address") or deposit.from_address or "").strip() or None
    deposit.block_number = _optional_int(transfer.get("block_number"))
    deposit.actual_amount = _money(transfer.get("amount") or 0)
    deposit.updated_at = now


def _ensure_bot_account(
    session: Session,
    *,
    user: User,
    bot_id: int,
) -> BotUserAccount:
    account = session.exec(
        select(BotUserAccount)
        .where(BotUserAccount.user_id == int(user.id or 0))
        .where(BotUserAccount.bot_id == int(bot_id))
    ).first()
    if account is not None:
        return account
    account = BotUserAccount(
        user_id=int(user.id or 0),
        bot_id=int(bot_id),
        balance=_money(0),
        total_deposit=_money(0),
        total_spent=_money(0),
        order_count=0,
        created_at=_now(),
        updated_at=_now(),
        last_active_at=_now(),
    )
    session.add(account)
    session.flush()
    return account


def _apply_completed_deposit(
    session: Session,
    *,
    deposit: Deposit,
    transfer: dict[str, Any],
    now: datetime,
) -> None:
    amount = _money(transfer.get("amount") or 0)
    if amount <= Decimal("0.00"):
        return

    user = session.exec(select(User).where(User.id == int(deposit.user_id))).first()
    if user is None:
        return

    account = _ensure_bot_account(session, user=user, bot_id=int(deposit.bot_id))
    before_balance = _money(account.balance or 0)
    after_balance = _money(before_balance + amount)

    account.balance = after_balance
    account.total_deposit = _money(account.total_deposit or 0) + amount
    account.updated_at = now
    account.last_active_at = now
    session.add(account)

    user.balance = _money(user.balance or 0) + amount
    user.total_deposit = _money(user.total_deposit or 0) + amount
    user.updated_at = now
    session.add(user)

    wallet = session.exec(
        select(WalletAddress).where(WalletAddress.address == str(deposit.to_address or "").strip())
    ).first()
    if wallet is None:
        wallet = session.exec(
            select(WalletAddress).where(WalletAddress.bot_id == int(deposit.bot_id)).order_by(WalletAddress.id.asc())
        ).first()
    if wallet is not None:
        wallet.balance = _money(wallet.balance or 0) + amount
        wallet.total_received = _money(wallet.total_received or 0) + amount
        wallet.updated_at = now
        wallet.last_checked_at = now
        wallet.last_tx_at = transfer.get("timestamp") or now
        session.add(wallet)

    tx_hash = str(transfer.get("tx_hash") or "").strip()
    request_id = f"deposit-chain-{int(deposit.id or 0)}-{tx_hash}"
    existing_ledger = session.exec(
        select(BalanceLedger).where(BalanceLedger.request_id == request_id)
    ).first()
    if existing_ledger is None:
        session.add(
            BalanceLedger(
                user_id=int(user.id or 0),
                bot_id=int(deposit.bot_id),
                action=BalanceAction.CREDIT,
                amount=amount,
                before_balance=before_balance,
                after_balance=after_balance,
                operator_id=None,
                remark="usdt_trc20_onchain",
                request_id=request_id,
            )
        )

    deposit.status = DepositStatus.COMPLETED
    deposit.tx_hash = tx_hash or deposit.tx_hash
    deposit.from_address = str(transfer.get("from_address") or deposit.from_address or "").strip() or None
    deposit.block_number = _optional_int(transfer.get("block_number"))
    deposit.actual_amount = amount
    deposit.confirmations = max(int(deposit.confirmations or 0), 1)
    deposit.updated_at = now
    deposit.completed_at = now
    session.add(deposit)


def sync_deposit_from_chain(
    session: Session,
    *,
    deposit: Deposit,
    request_get: Optional[Callable[..., Any]] = None,
    transfers: Optional[list[dict[str, Any]]] = None,
    used_hashes: Optional[set[str]] = None,
) -> str:
    """Sync a single deposit from chain state and mutate DB entities in current session."""
    if _status_text(deposit.method) != DepositMethod.USDT_TRC20.value:
        return _status_text(deposit.status)
    if _status_text(deposit.status) == DepositStatus.COMPLETED.value:
        return DepositStatus.COMPLETED.value

    now = _now()
    used = used_hashes if used_hashes is not None else _completed_hashes(session)
    current_hash = str(deposit.tx_hash or "").strip()
    if current_hash:
        used.discard(current_hash)

    tx_rows = list(transfers or [])
    if not tx_rows:
        tx_rows = query_usdt_inbound_transfers(
            session=session,
            to_address=str(deposit.to_address or ""),
            start_at=deposit.created_at,
            request_get=request_get,
        )

    matched = _pick_transfer_for_deposit(deposit=deposit, transfers=tx_rows, used_hashes=used)
    if matched is None:
        if (
            _status_text(deposit.status) in {DepositStatus.PENDING.value, DepositStatus.CONFIRMING.value}
            and deposit.expires_at
            and not str(deposit.tx_hash or "").strip()
            and deposit.expires_at <= now
        ):
            deposit.status = DepositStatus.EXPIRED
            deposit.updated_at = now
            session.add(deposit)
            return DepositStatus.EXPIRED.value
        return _status_text(deposit.status)

    tx_hash = str(matched.get("tx_hash") or "").strip()
    if tx_hash and tx_hash in used:
        return _status_text(deposit.status)

    if _is_success_transfer(matched):
        _apply_completed_deposit(session, deposit=deposit, transfer=matched, now=now)
        if tx_hash:
            used.add(tx_hash)
        return DepositStatus.COMPLETED.value

    contract_ret = str(matched.get("contract_ret") or "").strip().upper()
    if contract_ret and contract_ret not in {"SUCCESS", "SUCCESSFUL", "OK"}:
        deposit.status = DepositStatus.FAILED
        deposit.tx_hash = tx_hash or deposit.tx_hash
        deposit.updated_at = now
        session.add(deposit)
        return DepositStatus.FAILED.value

    _apply_confirming_deposit(deposit=deposit, transfer=matched, now=now)
    session.add(deposit)
    return DepositStatus.CONFIRMING.value


def sync_pending_usdt_deposits(
    *,
    limit: int = 100,
    session_factory: Optional[Callable[[], Session]] = None,
    request_get: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Batch-sync pending/confirming USDT deposits from chain data."""
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        rows = list(
            session.exec(
                select(Deposit)
                .where(Deposit.method == DepositMethod.USDT_TRC20)
                .where(Deposit.status.in_([DepositStatus.PENDING, DepositStatus.CONFIRMING, DepositStatus.EXPIRED]))  # type: ignore[arg-type]
                .order_by(Deposit.created_at.asc())
                .limit(max(1, min(int(limit or 100), 1000)))
            ).all()
        )

        if not rows:
            return {
                "total": 0,
                "completed": 0,
                "confirming": 0,
                "expired": 0,
                "failed": 0,
                "updated": 0,
            }

        used_hashes = _completed_hashes(session)
        grouped: dict[str, list[Deposit]] = {}
        for row in rows:
            key = str(row.to_address or "").strip()
            grouped.setdefault(key, []).append(row)

        transfer_cache: dict[str, list[dict[str, Any]]] = {}
        for address, deposits in grouped.items():
            start_at = min((item.created_at for item in deposits if item.created_at), default=None)
            transfer_cache[address] = query_usdt_inbound_transfers(
                session=session,
                to_address=address,
                start_at=start_at,
                request_get=request_get,
            )

        stats = {
            "total": len(rows),
            "completed": 0,
            "confirming": 0,
            "expired": 0,
            "failed": 0,
            "updated": 0,
        }
        for row in rows:
            before = _status_text(row.status)
            after = sync_deposit_from_chain(
                session,
                deposit=row,
                request_get=request_get,
                transfers=transfer_cache.get(str(row.to_address or "").strip(), []),
                used_hashes=used_hashes,
            )
            if after != before:
                stats["updated"] += 1
                if after in stats:
                    stats[after] += 1

        session.commit()
        return stats
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
