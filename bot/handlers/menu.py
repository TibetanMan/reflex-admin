"""Menu handlers for bot-side library purchase flow."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any, Optional

import qrcode
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from bot.runtime_context import ensure_runtime_identity
from services.bot_side_service import (
    create_bot_deposit,
    execute_library_purchase,
    export_bot_global_bins,
    export_bot_library_bins,
    get_bot_balance,
    get_bot_deposit,
    get_bot_library_snapshot,
    list_bot_catalog_categories,
    list_bot_inventory_libraries,
    list_bot_merchants,
    list_bot_merchant_items,
    preview_head_purchase_bins,
    quote_library_purchase,
    search_bot_libraries_by_bin,
)

router = Router(name="menu")


def create_menu_router() -> Router:
    """Factory: create a fresh Router with all menu handlers registered."""
    r = Router(name="menu")
    # Message handlers
    r.message.register(handle_full_info, F.text == BTN_FULL)
    r.message.register(handle_basic_info, F.text == BTN_BASIC)
    r.message.register(handle_special, F.text == BTN_SPECIAL)
    r.message.register(handle_bin_query, F.text == BTN_BIN_QUERY)
    r.message.register(handle_global_bins, F.text == BTN_GLOBAL_BINS)
    r.message.register(handle_merchant, F.text == BTN_MERCHANT)
    r.message.register(handle_deposit, F.text == BTN_DEPOSIT)
    r.message.register(handle_balance, F.text == BTN_BALANCE)
    r.message.register(handle_english, F.text == BTN_ENGLISH)
    r.message.register(handle_head_bins_input, MenuStates.waiting_head_bins)
    r.message.register(handle_quantity_input, MenuStates.waiting_quantity)
    r.message.register(handle_bin_query_input, MenuStates.waiting_bin_query)
    r.message.register(handle_recharge_amount_input, MenuStates.waiting_recharge_amount)
    r.message.register(handle_text_fallback, F.text)
    # Callback query handlers
    r.callback_query.register(handle_category_click, F.data.startswith("CAT:"))
    r.callback_query.register(handle_library_click, F.data.startswith("LIB:"))
    r.callback_query.register(handle_library_action, F.data.startswith("ACT:"))
    r.callback_query.register(handle_prefix_action, F.data.startswith("PF:"))
    r.callback_query.register(handle_search_bin_library_click, F.data.startswith("SBIN:"))
    r.callback_query.register(handle_merchant_items, F.data.startswith("MER:"))
    r.callback_query.register(handle_deposit_open_callback, F.data == "DEP:OPEN")
    r.callback_query.register(handle_deposit_status, F.data.startswith("DEP:STATUS:"))
    return r


BTN_FULL = "🏛 全资库"
BTN_BASIC = "📚 裸资库"
BTN_SPECIAL = "🔥 特价库"
BTN_MERCHANT = "🏪 商家基地"
BTN_BIN_QUERY = "🔍 卡头查询"
BTN_GLOBAL_BINS = "🌐 全球卡头库存"
BTN_DEPOSIT = "💰 余额充值"
BTN_BALANCE = "💵 余额查询"
BTN_ENGLISH = "🌐 English"

MAIN_MENU_BUTTONS = {
    BTN_FULL,
    BTN_BASIC,
    BTN_SPECIAL,
    BTN_MERCHANT,
    BTN_BIN_QUERY,
    BTN_GLOBAL_BINS,
    BTN_DEPOSIT,
    BTN_BALANCE,
    BTN_ENGLISH,
}


class MenuStates(StatesGroup):
    waiting_bin_query = State()
    waiting_recharge_amount = State()
    waiting_head_bins = State()
    waiting_quantity = State()


def get_main_menu() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=BTN_FULL), KeyboardButton(text=BTN_BASIC), KeyboardButton(text=BTN_SPECIAL)],
        [KeyboardButton(text=BTN_MERCHANT), KeyboardButton(text=BTN_BIN_QUERY), KeyboardButton(text=BTN_GLOBAL_BINS)],
        [KeyboardButton(text=BTN_DEPOSIT), KeyboardButton(text=BTN_BALANCE), KeyboardButton(text=BTN_ENGLISH)],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, is_persistent=True)


def _money_text(value: float | Decimal | int | str) -> str:
    return f"{float(value or 0):.2f}"


def _error_text(exc: Exception) -> str:
    detail = str(exc).strip()
    return detail or "操作失败，请稍后重试。"


def _is_menu_text(text: str) -> bool:
    return str(text or "").strip() in MAIN_MENU_BUTTONS


def _parse_bins(text: str) -> list[str]:
    raw = str(text or "").strip()
    if not raw:
        return []
    values = re.findall(r"(?<!\d)\d{6}(?!\d)", raw)
    if not values:
        values = [item.strip() for item in re.split(r"[\s,，]+", raw) if item.strip().isdigit() and len(item.strip()) == 6]
    deduped: list[str] = []
    seen: set[str] = set()
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


async def _ensure_runtime_ids(message: Message, *, tg_user: Any | None = None) -> tuple[int, int]:
    user = tg_user or message.from_user
    if user is None:
        raise ValueError("Missing Telegram user context.")
    me = await message.bot.get_me()
    result = await asyncio.to_thread(
        ensure_runtime_identity,
        bot_token=message.bot.token,
        bot_name=me.full_name,
        bot_username=me.username,
        tg_user=user,
    )
    return int(result["bot_id"]), int(result["user_id"])


def _category_rows_for_menu(rows: list[dict[str, Any]], *, catalog_type: str) -> list[dict[str, Any]]:
    key = str(catalog_type or "").strip().lower()
    filtered: list[dict[str, Any]] = []
    for row in rows:
        code = str(row.get("code") or "").strip().lower()
        name = str(row.get("name") or "").strip()
        if key == "full":
            if code.startswith("inventory_full_") or "\u5168\u8d44\u5e93" in name:
                label = (
                    "\u4e00\u624b"
                    if ("first_hand" in code or "\u4e00\u624b" in name)
                    else ("\u4e8c\u624b" if ("second_hand" in code or "\u4e8c\u624b" in name) else name)
                )
                filtered.append({**row, "menu_label": label})
            continue
        if key == "basic":
            if code == "inventory_raw_capital" or "\u88f8\u8d44\u5e93" in name:
                filtered.append({**row, "menu_label": "\u88f8\u8d44\u5e93"})
            continue
        if key == "special":
            if code == "inventory_special_offer" or "\u7279\u4ef7\u5e93" in name:
                filtered.append({**row, "menu_label": "\u7279\u4ef7\u5e93"})
            continue
    if key == "full":
        order = {"\u4e00\u624b": 0, "\u4e8c\u624b": 1}
        filtered.sort(key=lambda item: order.get(str(item.get("menu_label")), 9))
    return filtered


def _pick_direct_category_row(rows: list[dict[str, Any]], *, catalog_type: str) -> Optional[dict[str, Any]]:
    key = str(catalog_type or "").strip().lower()
    if key not in {"basic", "special"}:
        return None
    filtered = _category_rows_for_menu(rows, catalog_type=key)
    return filtered[0] if filtered else None


def _category_display_count(row: dict[str, Any]) -> int:
    if row.get("library_count") not in (None, ""):
        return int(row.get("library_count") or 0)
    return int(row.get("stock_count") or 0)


def _category_keyboard(rows: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f'{row.get("menu_label", row.get("name", "-"))}\u3010{_category_display_count(row)}\u3011',
                callback_data=f'CAT:{int(row.get("id") or 0)}',
            )
        ]
        for row in rows
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _library_keyboard(rows: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f'{row.get("name", "-")}\u3010{int(row.get("remaining_count") or 0)}\u3011',
                callback_data=f'LIB:{int(row.get("id") or 0)}',
            )
        ]
        for row in rows
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _library_menu_title(*, category_name: str, rows: list[dict[str, Any]], display_total: Optional[int] = None) -> str:
    total = int(display_total) if display_total is not None else sum(int(row.get("remaining_count") or 0) for row in rows)
    return f"{category_name}-\u3010{total}\u3011\n\u8bf7\u9009\u62e9\u5e93\u5b58\u5e93\uff1a"


def _library_action_keyboard(snapshot: dict[str, Any]) -> InlineKeyboardMarkup:
    library_id = int(snapshot.get("library_id") or 0)
    price = _money_text(snapshot.get("pick_price") or 0)
    prefix_counts = dict(snapshot.get("prefix_counts") or {})
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text=f"🎯 挑头购买 {price}U", callback_data=f"ACT:{library_id}:HEAD"),
            InlineKeyboardButton(text=f"🎲 随机购买 {price}U", callback_data=f"ACT:{library_id}:RND"),
        ],
        [InlineKeyboardButton(text="📄 实时卡头库存", callback_data=f"ACT:{library_id}:BINS")],
    ]
    for digit in ("3", "4", "5", "6"):
        c_count = int(prefix_counts.get(f"{digit}C") or 0)
        d_count = int(prefix_counts.get(f"{digit}D") or 0)
        rows.append(
            [
                InlineKeyboardButton(text=f"{digit}头C卡 {price}U 剩余{c_count}", callback_data=f"PF:{library_id}:{digit}:C"),
                InlineKeyboardButton(text=f"{digit}头D卡 {price}U 剩余{d_count}", callback_data=f"PF:{library_id}:{digit}:D"),
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _show_category_menu(message: Message, *, catalog_type: str):
    bot_id, _ = await _ensure_runtime_ids(message)
    all_rows = await asyncio.to_thread(list_bot_catalog_categories, catalog_type="full", bot_id=bot_id)
    rows = _category_rows_for_menu(list(all_rows), catalog_type=catalog_type)
    if not rows:
        await message.answer("暂无可用分类，请稍后再试。", reply_markup=get_main_menu())
        return
    title = "全资库" if catalog_type == "full" else ("裸资库" if catalog_type == "basic" else "特价库")
    await message.answer(
        f"{title}\n\n请选择要查看的分类：",
        reply_markup=_category_keyboard(rows),
    )


async def _show_library_menu(message: Message, *, category_id: int, display_total: Optional[int] = None):
    rows = await asyncio.to_thread(list_bot_inventory_libraries, category_id=category_id)
    if not rows:
        await message.answer("当前分类暂无可售库存。")
        return
    category_name = str(rows[0].get("category_name") or "分类")
    await message.answer(
        _library_menu_title(category_name=category_name, rows=rows, display_total=display_total),
        reply_markup=_library_keyboard(rows),
    )


async def _show_direct_catalog_library_menu(message: Message, *, catalog_type: str):
    bot_id, _ = await _ensure_runtime_ids(message)
    all_rows = await asyncio.to_thread(list_bot_catalog_categories, catalog_type="full", bot_id=bot_id)
    picked = _pick_direct_category_row(list(all_rows), catalog_type=catalog_type)
    if not picked:
        await message.answer("暂无可用分类，请稍后再试。", reply_markup=get_main_menu())
        return
    await _show_library_menu(
        message,
        category_id=int(picked.get("id") or 0),
        display_total=_category_display_count(picked),
    )


async def _show_library_detail(message: Message, *, library_id: int):
    snapshot = await asyncio.to_thread(get_bot_library_snapshot, library_id=library_id)
    text = (
        f"📦 库名称：{snapshot.get('library_name', '-')}\n"
        f"🏷 分类：{snapshot.get('category_name', '-')}\n"
        f"💵 挑头价格：{_money_text(snapshot.get('pick_price') or 0)} USDT\n"
        f"📊 剩余库存：{int(snapshot.get('remaining_count') or 0)}\n"
        f"🔢 当前BIN数：{int(snapshot.get('bin_count') or 0)}"
    )
    await message.answer(text, reply_markup=_library_action_keyboard(snapshot))


async def _show_merchant_menu(message: Message):
    rows = await asyncio.to_thread(list_bot_merchants)
    if not rows:
        await message.answer("暂无可用商家。")
        return
    text_lines = ["🏪 商家基地", ""]
    buttons: list[list[InlineKeyboardButton]] = []
    for row in rows:
        merchant_id = int(row.get("id") or 0)
        text_lines.append(
            f"• {row.get('name', '-')}"
            f" | 可售 {int(row.get('available_products') or 0)}"
            f" | 评分 {float(row.get('rating') or 0):.2f}"
        )
        buttons.append([InlineKeyboardButton(text=f"查看 {row.get('name', '-')}", callback_data=f"MER:{merchant_id}:1")])
    await message.answer("\n".join(text_lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def _build_recharge_qr_image(*, address: str, amount: Decimal) -> BufferedInputFile:
    payload = f"TRC20:{address}?amount={amount:.2f}"
    image = qrcode.make(payload)
    buf = BytesIO()
    image.save(buf, format="PNG")
    return BufferedInputFile(buf.getvalue(), filename="usdt_recharge_qr.png")


def _activation_text() -> str:
    return (
        "⛔️ 用户未激活，无法下单购买！\n"
        "请先完成充值后再继续下单。"
    )


def _recharge_open_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💰 去充值", callback_data="DEP:OPEN")]]
    )


def _format_head_remaining_text(bins: list[str], available_counts: dict[str, Any]) -> str:
    return "\uFF0C".join([str(int(available_counts.get(bin_number) or 0)) for bin_number in bins])


async def _try_shortcut_menu_from_state(message: Message, state: FSMContext) -> bool:
    text = str(message.text or "").strip()
    if text not in MAIN_MENU_BUTTONS:
        return False
    await state.clear()
    await message.answer("已返回主菜单。")
    return True


@router.message(F.text == BTN_FULL)
async def handle_full_info(message: Message, state: FSMContext):
    await state.clear()
    try:
        await _show_category_menu(message, catalog_type="full")
    except Exception as exc:
        await message.answer(f"操作失败：{_error_text(exc)}")


@router.message(F.text == BTN_BASIC)
async def handle_basic_info(message: Message, state: FSMContext):
    await state.clear()
    try:
        await _show_direct_catalog_library_menu(message, catalog_type="basic")
    except Exception as exc:
        await message.answer(f"操作失败：{_error_text(exc)}")


@router.message(F.text == BTN_SPECIAL)
async def handle_special(message: Message, state: FSMContext):
    await state.clear()
    try:
        await _show_direct_catalog_library_menu(message, catalog_type="special")
    except Exception as exc:
        await message.answer(f"操作失败：{_error_text(exc)}")


@router.callback_query(F.data.startswith("CAT:"))
async def handle_category_click(callback: CallbackQuery):
    if not callback.data or not callback.message:
        return
    try:
        category_id = int(callback.data.split(":")[1])
        await _show_library_menu(callback.message, category_id=category_id)
        await callback.answer()
    except Exception as exc:
        await callback.answer(_error_text(exc), show_alert=True)


@router.callback_query(F.data.startswith("LIB:"))
async def handle_library_click(callback: CallbackQuery):
    if not callback.data or not callback.message:
        return
    try:
        library_id = int(callback.data.split(":")[1])
        await _show_library_detail(callback.message, library_id=library_id)
        await callback.answer()
    except Exception as exc:
        await callback.answer(_error_text(exc), show_alert=True)


@router.callback_query(F.data.startswith("ACT:"))
async def handle_library_action(callback: CallbackQuery, state: FSMContext):
    if not callback.data or not callback.message:
        return
    try:
        _, library_text, action = callback.data.split(":")
        library_id = int(library_text)
    except Exception:
        await callback.answer("操作参数无效", show_alert=True)
        return

    try:
        snapshot = await asyncio.to_thread(get_bot_library_snapshot, library_id=library_id)
        library_name = str(snapshot.get("library_name") or "-")
        pick_price = _money_text(snapshot.get("pick_price") or 0)
        if action == "HEAD":
            await state.set_state(MenuStates.waiting_head_bins)
            await state.update_data(
                purchase_mode="head",
                library_id=library_id,
                library_name=library_name,
                pick_price=pick_price,
            )
            await callback.message.answer(
                "你已选择【挑头购买】\n"
                "请输入6位BIN（可输入多个，空格或逗号分隔）："
            )
            await callback.answer()
            return
        if action == "RND":
            await state.set_state(MenuStates.waiting_quantity)
            await state.update_data(
                purchase_mode="random",
                library_id=library_id,
                library_name=library_name,
                pick_price=pick_price,
            )
            await callback.message.answer(
                f"你已选择【{library_name}】\n"
                f"种类【随机购买】\n"
                f"价格：【{pick_price}】\n\n"
                "请输入购买数量："
            )
            await callback.answer()
            return
        if action == "BINS":
            payload = await asyncio.to_thread(export_bot_library_bins, library_id=library_id)
            content = str(payload.get("content") or "")
            filename = f"{str(payload.get('library_name') or 'library')}-实时卡头库存.txt"
            document = BufferedInputFile(content.encode("utf-8"), filename=filename)
            await callback.message.answer_document(document=document, caption=f"📄 {payload.get('library_name', '-')}")
            await callback.answer("已发送库存文件")
            return
        await callback.answer("不支持的操作", show_alert=True)
    except Exception as exc:
        await callback.answer(_error_text(exc), show_alert=True)


@router.callback_query(F.data.startswith("PF:"))
async def handle_prefix_action(callback: CallbackQuery, state: FSMContext):
    if not callback.data or not callback.message:
        return
    try:
        _, library_text, digit, card_kind = callback.data.split(":")
        library_id = int(library_text)
        if digit not in {"3", "4", "5", "6"}:
            raise ValueError("digit")
        if card_kind not in {"C", "D"}:
            raise ValueError("kind")
    except Exception:
        await callback.answer("前缀参数无效", show_alert=True)
        return

    try:
        snapshot = await asyncio.to_thread(get_bot_library_snapshot, library_id=library_id)
        prefix_counts = dict(snapshot.get("prefix_counts") or {})
        left_count = int(prefix_counts.get(f"{digit}{card_kind}") or 0)
        library_name = str(snapshot.get("library_name") or "-")
        pick_price = _money_text(snapshot.get("pick_price") or 0)
        await state.set_state(MenuStates.waiting_quantity)
        await state.update_data(
            purchase_mode="prefix",
            library_id=library_id,
            library_name=library_name,
            prefix_digit=digit,
            card_kind=card_kind,
            pick_price=pick_price,
        )
        await callback.message.answer(
            f"你已选择【{library_name}】\n"
            f"种类【{digit}头{card_kind}卡】\n"
            f"剩余数量【{left_count}】\n"
            f"价格：【{pick_price}】\n\n"
            "请输入购买数量："
        )
        await callback.answer()
    except Exception as exc:
        await callback.answer(_error_text(exc), show_alert=True)


@router.message(MenuStates.waiting_head_bins)
async def handle_head_bins_input(message: Message, state: FSMContext):
    if await _try_shortcut_menu_from_state(message, state):
        return
    text = str(message.text or "").strip()
    if not text:
        await message.answer("请输入BIN。")
        return
    bins = _parse_bins(text)
    if not bins:
        await message.answer("请输入6位BIN，可输入多个。")
        return

    data = await state.get_data()
    library_id = int(data.get("library_id") or 0)
    library_name = str(data.get("library_name") or "-")
    pick_price = str(data.get("pick_price") or "0.00")
    try:
        preview = await asyncio.to_thread(
            preview_head_purchase_bins,
            library_id=library_id,
            bins=bins,
        )
        missing = list(preview.get("missing_bins") or [])
        if missing:
            await message.answer(
                f"未找到 BIN：{', '.join(missing)}\n"
                "我们团队每周都会有大批量更新，敬请关注！"
            )
            return
        counts = dict(preview.get("available_counts") or {})
        remain_text = _format_head_remaining_text(bins, counts)
        await state.set_state(MenuStates.waiting_quantity)
        await state.update_data(
            purchase_mode="head",
            selected_bins=bins,
            library_id=library_id,
            library_name=library_name,
            pick_price=pick_price,
        )
        await message.answer(
            f"你已选择【{library_name}】\n"
            f"已选择卡头：{', '.join(bins)}\n"
            f"剩余数量【{remain_text}】\n"
            f"价格：【{pick_price}】\n\n"
            "请输入购买数量："
        )
    except Exception as exc:
        await message.answer(_error_text(exc))


@router.message(MenuStates.waiting_quantity)
async def handle_quantity_input(message: Message, state: FSMContext):
    if await _try_shortcut_menu_from_state(message, state):
        return
    text = str(message.text or "").strip()
    if not text.isdigit():
        await message.answer("请输入正确的购买数量。")
        return
    quantity = int(text)
    if quantity <= 0:
        await message.answer("购买数量必须大于 0。")
        return

    data = await state.get_data()
    mode = str(data.get("purchase_mode") or "")
    library_id = int(data.get("library_id") or 0)
    bins = list(data.get("selected_bins") or [])
    prefix_digit = str(data.get("prefix_digit") or "")
    card_kind = str(data.get("card_kind") or "")

    try:
        quote = await asyncio.to_thread(
            quote_library_purchase,
            library_id=library_id,
            mode=mode,
            quantity=quantity,
            bins=bins,
            prefix_digit=prefix_digit,
            card_kind=card_kind,
        )
        errors = list(quote.get("errors") or [])
        if errors:
            await message.answer("库存不足：\n" + "\n".join(errors))
            return
        bot_id, user_id = await _ensure_runtime_ids(message)
        balance = await asyncio.to_thread(get_bot_balance, user_id=user_id, bot_id=bot_id)
        current_balance = Decimal(str(balance.get("balance") or 0))
        payable = Decimal(str(quote.get("total_amount") or 0))
        if current_balance < payable:
            await message.answer(_activation_text(), reply_markup=_recharge_open_keyboard())
            return

        purchase = await asyncio.to_thread(
            execute_library_purchase,
            user_id=user_id,
            bot_id=bot_id,
            library_id=library_id,
            mode=mode,
            quantity=quantity,
            bins=bins,
            prefix_digit=prefix_digit,
            card_kind=card_kind,
        )
        await state.clear()
        await message.answer(
            "✅ 购买成功\n\n"
            f"订单号：{purchase.get('order_no', '-')}\n"
            f"库名称：{purchase.get('library_name', '-')}\n"
            f"总条数：{int(purchase.get('total_units') or 0)}\n"
            f"单价：{_money_text(purchase.get('unit_price') or 0)} USDT\n"
            f"总额：{_money_text(purchase.get('total_amount') or 0)} USDT\n"
            f"余额：{_money_text(purchase.get('balance_after') or 0)} USDT"
        )
        raw_items = list(purchase.get("raw_data_items") or [])
        if not raw_items:
            await message.answer("当前订单暂无可展示数据。")
            return
        chunk: list[str] = []
        size = 0
        for line in raw_items:
            value = str(line or "").strip()
            if not value:
                continue
            if size + len(value) + 1 > 3200 and chunk:
                await message.answer("\n".join(chunk))
                chunk = []
                size = 0
            chunk.append(value)
            size += len(value) + 1
        if chunk:
            await message.answer("\n".join(chunk))
    except Exception as exc:
        if "BALANCE_NOT_ENOUGH" in str(exc):
            await message.answer(_activation_text(), reply_markup=_recharge_open_keyboard())
            return
        await message.answer(_error_text(exc))


@router.message(F.text == BTN_BIN_QUERY)
async def handle_bin_query(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(MenuStates.waiting_bin_query)
    await message.answer("请输入要查询的 BIN（6位数字）：")


@router.message(MenuStates.waiting_bin_query)
async def handle_bin_query_input(message: Message, state: FSMContext):
    if await _try_shortcut_menu_from_state(message, state):
        return
    bins = _parse_bins(str(message.text or ""))
    if not bins:
        await message.answer("BIN 格式错误，请输入 6 位数字。")
        return
    query_bin = bins[0]
    try:
        rows = await asyncio.to_thread(search_bot_libraries_by_bin, bin_number=query_bin)
        if not rows:
            await message.answer(
                f"未找到 BIN：{query_bin} 的可售库存\n"
                "我们团队每周都会有大批量更新，敬请关注！"
            )
            return
        await state.clear()
        lines = [f"BIN {query_bin} 共匹配到 {len(rows)} 个库存"]
        buttons: list[list[InlineKeyboardButton]] = []
        for row in rows:
            library_id = int(row.get("library_id") or 0)
            library_name = str(row.get("library_name") or "-")
            bin_count = int(row.get("bin_count") or 0)
            pick_price = _money_text(row.get("pick_price") or 0)
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{library_name}｜{bin_count}条｜{pick_price}U",
                        callback_data=f"SBIN:{library_id}:{query_bin}",
                    )
                ]
            )
        await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception as exc:
        await message.answer(_error_text(exc))


@router.callback_query(F.data.startswith("SBIN:"))
async def handle_search_bin_library_click(callback: CallbackQuery):
    if not callback.data or not callback.message:
        return
    try:
        _, library_text, bin_number = callback.data.split(":")
        library_id = int(library_text)
        await _show_library_detail(callback.message, library_id=library_id)
        await callback.message.answer(f"已打开库存详情（来源 BIN: {bin_number}）。")
        await callback.answer()
    except Exception as exc:
        await callback.answer(_error_text(exc), show_alert=True)


@router.message(F.text == BTN_GLOBAL_BINS)
async def handle_global_bins(message: Message, state: FSMContext):
    await state.clear()
    try:
        payload = await asyncio.to_thread(export_bot_global_bins)
        content = str(payload.get("content") or "")
        local_now = datetime.utcnow() + timedelta(hours=8)
        filename = f"{local_now:%Y-%m-%d}-全局卡头库存.txt"
        document = BufferedInputFile(content.encode("utf-8"), filename=filename)
        await message.answer_document(document=document, caption=f"🌐 全局卡头库存（共 {int(payload.get('line_count') or 0)} 条）")
    except Exception as exc:
        await message.answer(_error_text(exc))


@router.message(F.text == BTN_MERCHANT)
async def handle_merchant(message: Message, state: FSMContext):
    await state.clear()
    try:
        await _show_merchant_menu(message)
    except Exception as exc:
        await message.answer(_error_text(exc))


@router.callback_query(F.data.startswith("MER:"))
async def handle_merchant_items(callback: CallbackQuery):
    if not callback.data or not callback.message:
        return
    try:
        _, merchant_text, page_text = callback.data.split(":")
        merchant_id = int(merchant_text)
        page = max(int(page_text), 1)
    except Exception:
        await callback.answer("商家参数无效", show_alert=True)
        return

    try:
        payload = await asyncio.to_thread(
            list_bot_merchant_items,
            merchant_id=merchant_id,
            page=page,
            page_size=8,
        )
        rows = list(payload.get("items") or [])
        page_value = int(payload.get("page") or 1)
        total_pages = max(int(payload.get("total_pages") or 1), 1)
        merchant_name = str(payload.get("merchant_name") or "-")
        lines = [f"{merchant_name} - 第 {page_value}/{total_pages} 页", ""]
        if not rows:
            lines.append("该商家暂无可售商品。")
        else:
            for index, row in enumerate(rows, start=1):
                lines.append(
                    f"{index}. {row.get('category_name', '-')}"
                    f" | BIN {row.get('bin_number', '-')}"
                    f" | {_money_text(row.get('price') or 0)} USDT"
                )
        nav: list[InlineKeyboardButton] = []
        if page_value > 1:
            nav.append(InlineKeyboardButton(text="⬅️ 上一页", callback_data=f"MER:{merchant_id}:{page_value - 1}"))
        if page_value < total_pages:
            nav.append(InlineKeyboardButton(text="下一页 ➡️", callback_data=f"MER:{merchant_id}:{page_value + 1}"))
        markup = InlineKeyboardMarkup(inline_keyboard=[nav]) if nav else None
        await callback.message.edit_text("\n".join(lines), reply_markup=markup)
        await callback.answer()
    except Exception as exc:
        await callback.answer(_error_text(exc), show_alert=True)


@router.message(F.text == BTN_DEPOSIT)
async def handle_deposit(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(MenuStates.waiting_recharge_amount)
    await message.answer(
        "💰【余额充值】：\n"
        "请输入充值金额（30-10,000 USDT）\n"
        "请检查充值金额\n\n"
        "请输入充值金额："
    )


@router.callback_query(F.data == "DEP:OPEN")
async def handle_deposit_open_callback(callback: CallbackQuery, state: FSMContext):
    if callback.message is None:
        return
    await state.clear()
    await state.set_state(MenuStates.waiting_recharge_amount)
    await callback.message.answer(
        "💰【余额充值】：\n"
        "请输入充值金额（30-10,000 USDT）\n"
        "请检查充值金额\n\n"
        "请输入充值金额："
    )
    await callback.answer()


@router.message(MenuStates.waiting_recharge_amount)
async def handle_recharge_amount_input(message: Message, state: FSMContext):
    if await _try_shortcut_menu_from_state(message, state):
        return
    raw = str(message.text or "").strip()
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        await message.answer("充值金额格式错误，例如 100 或 100.50。")
        return
    if amount < Decimal("30") or amount > Decimal("10000"):
        await message.answer("充值金额必须在 30 到 10000 USDT 之间。")
        return
    if abs(amount.as_tuple().exponent) > 2:
        await message.answer("充值金额最多支持两位小数。")
        return

    try:
        bot_id, user_id = await _ensure_runtime_ids(message)
        payload = await asyncio.to_thread(
            create_bot_deposit,
            user_id=user_id,
            amount=amount,
            bot_id=bot_id,
        )
        await state.clear()
        to_address = str(payload.get("to_address") or "-")
        expires_text = str(payload.get("expires_at") or "")
        if expires_text:
            expires_dt = datetime.strptime(expires_text, "%Y-%m-%d %H:%M:%S")
            expires_local = expires_dt + timedelta(hours=8)
            expires_display = expires_local.strftime("%Y-%m-%d %H:%M:%S")
        else:
            expires_display = "-"
        qr = _build_recharge_qr_image(address=to_address, amount=amount)
        caption = (
            f"【钱包地址(TRC-20)】：\n{to_address}\n\n"
            f"充值金额：{amount:.2f} USDT\n"
            f"订单有效期：{expires_display}（UTC+8）\n\n"
            "【重要提示】：\n"
            "请务必向上方地址转入精确金额，金额需与订单一致（例如 100 USDT 订单就转 100 USDT），"
            "不要多转、少转或向错误地址转账。"
            "那么将充值失败、无法到账！\n\n"
            "到账通常需要 1-3 分钟，最晚不超过 5 分钟，请耐心等待。\n\n"
            "如有疑问，可输入 /help 联系客服!"
        )
        await message.answer_photo(
            photo=qr,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 查询到账状态", callback_data=f"DEP:STATUS:{int(payload.get('id') or 0)}")]
                ]
            ),
        )
    except Exception as exc:
        await message.answer(_error_text(exc))


@router.callback_query(F.data.startswith("DEP:STATUS:"))
async def handle_deposit_status(callback: CallbackQuery):
    if not callback.data or not callback.message:
        return
    try:
        deposit_id = int(callback.data.split(":")[2])
        bot_id, user_id = await _ensure_runtime_ids(callback.message, tg_user=callback.from_user)
        row = await asyncio.to_thread(
            get_bot_deposit,
            deposit_id=deposit_id,
            user_id=user_id,
            bot_id=bot_id,
            sync_onchain=True,
        )
        await callback.message.answer(
            "💳 充值单状态\n\n"
            f"编号：{row.get('deposit_no', '-')}\n"
            f"金额：{_money_text(row.get('amount') or 0)} USDT\n"
            f"状态：{row.get('status', '-')}\n"
            f"地址：{row.get('to_address', '-')}\n"
            f"Tx：{row.get('tx_hash', '-') or '-'}"
        )
        await callback.answer("已刷新")
    except Exception as exc:
        await callback.answer(_error_text(exc), show_alert=True)


@router.message(F.text == BTN_BALANCE)
async def handle_balance(message: Message, state: FSMContext):
    await state.clear()
    try:
        bot_id, user_id = await _ensure_runtime_ids(message)
        balance = await asyncio.to_thread(get_bot_balance, user_id=user_id, bot_id=bot_id)
        user = message.from_user
        username = f"@{user.username}" if user and user.username else (user.first_name if user else "User")
        await message.answer(
            f"👤 用户：{username} | {user.id if user else '-'}\n\n"
            f"💵 当前余额：$ {_money_text(balance.get('balance') or 0)}"
        )
    except Exception as exc:
        await message.answer(_error_text(exc))


@router.message(F.text == BTN_ENGLISH)
async def handle_english(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("English mode is in progress. Please use /help for support.")


@router.message(F.text)
async def handle_text_fallback(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        return
    await message.answer("请选择下方菜单，或输入 /help 查看帮助。")

