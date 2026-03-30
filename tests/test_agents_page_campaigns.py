from __future__ import annotations

import inspect

import test_reflex.pages.agents as agents_page_module


def test_agents_page_contains_campaign_management_labels():
    page_source = inspect.getsource(agents_page_module.agents_page)
    modal_source = inspect.getsource(agents_page_module.agent_campaign_modal)
    row_source = inspect.getsource(agents_page_module.render_agent_row)

    assert "agent_campaign_modal()" in page_source
    assert "活动配置" in modal_source
    assert "首充赠送比例" in modal_source
    assert "固定赠送金额" in modal_source
    assert "save_campaign_config(AuthState.username)" in modal_source
    assert 'open_campaign_modal(agent["id"])' in row_source
