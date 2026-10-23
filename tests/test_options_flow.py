from unittest.mock import patch

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
    result = await flow.async_step_events()
    assert result["type"] == "menu"
    assert set(result["menu_options"]) == {"events_form", "back"}
    result = await flow.async_step_events_form(
        {"reason": "washer_finished", "name": "Washer", "message": "Fertig", "enabled": True, "priority": "high"}
    )
    assert result["type"] == "menu"
    assert entry.options["events"]["washer_finished"]["message"] == "Fertig"


@pytest.mark.asyncio
async def test_options_flow_back_returns_to_main_without_closing(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    flow = SmartNotificationsOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id

    result = await flow.async_step_devices()
    assert set(result["menu_options"]) == {
        "devices_add_form", "devices_edit_form", "devices_remove_form", "back"
    }
    result = await flow.async_step_back()
    assert result["type"] == "menu"
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_empty_device_actions_abort_with_guidance(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    flow = SmartNotificationsOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id

    result = await flow.async_step_test_device()
    assert result["type"] == "menu"
    result = await flow.async_step_test_device_form()
    assert result["type"] == "abort"
    assert result["reason"] == "no_devices"


@pytest.mark.asyncio
async def test_event_test_returns_translated_error_for_missing_route(hass: HomeAssistant):
    from smart_notifications import async_setup

    await async_setup(hass, {})
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    flow = SmartNotificationsOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id

    result = await flow.async_step_test_event_form(
        {"reason": "water_running", "confirm": True}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "test_event_form"
    assert result["errors"] == {"base": "no_event_devices"}


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


def _discovered_devices():
    return [
        {
            "entity_id": "media_player.hub",
            "display_name": "Esszimmer Hub – Google Cast – Sprachausgabe",
            "physical_key": "device:hub",
            "integration": "cast",
            "output_type": "tts",
        },
        {
            "entity_id": "media_player.hub_music",
            "display_name": "Esszimmer Hub – Music Assistant – Sprachausgabe",
            "physical_key": "device:hub",
            "integration": "music_assistant",
            "output_type": "tts",
        },
    ]


@pytest.mark.asyncio
async def test_device_can_be_added_and_duplicate_entity_is_rejected(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    flow = SmartNotificationsOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id

    with patch("smart_notifications.config_flow.discovered_devices", return_value=_discovered_devices()):
        result = await flow.async_step_devices_add_form()
        assert result["step_id"] == "devices_add_form"
        result = await flow.async_step_devices_add_form({
            "entity_id": "media_player.hub",
            "alias": "Esszimmer",
            "physical_group": "Esszimmer Hub",
        })
        assert result["type"] == "menu"
        profile = entry.options["devices"]["media_player_hub"]
        assert profile["alias"] == "Esszimmer"
        assert profile["physical_key"] == "manual:esszimmer hub"

        result = await flow.async_step_devices_add_form({"entity_id": "media_player.hub"})
        assert result["errors"] == {"base": "duplicate_entity"}


@pytest.mark.asyncio
async def test_device_can_be_edited_and_disabled(hass: HomeAssistant):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "devices": {
                "media_player_hub": {
                    **_discovered_devices()[0], "enabled": True, "alias": "Alt"
                }
            },
            "events": {},
            "routes": {"washer_finished": ["media_player_hub"]},
        },
    )
    entry.add_to_hass(hass)
    flow = SmartNotificationsOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id

    with patch("smart_notifications.config_flow.discovered_devices", return_value=_discovered_devices()):
        result = await flow.async_step_devices_edit_form({
            "device_id": "media_player_hub",
            "entity_id": "media_player.hub_music",
            "alias": "Esszimmer MA",
            "physical_group": "Esszimmer Hub",
            "enabled": False,
        })
    profile = entry.options["devices"]["media_player_hub"]
    assert result["type"] == "menu"
    assert profile["entity_id"] == "media_player.hub_music"
    assert profile["alias"] == "Esszimmer MA"
    assert profile["enabled"] is False


@pytest.mark.asyncio
async def test_device_removal_requires_confirmation_and_cleans_routes(hass: HomeAssistant):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "devices": {"media_player_hub": {"entity_id": "media_player.hub", "display_name": "Hub"}},
            "events": {},
            "routes": {"washer_finished": ["media_player_hub", "other"]},
        },
    )
    entry.add_to_hass(hass)
    flow = SmartNotificationsOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id

    result = await flow.async_step_devices_remove_form({"device_id": "media_player_hub", "confirm": False})
    assert "media_player_hub" in entry.options["devices"]
    assert result["type"] == "menu"
    await flow.async_step_devices_remove_form({"device_id": "media_player_hub", "confirm": True})
    assert "media_player_hub" not in entry.options["devices"]
    assert entry.options["routes"]["washer_finished"] == ["other"]
