"""Smart Notifications integration."""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.template import Template

from .const import (
    ATTR_CONFIRM,
    ATTR_CONTEXT,
    ATTR_DEVICE_ID,
    ATTR_EVENT_KEY,
    ATTR_MESSAGE,
    ATTR_REASON,
    CONF_DEVICES,
    CONF_EVENTS,
    CONF_TITLE,
    CONF_TTS_ENTITY,
    DOMAIN,
    SERVICE_SEND,
    SERVICE_TEST_DEVICE,
    SERVICE_TEST_EVENT,
    TEST_MESSAGE,
)
from .frontend import async_setup_frontend
from .storage import merged_config, route_map

_LOGGER = logging.getLogger(__name__)
SEND_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_REASON): cv.string,
        vol.Optional(ATTR_CONTEXT, default={}): dict,
        vol.Optional(ATTR_EVENT_KEY): cv.string,
    }
)
TEST_DEVICE_SCHEMA = vol.Schema({vol.Required(ATTR_DEVICE_ID): cv.string, vol.Optional(ATTR_MESSAGE, default=TEST_MESSAGE): cv.string, vol.Required(ATTR_CONFIRM, default=False): cv.boolean})
TEST_EVENT_SCHEMA = vol.Schema({vol.Required(ATTR_REASON): cv.string, vol.Optional(ATTR_CONFIRM, default=False): cv.boolean})


async def async_deliver_profile(hass: HomeAssistant, config_data: dict[str, Any], profile: dict[str, Any], message: str, *, test: bool = False) -> None:
    """Deliver one message using only native Home Assistant actions."""
    if profile["channel"] == "tts":
        tts_entity = config_data.get(CONF_TTS_ENTITY)
        if not tts_entity:
            raise ServiceValidationError("Keine TTS-Engine konfiguriert")
        await hass.services.async_call("tts", "speak", {"media_player_entity_id": profile["entity_id"], "message": message}, target={"entity_id": tts_entity}, blocking=True)
    elif profile["channel"] == "notify":
        await hass.services.async_call("notify", "send_message", {"message": message, "title": "Smart Notifications Test" if test else config_data.get(CONF_TITLE)}, target={"entity_id": profile["entity_id"]}, blocking=True)
    else:
        raise ServiceValidationError(f"Nicht unterstützter Kanal: {profile['channel']}")


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the domain and its central action."""

    runtime = hass.data.setdefault(DOMAIN, {})
    runtime.setdefault("entries", {})
    runtime.setdefault("history", deque(maxlen=100))

    async def async_send(call: ServiceCall) -> None:
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            raise ServiceValidationError("Smart Notifications ist nicht konfiguriert")
        entry = entries[0]
        config_data = merged_config(entry.options)
        reason = call.data[ATTR_REASON]
        event = config_data[CONF_EVENTS].get(reason)
        if not event or not event.get("enabled", True):
            raise ServiceValidationError(f"Unbekanntes oder deaktiviertes Ereignis: {reason}")
        template = Template(event["message"], hass)
        message = template.async_render(call.data.get(ATTR_CONTEXT, {}), parse_result=False)
        selected = route_map(config_data, reason)
        profiles = config_data[CONF_DEVICES]
        seen_physical: set[str] = set()
        deliveries = []
        for profile_id in selected:
            profile = profiles.get(profile_id)
            if not profile or not profile.get("enabled", True):
                continue
            identity = profile.get("physical_key") or f"entity:{profile.get('entity_id')}"
            if identity in seen_physical:
                _LOGGER.info("Suppressed duplicate output for %s (%s)", identity, reason)
                continue
            seen_physical.add(identity)
            try:
                await async_deliver_profile(hass, config_data, profile, message)
                deliveries.append({"profile": profile_id, "status": "sent"})
            except HomeAssistantError as err:  # one unavailable target must not hide others
                _LOGGER.warning("Output failed for %s: %s", profile_id, err)
                deliveries.append({"profile": profile_id, "status": "failed", "error": str(err)})
        hass.data[DOMAIN]["history"].appendleft(
            {"timestamp": datetime.now().isoformat(), "reason": reason, "message": message, "deliveries": deliveries}
        )

    async def async_test_device(call: ServiceCall) -> None:
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries or not call.data.get(ATTR_CONFIRM):
            return
        config_data = merged_config(entries[0].options)
        profile = config_data[CONF_DEVICES].get(call.data[ATTR_DEVICE_ID])
        if not profile:
            raise ServiceValidationError("Ausgabegerät nicht gefunden")
        await async_deliver_profile(hass, config_data, profile, call.data.get(ATTR_MESSAGE, TEST_MESSAGE), test=True)
        hass.data[DOMAIN]["history"].appendleft({"timestamp": datetime.now().isoformat(), "reason": "test_device", "message": call.data.get(ATTR_MESSAGE, TEST_MESSAGE), "deliveries": [{"profile": call.data[ATTR_DEVICE_ID], "status": "sent"}]})

    async def async_test_event(call: ServiceCall) -> None:
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries or not call.data.get(ATTR_CONFIRM):
            return
        await async_send(ServiceCall(DOMAIN, SERVICE_SEND, {ATTR_REASON: call.data[ATTR_REASON], ATTR_CONTEXT: {}}))

    if not hass.services.has_service(DOMAIN, SERVICE_SEND):
        hass.services.async_register(DOMAIN, SERVICE_SEND, async_send, schema=SEND_SCHEMA)
    if not hass.services.has_service(DOMAIN, SERVICE_TEST_DEVICE):
        hass.services.async_register(DOMAIN, SERVICE_TEST_DEVICE, async_test_device, schema=TEST_DEVICE_SCHEMA)
    if not hass.services.has_service(DOMAIN, SERVICE_TEST_EVENT):
        hass.services.async_register(DOMAIN, SERVICE_TEST_EVENT, async_test_event, schema=TEST_EVENT_SCHEMA)
    await async_setup_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = hass.data.setdefault(DOMAIN, {})
    runtime.setdefault("entries", {})
    runtime.setdefault("history", deque(maxlen=100))
    runtime["entries"][entry.entry_id] = entry
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate Beta.1 options without removing user configuration."""
    hass.config_entries.async_update_entry(
        entry,
        options=merged_config(entry.options),
        version=2,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.get(DOMAIN, {}).get("entries", {}).pop(entry.entry_id, None)
    return True
