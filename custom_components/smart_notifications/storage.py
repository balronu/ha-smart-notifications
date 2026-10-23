"""Configuration and physical-device helpers."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_DEVICES, CONF_EVENTS, CONF_ROUTES, DEFAULT_CONFIG
from .message import normalize_event

UUID_RE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)


def default_config() -> dict[str, Any]:
    return deepcopy(DEFAULT_CONFIG)


def merged_config(options: dict[str, Any] | None) -> dict[str, Any]:
    config = default_config()
    for key, value in (options or {}).items():
        if key in (CONF_EVENTS, CONF_DEVICES, CONF_ROUTES) and isinstance(value, dict):
            if key == CONF_EVENTS:
                config[key].update({event_key: normalize_event(deepcopy(event)) for event_key, event in value.items()})
            else:
                config[key].update(deepcopy(value))
        else:
            config[key] = deepcopy(value)
    return config


def physical_key(hass: HomeAssistant, entity_id: str) -> str:
    """Return a stable best-effort physical identity for an entity."""
    registry = er.async_get(hass)
    entity = registry.async_get(entity_id)
    if entity and entity.device_id:
        devices = dr.async_get(hass)
        device = devices.async_get(entity.device_id)
        if device:
            for _domain, identifier in device.identifiers:
                normalized = re.sub(r"[^0-9a-f]", "", identifier.lower())
                if UUID_RE.match(normalized):
                    return f"physical:{normalized}"
            return f"device:{device.id}"
    return f"entity:{entity_id}"


def discovered_devices(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Return only channels implemented by the first beta."""
    result: list[dict[str, Any]] = []
    registry = er.async_get(hass)
    areas = ar.async_get(hass)
    integration_names = {
        "cast": "Google Cast",
        "music_assistant": "Music Assistant",
        "mobile_app": "Mobile App",
        "notify": "Notify",
    }
    for entity in registry.entities.values():
        if entity.domain not in ("media_player", "notify"):
            continue
        state = hass.states.get(entity.entity_id)
        name = (
            entity.name
            or entity.original_name
            or (state.attributes.get("friendly_name") if state else None)
            or entity.entity_id
        )
        config_entry = (
            hass.config_entries.async_get_entry(entity.config_entry_id)
            if entity.config_entry_id
            else None
        )
        integration = integration_names.get(
            config_entry.domain if config_entry else entity.domain,
            (config_entry.domain if config_entry else entity.domain)
            .replace("_", " ")
            .title(),
        )
        channel = "tts" if entity.domain == "media_player" else "notify"
        channel_name = "Sprachausgabe" if channel == "tts" else "Push-Benachrichtigung"
        area_name = None
        if entity.area_id and (area := areas.async_get_area(entity.area_id)):
            area_name = area.name
        display_name = f"{name} – {integration} – {channel_name}"
        if area_name:
            display_name = f"{name} ({area_name}) – {integration} – {channel_name}"
        result.append(
            {
                "entity_id": entity.entity_id,
                "name": name,
                "display_name": display_name,
                "area": area_name,
                "integration": integration,
                "domain": entity.domain,
                "channel": channel,
                "physical_key": physical_key(hass, entity.entity_id),
                "physical_confidence": "high" if entity.device_id else "low",
                "physical_evidence": "Home-Assistant-Gerät" if entity.device_id else "Keine gemeinsame Geräte-ID",
            }
        )
    return sorted(result, key=lambda item: item["entity_id"])


def discovered_tts_entities(hass: HomeAssistant) -> list[dict[str, str]]:
    """Return TTS engines separately from output devices."""
    return sorted(
        [
            {
                "entity_id": state.entity_id,
                "name": state.attributes.get("friendly_name", state.entity_id),
            }
            for state in hass.states.async_all("tts")
        ],
        key=lambda item: item["entity_id"],
    )


def route_map(config: dict[str, Any], reason: str) -> list[str]:
    return list(config.get(CONF_ROUTES, {}).get(reason, []))
