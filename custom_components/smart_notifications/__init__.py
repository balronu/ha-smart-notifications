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
    ATTR_CONTEXT,
    ATTR_EVENT_KEY,
    ATTR_REASON,
    CONF_DEVICES,
    CONF_EVENTS,
    CONF_TITLE,
    CONF_TTS_ENTITY,
    DOMAIN,
    SERVICE_SEND,
)
from .storage import merged_config, route_map

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_REASON): cv.string,
        vol.Optional(ATTR_CONTEXT, default={}): dict,
        vol.Optional(ATTR_EVENT_KEY): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the domain and its central action."""

    hass.data.setdefault(DOMAIN, {"entries": {}, "history": deque(maxlen=100)})

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
                if profile["channel"] == "tts":
                    tts_entity = config_data.get(CONF_TTS_ENTITY)
                    if not tts_entity:
                        raise ServiceValidationError("Keine TTS-Engine konfiguriert")
                    await hass.services.async_call(
                        "tts",
                        "speak",
                        {
                            "media_player_entity_id": profile["entity_id"],
                            "message": message,
                        },
                        target={"entity_id": tts_entity},
                        blocking=True,
                    )
                elif profile["channel"] == "notify":
                    await hass.services.async_call(
                        "notify",
                        "send_message",
                        {"message": message, "title": config_data.get(CONF_TITLE)},
                        target={"entity_id": profile["entity_id"]},
                        blocking=True,
                    )
                else:
                    raise ServiceValidationError(f"Nicht unterstützter Kanal: {profile['channel']}")
                deliveries.append({"profile": profile_id, "status": "sent"})
            except HomeAssistantError as err:  # one unavailable target must not hide others
                _LOGGER.warning("Output failed for %s: %s", profile_id, err)
                deliveries.append({"profile": profile_id, "status": "failed", "error": str(err)})
        hass.data[DOMAIN]["history"].appendleft(
            {"timestamp": datetime.now().isoformat(), "reason": reason, "message": message, "deliveries": deliveries}
        )

    hass.services.async_register(DOMAIN, SERVICE_SEND, async_send, schema=CONFIG_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {"entries": {}, "history": deque(maxlen=100)})
    hass.data[DOMAIN]["entries"][entry.entry_id] = entry
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN]["entries"].pop(entry.entry_id, None)
    return True
