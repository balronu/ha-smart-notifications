from unittest.mock import AsyncMock

import pytest
import smart_notifications
from homeassistant import loader
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.translation import async_get_translations
from pytest_homeassistant_custom_component.common import MockConfigEntry
from smart_notifications import async_setup, async_setup_entry, async_unload_entry
from smart_notifications.config_flow import SmartNotificationsConfigFlow
from smart_notifications.const import DOMAIN


@pytest.mark.asyncio
async def test_config_flow_creates_one_entry(hass: HomeAssistant):
    flow = SmartNotificationsConfigFlow()
    flow.hass = hass
    flow.context = {"source": SOURCE_USER}
    result = await flow.async_step_user()
    assert result["type"] == "form"
    result = await flow.async_step_user(user_input={"title": "Test"})
    assert result["type"] == "create_entry"
    assert result["title"] == "Smart Notifications"


@pytest.mark.asyncio
async def test_action_uses_shared_message_and_suppresses_physical_duplicate(hass: HomeAssistant):
    tts_call = AsyncMock()
    notify_call = AsyncMock()
    hass.services.async_register("tts", "speak", tts_call)
    hass.services.async_register("notify", "send_message", notify_call)
    hass.states.async_set("tts.piper", "idle")
    hass.states.async_set("media_player.hub", "idle")
    hass.states.async_set("notify.hub", "idle")
    await async_setup(hass, {})
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "tts_entity": "tts.piper",
            "events": {"washer_finished": {"name": "Washer", "message": "Fertig {{ room }}", "enabled": True}},
            "devices": {
                "hub_cast": {"entity_id": "media_player.hub", "channel": "tts", "physical_key": "physical:hub", "enabled": True},
                "hub_notify": {"entity_id": "notify.hub", "channel": "notify", "physical_key": "physical:hub", "enabled": True},
            },
            "routes": {"washer_finished": ["hub_cast", "hub_notify"]},
        },
    )
    entry.add_to_hass(hass)
    await async_setup_entry(hass, entry)
    await hass.services.async_call(DOMAIN, "send", {"reason": "washer_finished", "context": {"room": "Küche"}}, blocking=True)
    assert tts_call.await_count == 1
    assert notify_call.await_count == 0
    assert tts_call.await_args.args[0].data["message"] == "Fertig Küche"


@pytest.mark.asyncio
async def test_explicit_device_test_requires_confirmation_and_supports_push(hass: HomeAssistant):
    notify_call = AsyncMock()
    hass.services.async_register("notify", "send_message", notify_call)
    hass.states.async_set("notify.phone", "idle")
    await async_setup(hass, {})
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={"devices": {"phone": {"entity_id": "notify.phone", "channel": "notify", "enabled": True}}, "events": {}, "routes": {}})
    entry.add_to_hass(hass)
    await async_setup_entry(hass, entry)
    await hass.services.async_call(DOMAIN, "test_device", {"device_id": "phone", "confirm": False}, blocking=True)
    assert notify_call.await_count == 0
    await hass.services.async_call(DOMAIN, "test_device", {"device_id": "phone", "message": "Probe", "confirm": True}, blocking=True)
    assert notify_call.await_count == 1
    assert notify_call.await_args.args[0].data["message"] == "Probe"


@pytest.mark.asyncio
async def test_event_test_uses_current_service_call_contract_and_delivers_tts(hass: HomeAssistant):
    tts_call = AsyncMock()
    hass.services.async_register("tts", "speak", tts_call)
    hass.states.async_set("tts.piper", "idle")
    hass.states.async_set("media_player.hub", "idle")
    await async_setup(hass, {})
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "tts_entity": "tts.piper",
            "events": {"water_running": {"name": "Wasser", "message": "Das Wasser läuft noch.", "enabled": True}},
            "devices": {"hub": {"entity_id": "media_player.hub", "channel": "tts", "enabled": True}},
            "routes": {"water_running": ["hub"]},
        },
    )
    entry.add_to_hass(hass)
    await async_setup_entry(hass, entry)

    await hass.services.async_call(
        DOMAIN,
        "test_event",
        {"reason": "water_running", "confirm": True},
        blocking=True,
    )

    assert tts_call.await_count == 1


