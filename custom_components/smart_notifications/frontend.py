"""Static Lovelace card and authenticated status/test API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aiohttp import web
from homeassistant.components import frontend as ha_frontend
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.http.server import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, SERVICE_TEST_DEVICE, SERVICE_TEST_EVENT
from .discovery import apply_candidate_action, async_scan
from .storage import merged_config

CARD_RESOURCE_URL = "/smart_notifications/smart-notifications-card.js?v=0.1.0-beta.9"


class SmartNotificationsStatusView(HomeAssistantView):
    """Expose only the configured output metadata and bounded runtime history."""

    url = "/api/smart_notifications/status"
    name = "api:smart_notifications:status"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        entry = next(iter(hass.config_entries.async_entries(DOMAIN)), None)
        config = merged_config(entry.options if entry else {})
        devices = [{"id": key, "name": value.get("name", key), "entity_id": value.get("entity_id"), "channel": value.get("channel"), "available": hass.states.get(value.get("entity_id", "")).state not in (None, "unavailable", "unknown")} for key, value in config["devices"].items()]
        return self.json({"configured": entry is not None, "devices": devices, "events": [{"id": key, "name": value["name"], "message": value["message"], "devices": config["routes"].get(key, [])} for key, value in config["events"].items() if value.get("enabled", True)], "history": list(hass.data.get(DOMAIN, {}).get("history", []))[:20]})


class SmartNotificationsTestView(HomeAssistantView):
    """Handle deliberate card test clicks; no action occurs on GET or load."""

    url = "/api/smart_notifications/test"
    name = "api:smart_notifications:test"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        data: dict[str, Any] = await request.json()
        hass: HomeAssistant = request.app["hass"]
        if data.get("kind") == "device":
            await hass.services.async_call(DOMAIN, SERVICE_TEST_DEVICE, {"device_id": data.get("device_id", ""), "message": data.get("message", ""), "confirm": True}, blocking=True)
        elif data.get("kind") == "event":
            await hass.services.async_call(DOMAIN, SERVICE_TEST_EVENT, {"reason": data.get("reason", ""), "confirm": True}, blocking=True)
        else:
            return self.json({"error": "kind must be device or event"}, status_code=400)
        return self.json({"ok": True})


class SmartNotificationsDiscoveryView(HomeAssistantView):
    """Authenticated discovery API used by the Lovelace card.

    It delegates state changes to the same discovery helper used by the native
    Options Flow. It never writes automation or script sources.
    """

    url = "/api/smart_notifications/discovery"
    name = "api:smart_notifications:discovery"
    requires_auth = True

    @staticmethod
    def _entry(hass: HomeAssistant):
        return next(iter(hass.config_entries.async_entries(DOMAIN)), None)

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        entry = self._entry(hass)
        config = merged_config(entry.options if entry else {})
        candidates = list(config.get("discovery", {}).get("candidates", {}).values())
        return self.json({
            "configured": entry is not None,
            "source_scope": "automations.yaml und scripts.yaml; Storage-Automationen werden nicht über private APIs gelesen.",
            "candidates": candidates,
            "events": [{"id": key, **value, "devices": config["routes"].get(key, [])} for key, value in config["events"].items()],
            "devices": [{"id": key, "name": value.get("alias") or value.get("name") or key, "entity_id": value.get("entity_id")} for key, value in config["devices"].items()],
        })

    async def post(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        entry = self._entry(hass)
        if entry is None:
            return self.json({"error": "not_configured"}, status_code=409)
        payload: dict[str, Any] = await request.json()
        config = merged_config(entry.options)
        action = payload.get("action")
        if action == "scan":
            candidates = await async_scan(hass, config.get("discovery"))
            config["discovery"] = {"candidates": {item["candidate_id"]: item for item in candidates}}
        elif action in {"review", "ignore", "adopt"}:
            candidate = apply_candidate_action(config, str(payload.get("candidate_id", "")), action, payload.get("edits"))
            if candidate is None:
                return self.json({"error": "candidate_not_found"}, status_code=404)
        else:
            return self.json({"error": "unsupported_action"}, status_code=400)
        hass.config_entries.async_update_entry(entry, options=config)
        return self.json({"ok": True, "candidates": list(config["discovery"]["candidates"].values()), "events": config["events"]})


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register the static card and API once during domain setup."""
    if hass.http is None:
        return
    runtime = hass.data.setdefault(DOMAIN, {})
    if runtime.get("frontend_registered"):
        return
    card_path = Path(__file__).parent / "frontend" / "smart-notifications-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig("/smart_notifications/smart-notifications-card.js", str(card_path), cache_headers=False)]
    )
    # Public HA API: load the module before Lovelace builds the card picker.
    # The query string is a cache-buster for HACS upgrades; the static path
    # remains the same and therefore needs no second resource registration.
    ha_frontend.add_extra_js_url(hass, CARD_RESOURCE_URL)
    hass.http.register_view(SmartNotificationsStatusView)
    hass.http.register_view(SmartNotificationsTestView)
    hass.http.register_view(SmartNotificationsDiscoveryView)
    runtime["frontend_registered"] = True
