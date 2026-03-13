"""/start and /help handlers."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.runtime_context import ensure_runtime_identity
from services.bot_side_api import get_bot_balance

from .menu import get_main_menu

router = Router(name="start")
logger = logging.getLogger(__name__)


def create_start_router() -> Router:
    """Factory: create a fresh Router with all start/help handlers registered."""
    r = Router(name="start")
    r.message.register(cmd_start, CommandStart())
    r.message.register(cmd_help, Command("help"))
    return r


async def _resolve_runtime_ids(message: Message) -> tuple[int, int]:
    user = message.from_user
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


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command."""
    try:
        bot_id, user_id = await _resolve_runtime_ids(message)
        balance = await asyncio.to_thread(get_bot_balance, user_id=user_id, bot_id=bot_id)
        current_balance = float(balance.get("balance") or 0)
    except Exception as exc:
        logger.exception("Failed to initialize runtime identity: %s", exc)
        current_balance = 0.0

    user = message.from_user
    username = f"@{user.username}" if user and user.username else "未设置"
    first_name = user.first_name if user and user.first_name else "用户"
    welcome_text = (
        f"欢迎你，{first_name}\n\n"
        f"用户ID: {user.id if user else '-'}\n"
        f"用户名: {username}\n"
        f"余额: {current_balance:.2f} USDT\n\n"
        "请使用下方菜单浏览商品、查询卡头、充值和下单。"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    help_text = (
        "可用指令\n"
        "/start - 重置会话并显示主菜单\n"
        "/help - 查看帮助\n\n"
        "常用入口\n"
        "1. 全资库 / 裸资库 / 特价库: 按库进行挑头/随机/3-6头购买\n"
        "2. 卡头查询: 全库检索BIN并进入库详情\n"
        "3. 全球卡头库存: 下载全局可售BIN文件\n"
        "4. 充值: 输入金额创建 USDT 充值单\n"
        "5. 余额查询: 查看当前账户余额"
    )
    await message.answer(help_text, reply_markup=get_main_menu())
