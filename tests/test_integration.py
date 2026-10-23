from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
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
async def test_config_entry_setup_and_unload(hass: HomeAssistant):
    await async_setup(hass, {})
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    assert await async_setup_entry(hass, entry)
    assert entry.entry_id in hass.data[DOMAIN]["entries"]
    assert await async_unload_entry(hass, entry)
    assert entry.entry_id not in hass.data[DOMAIN]["entries"]
