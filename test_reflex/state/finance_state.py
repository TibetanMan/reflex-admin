"""Finance page state."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List

import reflex as rx

from services.finance_api import (
    create_manual_deposit,
    list_finance_deposits,
    list_finance_wallets,
    reconcile_finance_deposits,
)


STATUS_LABEL_TO_CODE = {
    "All Status": "",
    "Completed": "completed",
    "Confirming": "confirming",
}


class FinanceState(rx.State):
    """Finance state for deposits and wallet cards."""

    deposits: List[Dict[str, Any]] = []
    wallets: List[Dict[str, Any]] = []

    search_query: str = ""
    filter_status: str = "All Status"
    filter_method: str = ""

    show_manual_deposit_modal: bool = False
    manual_user_id: str = ""
    manual_amount: str = ""
    manual_remark: str = ""

    def _parse_amount(self, value: str) -> Decimal | None:
        try:
            amount = Decimal(value)
        except (InvalidOperation, ValueError):
            return None
        amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if amount <= 0:
            return None
        return amount

    def load_finance_data(self):
        self.deposits = list_finance_deposits()
        self.wallets = list_finance_wallets()

    def set_search_query(self, value: str):
        self.search_query = value

    def set_filter_status(self, value: str):
        self.filter_status = value

    def set_filter_method(self, value: str):
        self.filter_method = value

    def refresh_list(self):
        return [
            type(self).load_finance_data,
            rx.toast.info("Finance records refreshed", duration=1500),
        ]

    def sync_onchain_deposits(self):
        summary = reconcile_finance_deposits(limit=200)
        self.load_finance_data()
        updated = int(summary.get("updated") or 0)
        completed = int(summary.get("completed") or 0)
        if updated <= 0:
            return rx.toast.info("No on-chain status updates", duration=1800)
        return rx.toast.success(
            f"On-chain sync done: {updated} updated, {completed} completed",
            duration=2200,
        )

    def export_finance_report_csv(self):
        rows = list(self.filtered_deposits)
        if not rows:
            return rx.toast.info("No deposit rows available for export", duration=1800)

        columns = [
            "deposit_no",
            "user",
            "bot",
            "amount",
            "method",
            "status",
            "created_at",
            "tx_hash",
        ]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: str(row.get(column) or "") for column in columns})

        file_name = f"finance_report_{datetime.now():%Y%m%d_%H%M%S}.csv"
        return rx.download(
            data=output.getvalue().encode("utf-8-sig"),
            filename=file_name,
            mime_type="text/csv;charset=utf-8",
        )

    def open_manual_deposit_modal(self):
        self.show_manual_deposit_modal = True
        self.manual_user_id = ""
        self.manual_amount = ""
        self.manual_remark = ""

    def close_manual_deposit_modal(self):
        self.show_manual_deposit_modal = False

    def handle_manual_deposit_modal_change(self, is_open: bool):
        if not is_open:
            self.close_manual_deposit_modal()

    def set_manual_user_id(self, value: str):
        self.manual_user_id = value

    def set_manual_amount(self, value: str):
        self.manual_amount = value

    def set_manual_remark(self, value: str):
        self.manual_remark = value

    def copy_wallet_address(self, address: str):
        value = str(address).strip()
        if not value:
            return rx.toast.error("Address is empty", duration=1500)
        return [
            rx.set_clipboard(value),
            rx.toast.success("Address copied", duration=1500),
        ]

    def copy_deposit_no(self, deposit_no: str):
        value = str(deposit_no).strip()
        if not value:
            return rx.toast.error("Deposit number is empty", duration=1500)
        return [
            rx.set_clipboard(value),
            rx.toast.success("Deposit number copied", duration=1500),
        ]

    def open_tx_hash_link(self, tx_hash: str):
        value = str(tx_hash).strip()
        if not value:
            return rx.toast.error("Transaction hash is empty", duration=1500)
        safe_value = value.replace("'", "").replace('"', "")
        return rx.call_script(
            f"window.open('https://tronscan.org/#/transaction/{safe_value}', '_blank')"
        )

    def process_manual_deposit(self, operator_username: str = ""):
        user_text = self.manual_user_id.strip()
        amount_text = self.manual_amount.strip()
        remark = self.manual_remark.strip() or "manual_deposit"
        operator_username_value = str(operator_username or "").strip() or "admin"
        amount = self._parse_amount(amount_text)

        if not user_text:
            return rx.toast.error("Please input user id", duration=2000)
        if amount is None:
            return rx.toast.error("Amount must be greater than 0 with up to 2 decimals", duration=2500)

        try:
            create_manual_deposit(
                user_identifier=user_text,
                amount=amount,
                remark=remark,
                operator_username=operator_username_value,
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2200)

        self.load_finance_data()
        self.close_manual_deposit_modal()
        return rx.toast.success("Manual deposit created", duration=2200)

    @rx.var
    def status_options(self) -> List[str]:
        return list(STATUS_LABEL_TO_CODE.keys())

    @rx.var
    def filtered_deposits(self) -> List[Dict[str, Any]]:
        items = list(self.deposits)

        query = self.search_query.strip().lower()
        if query:
            items = [
                item
                for item in items
                if query in str(item.get("deposit_no", "")).lower()
                or query in str(item.get("user", "")).lower()
                or query in str(item.get("bot", "")).lower()
            ]

        status_code = STATUS_LABEL_TO_CODE.get(self.filter_status, "")
        if status_code:
            items = [item for item in items if item.get("status") == status_code]

        return sorted(items, key=lambda item: str(item.get("created_at", "")), reverse=True)

    @rx.var
    def total_deposits(self) -> int:
        return len(self.deposits)

    @rx.var
    def completed_deposits(self) -> int:
        return sum(1 for item in self.deposits if item.get("status") == "completed")

    @rx.var
    def pending_deposits(self) -> int:
        return sum(1 for item in self.deposits if item.get("status") == "confirming")

    @rx.var
    def total_deposit_amount(self) -> float:
        return round(
            sum(float(item.get("amount", 0)) for item in self.deposits if item.get("status") == "completed"),
            2,
        )

    @rx.var
    def today_deposits(self) -> float:
        today = datetime.now().strftime("%Y-%m-%d")
        return round(
            sum(
                float(item.get("amount", 0))
                for item in self.deposits
                if item.get("status") == "completed" and str(item.get("created_at", "")).startswith(today)
            ),
            2,
        )

    @rx.var
    def total_balance(self) -> float:
        return round(sum(float(wallet.get("balance", 0)) for wallet in self.wallets), 2)
