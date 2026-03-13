import inspect
import importlib

import test_reflex.pages.agents as agents_page_module
import test_reflex.pages.bots as bots_page_module
import test_reflex.pages.merchants as merchants_page_module
from test_reflex.state.agent_state import AgentState
from test_reflex.state.bot_state import BotState
from test_reflex.state.dashboard import DashboardState
from test_reflex.state.merchant_state import MerchantState


def test_dashboard_state_loads_from_dashboard_service():
    source = inspect.getsource(DashboardState.load_dashboard_data.fn)

    assert "get_dashboard_snapshot(" in source


def test_bot_state_uses_bot_service_calls():
    load_source = inspect.getsource(BotState.load_bots_data.fn)
    create_source = inspect.getsource(BotState.create_bot.fn)
    update_source = inspect.getsource(BotState.update_bot.fn)
    delete_source = inspect.getsource(BotState.delete_bot.fn)
    toggle_source = inspect.getsource(BotState.toggle_bot_status.fn)

    assert "list_bots_snapshot(" in load_source
    assert "list_bot_owner_options(" in load_source
    assert "create_bot_record(" in create_source
    assert "update_bot_record(" in update_source
    assert "delete_bot_record(" in delete_source
    assert "toggle_bot_record_status(" in toggle_source


def test_agent_state_uses_agent_service_calls():
    load_source = inspect.getsource(AgentState.load_agents_data.fn)
    create_source = inspect.getsource(AgentState.save_new_agent.fn)
    update_source = inspect.getsource(AgentState.save_edit_agent.fn)
    toggle_source = inspect.getsource(AgentState.toggle_agent_status.fn)

    assert "list_agents_snapshot(" in load_source
    assert "create_agent_with_bot(" in create_source
    assert "update_agent_record(" in update_source
    assert "toggle_agent_record_status(" in toggle_source


def test_merchant_state_uses_merchant_service_calls():
    load_source = inspect.getsource(MerchantState.load_merchants_data.fn)
    create_source = inspect.getsource(MerchantState.save_new_merchant.fn)
    update_source = inspect.getsource(MerchantState.save_edit_merchant.fn)
    s1 = inspect.getsource(MerchantState.toggle_merchant_status.fn)
    s2 = inspect.getsource(MerchantState.toggle_merchant_featured.fn)
    s3 = inspect.getsource(MerchantState.toggle_merchant_verified.fn)

    assert "list_merchants_snapshot(" in load_source
    assert "create_merchant_record(" in create_source
    assert "update_merchant_record(" in update_source
    assert "toggle_merchant_status(" in s1
    assert "toggle_merchant_featured(" in s2
    assert "toggle_merchant_verified(" in s3


def test_pages_register_on_mount_loaders():
    dashboard_module = importlib.import_module("test_reflex.pages.index")
    dashboard_source = inspect.getsource(dashboard_module.dashboard)
    bots_source = inspect.getsource(bots_page_module.bots_page)
    agents_source = inspect.getsource(agents_page_module.agents_page)
    merchants_source = inspect.getsource(merchants_page_module.merchants_page)

    assert "load_dashboard_data" in dashboard_source
    assert "load_bots_data" in bots_source
    assert "load_agents_data" in agents_source
    assert "load_merchants_data" in merchants_source
