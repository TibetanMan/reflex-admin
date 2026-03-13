from __future__ import annotations


def test_render_stock_snapshot_lines():
    from bot.renderers import render_stock_snapshot

    text = render_stock_snapshot(
        [
            {
                "id": 1,
                "name": "全资库 一手",
                "stock_count": 12,
                "base_price": 6.5,
            },
            {
                "id": 2,
                "name": "裸资库",
                "stock_count": 0,
                "base_price": 4.0,
            },
        ]
    )

    assert "库存快照" in text
    assert "全资库 一手" in text
    assert "裸资库" in text
    assert "12" in text
    assert "0" in text
    assert "6.50" in text
    assert "4.00" in text
