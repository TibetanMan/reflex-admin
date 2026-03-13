import inspect
import importlib

import test_reflex.pages.inventory as inventory_page_module
from test_reflex.state.inventory import InventoryState
from test_reflex.state.profile_state import ProfileState

settings_page_module = importlib.import_module("test_reflex.pages.settings")


def test_settings_state_uses_settings_service_calls():
    load_source = inspect.getsource(settings_page_module.SettingsState.load_settings_data.fn)
    save_default_source = inspect.getsource(
        settings_page_module.SettingsState.confirm_default_usdt_address_change.fn
    )
    save_usdt_source = inspect.getsource(settings_page_module.SettingsState.save_usdt_query_api_settings.fn)
    save_bins_source = inspect.getsource(settings_page_module.SettingsState.save_bins_query_api_settings.fn)
    save_tg_source = inspect.getsource(settings_page_module.SettingsState.save_telegram_push_settings.fn)

    assert "get_settings_snapshot(" in load_source
    assert "update_default_usdt_address(" in save_default_source
    assert "update_usdt_query_api_settings(" in save_usdt_source
    assert "update_bins_query_api_settings(" in save_bins_source
    assert "update_telegram_push_settings(" in save_tg_source


def test_profile_state_uses_profile_service_calls():
    load_source = inspect.getsource(ProfileState.load_profile_data.fn)
    save_source = inspect.getsource(ProfileState.save_profile.fn)

    assert "get_profile_snapshot(" in load_source
    assert "update_profile_snapshot(" in save_source


def test_inventory_state_uses_inventory_service_calls():
    load_source = inspect.getsource(InventoryState.load_inventory_data.fn)
    import_source = inspect.getsource(InventoryState.start_import.fn)
    price_source = inspect.getsource(InventoryState.update_price.fn)
    status_source = inspect.getsource(InventoryState.toggle_status.fn)
    delete_source = inspect.getsource(InventoryState.delete_item.fn)

    assert "list_inventory_snapshot(" in load_source
    assert "list_inventory_filter_options(" in load_source
    assert "import_inventory_library(" in import_source
    assert "update_inventory_price(" in price_source
    assert "toggle_inventory_status(" in status_source
    assert "delete_inventory_library(" in delete_source


def test_pages_register_on_mount_loaders_for_settings_profile_inventory():
    profile_module = importlib.import_module("test_reflex.pages.profile")
    settings_source = inspect.getsource(settings_page_module.settings)
    profile_source = inspect.getsource(profile_module.profile)
    inventory_source = inspect.getsource(inventory_page_module.inventory_page)

    assert "load_settings_data" in settings_source
    assert "load_profile_data" in profile_source
    assert "load_inventory_data" in inventory_source


def test_profile_page_binds_logged_in_username_for_loading():
    profile_module = importlib.import_module("test_reflex.pages.profile")
    profile_source = inspect.getsource(profile_module.profile)

    assert "AuthState.username" in profile_source