@pytest.mark.asyncio
async def test_event_test_reports_missing_output_devices(hass: HomeAssistant):
    await async_setup(hass, {})
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "events": {"water_running": {"name": "Wasser", "message": "Das Wasser läuft noch.", "enabled": True}},
            "devices": {},
            "routes": {},
        },
    )
    entry.add_to_hass(hass)
    await async_setup_entry(hass, entry)

    with pytest.raises(ServiceValidationError, match="no_event_devices"):
        await hass.services.async_call(
            DOMAIN,
            "test_event",
            {"reason": "water_running", "confirm": True},
            blocking=True,
        )


@pytest.mark.asyncio
async def test_config_entry_setup_and_unload(hass: HomeAssistant):
    await async_setup(hass, {})
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    assert await async_setup_entry(hass, entry)
    assert entry.entry_id in hass.data[DOMAIN]["entries"]
    assert await async_unload_entry(hass, entry)
    assert entry.entry_id not in hass.data[DOMAIN]["entries"]


@pytest.mark.asyncio
async def test_actual_config_entry_loader_does_not_treat_service_schema_as_yaml_config(
    hass: HomeAssistant, enable_custom_integrations
):
    assert not hasattr(smart_notifications, "CONFIG_SCHEMA")
    hass.data[loader.DATA_CUSTOM_COMPONENTS] = loader._get_custom_components(hass)
    hass.data[loader.DATA_CUSTOM_COMPONENTS] = loader._get_custom_components(hass)
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state.value == "loaded"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_actual_config_and_options_flows_accept_piper_and_show_menu(
    hass: HomeAssistant, enable_custom_integrations
):
    hass.states.async_set("tts.piper", "2026-10-23T00:00:00+00:00", {"friendly_name": "Piper"})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == "form"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"tts_entity": "tts.piper", "title": "Test", "dedup_seconds": 30}
    )
    assert result["type"] == "create_entry"
    entry_id = result["result"].entry_id
    options = await hass.config_entries.options.async_init(entry_id)
    assert options["type"] == "menu"
    assert set(options["menu_options"]) == {
        "settings", "devices", "events", "discover_notifications", "event_devices", "device_events", "test_device", "test_event"
    }
    settings = await hass.config_entries.options.async_configure(
        options["flow_id"], {"next_step_id": "settings"}
    )
    assert settings["type"] == "menu"
    assert settings["step_id"] == "settings"
    assert set(settings["menu_options"]) == {"settings_form", "back"}
    main_menu = await hass.config_entries.options.async_configure(
        options["flow_id"], {"next_step_id": "back"}
    )
    assert main_menu["type"] == "menu"
    assert main_menu["step_id"] == "init"


@pytest.mark.asyncio
async def test_actual_options_device_menu_steps_are_supported(
    hass: HomeAssistant, enable_custom_integrations
):
    hass.states.async_set("tts.piper", "idle", {"friendly_name": "Piper"})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"tts_entity": "tts.piper", "title": "Test", "dedup_seconds": 30}
    )
    entry_id = result["result"].entry_id
    registry = er.async_get(hass)
    entity = registry.async_get_or_create(
        "media_player",
        "test",
        "hub",
        config_entry=hass.config_entries.async_get_entry(entry_id),
        original_name="Esszimmer Hub",
    )
    profile_id = entity.entity_id.replace(".", "_")
    hass.states.async_set(entity.entity_id, "idle", {"friendly_name": "Esszimmer Hub"})
    options = await hass.config_entries.options.async_init(entry_id)
    devices = await hass.config_entries.options.async_configure(
        options["flow_id"], {"next_step_id": "devices"}
    )
    assert devices["type"] == "menu"
    assert set(devices["menu_options"]) == {
        "devices_add_form", "devices_edit_form", "devices_remove_form", "back"
    }
    add = await hass.config_entries.options.async_configure(
        options["flow_id"], {"next_step_id": "devices_add_form"}
    )
    assert add["type"] == "form"
    added = await hass.config_entries.options.async_configure(
        options["flow_id"],
        {"entity_id": entity.entity_id, "alias": "Esszimmer", "physical_group": "Hub"},
    )
    assert added["type"] == "menu"
    edited = await hass.config_entries.options.async_configure(
        options["flow_id"],
        {"next_step_id": "devices_edit_form"},
    )
    assert edited["type"] == "form"
    edited = await hass.config_entries.options.async_configure(
        options["flow_id"],
        {
            "device_id": profile_id,
            "entity_id": entity.entity_id,
            "alias": "Esszimmer bearbeitet",
            "physical_group": "Hub",
            "enabled": False,
        },
    )
    assert edited["type"] == "menu"
    removed = await hass.config_entries.options.async_configure(
        options["flow_id"], {"next_step_id": "devices_remove_form"}
    )
    assert removed["type"] == "form"
    cancelled = await hass.config_entries.options.async_configure(
        options["flow_id"], {"device_id": profile_id, "confirm": False}
    )
    assert cancelled["type"] == "menu"
    assert profile_id in hass.config_entries.async_get_entry(entry_id).options["devices"]
    await hass.config_entries.options.async_configure(
        options["flow_id"], {"next_step_id": "devices_remove_form"}
    )
    finished = await hass.config_entries.options.async_configure(
        options["flow_id"], {"device_id": profile_id, "confirm": True}
    )
    assert finished["type"] == "menu"
    assert profile_id not in hass.config_entries.async_get_entry(entry_id).options["devices"]


