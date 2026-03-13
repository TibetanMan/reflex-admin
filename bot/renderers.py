"""Text rendering helpers for Telegram bot messages/files."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def render_stock_snapshot(categories: list[dict[str, Any]]) -> str:
    """Build a human-readable stock snapshot text payload."""
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = [
        "库存快照",
        f"生成时间: {now_text}",
        "",
    ]
    if not categories:
        lines.append("暂无可用分类。")
        return "\n".join(lines)

    for index, row in enumerate(categories, start=1):
        name = str(row.get("name") or "-")
        stock = int(row.get("stock_count") or 0)
        try:
            base_price = float(row.get("base_price") or 0)
        except (ValueError, TypeError):
            base_price = 0.0
        lines.append(f"{index}. {name} | 库存 {stock} | 参考价 {base_price:.2f} USDT")
    return "\n".join(lines)