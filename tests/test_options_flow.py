from unittest.mock import patch

import pytest
import voluptuous as vol
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
    assert set(result["menu_options"]) == {"events_add_form", "events_edit_form", "events_remove_form", "back"}
    result = await flow.async_step_events_form(
        {"reason": "washer_finished", "name": "Washer", "message": "Fertig", "enabled": True, "priority": "high"}
    )
    assert result["type"] == "menu"
    assert entry.options["events"]["washer_finished"]["message"] == "Fertig"


@pytest.mark.asyncio
async def test_event_crud_keeps_stable_id_and_cleans_route(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={"routes": {"garden_alarm": ["device"]}})
    entry.add_to_hass(hass)
    flow = SmartNotificationsOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id
    result = await flow.async_step_events_add_form({
        "reason": "garden_alarm", "name": "Gartenalarm", "message": "Alarm", "description": "Test", "enabled": True, "priority": "high", "dedup_seconds": 15
    })
    assert result["type"] == "menu"
    result = await flow.async_step_events_edit_form({
        "reason": "garden_alarm", "name": "Gartenalarm neu", "message": "Alarm neu", "description": "Test", "enabled": False, "priority": "critical", "dedup_seconds": 20
    })
    assert result["type"] == "menu"
    assert entry.options["events"]["garden_alarm"]["name"] == "Gartenalarm neu"
    await flow.async_step_events_remove_form({"reason": "garden_alarm", "confirm": False})
    assert "garden_alarm" in entry.options["events"]
    await flow.async_step_events_remove_form({"reason": "garden_alarm", "confirm": True})
    assert "garden_alarm" not in entry.options["events"]
    assert "garden_alarm" not in entry.options["routes"]


@pytest.mark.asyncio
async def test_event_edit_prefills_saved_values_before_update(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={
        "events": {"saved_event": {"name": "Gespeicherter Name", "message": "Gespeicherter Text", "enabled": False, "priority": "high", "description": "Beschreibung", "dedup_seconds": 45}}
    })
    entry.add_to_hass(hass)
    flow = SmartNotificationsOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id

    select = await flow.async_step_events_edit_form()
    assert select["type"] == "form"
    prefilled = await flow.async_step_events_edit_form({"reason": "saved_event"})
    assert prefilled["type"] == "form"
    defaults = {str(key.schema if hasattr(key, "schema") else key): key.default() if callable(key.default) else key.default for key in prefilled["data_schema"].schema if hasattr(key, "default")}
    assert "Gespeicherter Name" in defaults.values()
    assert "Gespeicherter Text" in defaults.values()
    assert False in defaults.values()
    assert "high" in defaults.values()


@pytest.mark.asyncio
async def test_event_forms_persist_dynamic_message_type_and_parameters(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    flow = SmartNotificationsOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id
    result = await flow.async_step_events_add_form({
        "reason": "bathroom_cold", "name": "Bad kalt",
        "message": "{{ states('sensor.bathroom') }} Grad",
        "message_type": "template", "parameters": {}, "enabled": False,
        "priority": "high", "description": "Dynamisch", "dedup_seconds": 0,
    })
    assert result["type"] == "menu"
    event = entry.options["events"]["bathroom_cold"]
    assert event["message_type"] == "template"
    assert event["parameters"] == {}


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
        "settings", "devices", "events", "discover_notifications", "event_devices", "device_events", "test_device", "test_event"
    }


@pytest.mark.asyncio
async def test_discovery_scan_is_manual_and_returns_to_menu(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    flow = SmartNotificationsOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id
    result = await flow.async_step_discover_notifications()
    assert result["type"] == "menu"
    result = await flow.async_step_discover_scan_form({"confirm": True})
    assert result["type"] == "menu"
    assert entry.options["discovery"]["candidates"] == {}


@pytest.mark.asyncio
async def test_discovery_adoption_is_editable_and_disabled(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={
        "discovery": {"candidates": {
            "candidate-1": {
                "candidate_id": "candidate-1", "source_type": "automation", "source_id": "house",
                "source_name": "Haushaltsmeldung", "suggested_reason": "door_open", "message": "Tür offen",
                "status": "new",
            }
        }}
    })
    entry.add_to_hass(hass)
    flow = SmartNotificationsOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id

    result = await flow.async_step_discover_candidates_form({"candidate_id": "candidate-1", "action": "adopt"})
    assert result["type"] == "menu"
    adopted = entry.options["discovery"]["candidates"]["candidate-1"]
    assert adopted["status"] == "adopted"
    assert entry.options["events"]["door_open"]["enabled"] is False
    assert entry.options["events"]["door_open"]["message"] == "Tür offen"


@pytest.mark.asyncio
async def test_discovery_candidate_labels_use_friendly_names_and_no_raw_status(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={
        "discovery": {"candidates": {
            "candidate-1": {"candidate_id": "candidate-1", "source_type": "automation", "source_id": "house", "source_name": "Haushaltsmeldung", "service": "notify.send_message", "status": "new"}
        }}
    })
    entry.add_to_hass(hass)
    flow = SmartNotificationsOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id
    result = await flow.async_step_discover_candidates_form()
    schema = result["data_schema"].schema
    labels = schema[vol.Required("candidate_id")].config["options"]
    assert labels[0]["label"] == "Haushaltsmeldung – notify.send_message"
    actions = schema[vol.Required("action", default="review")].config["options"]
    assert [item["label"] for item in actions] == ["Prüfen", "Übernehmen", "Ignorieren"]


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