@pytest.mark.asyncio
async def test_actual_options_event_crud_preserves_stable_id_and_routes(
    hass: HomeAssistant, enable_custom_integrations
):
    hass.states.async_set("tts.piper", "idle", {"friendly_name": "Piper"})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"tts_entity": "tts.piper", "title": "Test", "dedup_seconds": 30}
    )
    entry_id = result["result"].entry_id
    entry = hass.config_entries.async_get_entry(entry_id)
    hass.config_entries.async_update_entry(entry, options={
        **entry.options,
        "events": {"garden_alarm": {"name": "Alarm", "message": "Alt", "enabled": True}},
        "routes": {"garden_alarm": []},
    })
    options = await hass.config_entries.options.async_init(entry_id)
    events = await hass.config_entries.options.async_configure(
        options["flow_id"], {"next_step_id": "events"}
    )
    assert set(events["menu_options"]) == {
        "events_add_form", "events_edit_form", "events_remove_form", "back"
    }
    add = await hass.config_entries.options.async_configure(
        options["flow_id"], {"next_step_id": "events_add_form"}
    )
    assert add["type"] == "form"
    created = await hass.config_entries.options.async_configure(
        options["flow_id"],
        {
            "reason": "beta7_event",
            "name": "Waschmaschine",
            "message": "Fertig",
            "description": "Test",
            "enabled": True,
            "priority": "normal",
            "dedup_seconds": 10,
        },
    )
    assert created["type"] == "menu"
    edit = await hass.config_entries.options.async_configure(
        options["flow_id"], {"next_step_id": "events_edit_form"}
    )
    assert edit["type"] == "form"
    edited = await hass.config_entries.options.async_configure(
        options["flow_id"],
        {
            "reason": "beta7_event",
            "name": "Waschmaschine neu",
            "message": "Fertig neu",
            "description": "Test",
            "enabled": False,
            "priority": "high",
            "dedup_seconds": 20,
        },
    )
    assert edited["type"] == "menu"
    assert hass.config_entries.async_get_entry(entry_id).options["events"]["beta7_event"]["enabled"] is False
    remove = await hass.config_entries.options.async_configure(
        options["flow_id"], {"next_step_id": "events_remove_form"}
    )
    assert remove["type"] == "form"
    removed = await hass.config_entries.options.async_configure(
        options["flow_id"], {"reason": "beta7_event", "confirm": True}
    )
    assert removed["type"] == "menu"
    assert "beta7_event" not in hass.config_entries.async_get_entry(entry_id).options["events"]


@pytest.mark.asyncio
async def test_real_german_options_translations_include_main_and_back_labels(hass: HomeAssistant):
    translations = await async_get_translations(
        hass, "de", "options", integrations={DOMAIN}
    )
    prefix = f"component.{DOMAIN}.options.step."
    assert translations[f"{prefix}init.menu_options.settings"] == "Grundeinstellungen"
    assert (
        translations[f"{prefix}devices.menu_options.back"]
        == "Zurück zum Hauptmenü"
    )
    assert translations[f"{prefix}devices.menu_options.devices_edit_form"] == "Ausgabegerät bearbeiten"
    assert translations[f"{prefix}devices.menu_options.devices_remove_form"] == "Ausgabegerät entfernen"
    assert translations[f"{prefix}devices_edit_form.data.enabled"] == "Aktiviert"
    assert translations[f"{prefix}init.menu_options.discover_notifications"] == "Benachrichtigungen erkennen"
    assert translations[f"{prefix}test_device_form.data.device_id"] == "Ausgabegerät"
    assert "device_count" not in " ".join(translations.values())
