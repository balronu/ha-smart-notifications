import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from smart_notifications.config_flow import SmartNotificationsOptionsFlow
from smart_notifications.const import DOMAIN


@pytest.mark.asyncio
async def test_options_flow_persists_shared_event_and_route_data(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    flow = SmartNotificationsOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id
    result = await flow.async_step_events(
        {"reason": "washer_finished", "name": "Washer", "message": "Fertig", "enabled": True, "priority": "high"}
    )
    assert result["type"] == "create_entry"
    assert result["data"]["events"]["washer_finished"]["message"] == "Fertig"


@pytest.mark.asyncio
async def test_options_menu_exposes_translated_supported_steps(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    flow = SmartNotificationsOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id
    result = await flow.async_step_init()
    assert result["type"] == "menu"
    assert set(result["menu_options"]) == {
        "settings", "devices", "events", "event_devices", "device_events", "test_device", "test_event"
    }
