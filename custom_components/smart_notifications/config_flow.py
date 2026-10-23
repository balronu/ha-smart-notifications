"""Config and options flows for Smart Notifications."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .const import (
    ATTR_CONFIRM,
    ATTR_DEVICE_ID,
    ATTR_MESSAGE,
    ATTR_REASON,
    CONF_DEDUP_SECONDS,
    CONF_DEVICES,
    CONF_EVENTS,
    CONF_ROUTES,
    CONF_TITLE,
    CONF_TTS_ENTITY,
    DOMAIN,
    TEST_MESSAGE,
)
from .storage import discovered_devices, merged_config

_LOGGER = logging.getLogger(__name__)


class SmartNotificationsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle initial setup."""

    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        if user_input is not None:
            return self.async_create_entry(title="Smart Notifications", data={}, options={**user_input, CONF_DEVICES: {}, CONF_ROUTES: {}})
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Optional(CONF_TTS_ENTITY, default=""): selector.EntitySelector(selector.EntitySelectorConfig(domain="tts")), vol.Optional(CONF_TITLE, default="Home Assistant"): str, vol.Optional(CONF_DEDUP_SECONDS, default=30): vol.Coerce(int)}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SmartNotificationsOptionsFlow()


class SmartNotificationsOptionsFlow(config_entries.OptionsFlow):
    """Edit shared event, device and route data."""

    def __init__(self):
        self.data: dict[str, Any] | None = None

    def _ensure_data(self) -> dict[str, Any]:
        if self.data is None:
            self.data = merged_config(self.config_entry.options)
        return self.data

    async def _save_options(self) -> None:
        """Persist a submitted form without ending the navigation flow."""
        self.hass.config_entries.async_update_entry(
            self.config_entry, options=deepcopy(self._ensure_data())
        )

    @staticmethod
    def _profile_label(profile: dict[str, Any]) -> str:
        """Return a human-readable label for stored and newly discovered profiles."""
        return profile.get("alias") or profile.get("display_name") or profile.get("name") or profile.get("entity_id", "")

    @staticmethod
    def _event_options(data: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {"value": key, "label": event["name"]}
            for key, event in data[CONF_EVENTS].items()
        ]

    @staticmethod
    def _device_options(data: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {
                "value": key,
                "label": f"{SmartNotificationsOptionsFlow._profile_label(profile)} – {profile.get('entity_id', '')}",
            }
            for key, profile in data[CONF_DEVICES].items()
        ]

    @staticmethod
    def _entity_options(options: list[dict[str, Any]]) -> list[dict[str, str]]:
        return [{"value": item["entity_id"], "label": item["display_name"]} for item in options]

    @staticmethod
    def _physical_group(profile: dict[str, Any]) -> str:
        key = profile.get("physical_key", "")
        return key.removeprefix("manual:") if key.startswith("manual:") else ""

    async def async_step_init(self, user_input=None):
        self._ensure_data()
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "settings",
                "devices",
                "events",
                "event_devices",
                "device_events",
                "test_device",
                "test_event",
            ],
        )

    async def async_step_back(self, user_input=None):
        """Return to the main menu through the native menu flow."""
        return await self.async_step_init()

    async def async_step_settings(self, user_input=None):
        return self.async_show_menu(
            step_id="settings", menu_options=["settings_form", "back"]
        )

    async def async_step_settings_form(self, user_input=None):
        data = self._ensure_data()
        if user_input is not None:
            data.update(user_input)
            await self._save_options()
            return await self.async_step_settings()
        return self.async_show_form(
            step_id="settings_form",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TTS_ENTITY, default=data.get(CONF_TTS_ENTITY, "")
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="tts")
                    ),
                    vol.Optional(
                        CONF_TITLE, default=data.get(CONF_TITLE, "Home Assistant")
                    ): str,
                    vol.Optional(
                        CONF_DEDUP_SECONDS,
                        default=data.get(CONF_DEDUP_SECONDS, 30),
                    ): vol.Coerce(int),
                }
            ),
        )

    async def async_step_devices(self, user_input=None):
        return self.async_show_menu(
            step_id="devices",
            menu_options=[
                "devices_add_form", "devices_edit_form", "devices_remove_form", "back"
            ],
        )

    def _show_devices_add_form(self, options, errors=None):
        return self.async_show_form(
            step_id="devices_add_form",
            data_schema=vol.Schema(
                {
                    vol.Required("entity_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=self._entity_options(options),
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional("alias", default=""): str,
                    vol.Optional("physical_group", default=""): str,
                }
            ),
            errors=errors or {},
        )

    async def async_step_devices_add_form(self, user_input=None):
        data = self._ensure_data()
        options = discovered_devices(self.hass)
        if not options:
            return self.async_abort(reason="no_discovered_devices")
        if user_input is not None:
            entity_id = user_input["entity_id"]
            if any(profile.get("entity_id") == entity_id for profile in data[CONF_DEVICES].values()):
                return self._show_devices_add_form(options, {"base": "duplicate_entity"})
            found = next((x for x in options if x["entity_id"] == entity_id), None)
            if found:
                profile_id = entity_id.replace(".", "_")
                profile = {**found, "enabled": True, "alias": user_input.get("alias", "").strip()}
                if user_input.get("physical_group"):
                    profile["physical_key"] = f"manual:{user_input['physical_group'].strip().lower()}"
                    profile["physical_confidence"] = "manual"
                    profile["physical_evidence"] = "Manuell bestätigt"
                data[CONF_DEVICES][profile_id] = profile
            await self._save_options()
            return await self.async_step_devices()
        return self._show_devices_add_form(options)

    async def async_step_devices_edit_form(self, user_input=None):
        data = self._ensure_data()
        if not data[CONF_DEVICES]:
            return self.async_abort(reason="no_devices")
        options = discovered_devices(self.hass)
        current_entities = {profile.get("entity_id") for profile in data[CONF_DEVICES].values()}
        known = {item["entity_id"] for item in options}
        for entity_id in current_entities - known:
            options.append({"entity_id": entity_id, "display_name": f"{entity_id} – nicht verfügbar"})
        if user_input is not None:
            profile_id = user_input["device_id"]
            profile = data[CONF_DEVICES].get(profile_id)
            entity_id = user_input["entity_id"]
            if profile is None:
                return self.async_abort(reason="no_devices")
            if any(key != profile_id and value.get("entity_id") == entity_id for key, value in data[CONF_DEVICES].items()):
                return self._show_devices_edit_form(data, options, {"base": "duplicate_entity"})
            found = next((item for item in options if item["entity_id"] == entity_id), None)
            updated = {**profile, "entity_id": entity_id, "alias": user_input.get("alias", "").strip(), "enabled": user_input.get("enabled", True)}
            if found:
                updated.update({key: value for key, value in found.items() if key not in {"entity_id", "display_name"}})
            group = user_input.get("physical_group", "").strip()
            if group:
                updated["physical_key"] = f"manual:{group.lower()}"
                updated["physical_confidence"] = "manual"
                updated["physical_evidence"] = "Manuell bestätigt"
            data[CONF_DEVICES][profile_id] = updated
            await self._save_options()
            return await self.async_step_devices()
        return self._show_devices_edit_form(data, options)

    def _show_devices_edit_form(self, data, options, errors=None):
        return self.async_show_form(
            step_id="devices_edit_form",
            data_schema=vol.Schema(
                {
                    vol.Required("device_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=self._device_options(data))
                    ),
                    vol.Required("entity_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=self._entity_options(options))
                    ),
                    vol.Optional("alias", default=""): str,
                    vol.Optional("physical_group", default=""): str,
                    vol.Required("enabled", default=True): bool,
                }
            ),
            errors=errors or {},
        )

    async def async_step_devices_remove_form(self, user_input=None):
        data = self._ensure_data()
        if not data[CONF_DEVICES]:
            return self.async_abort(reason="no_devices")
        if user_input is not None:
            profile_id = user_input["device_id"]
            if user_input.get("confirm"):
                data[CONF_DEVICES].pop(profile_id, None)
                for reason, route in data[CONF_ROUTES].items():
                    data[CONF_ROUTES][reason] = [item for item in route if item != profile_id]
                await self._save_options()
            return await self.async_step_devices()
        return self.async_show_form(
            step_id="devices_remove_form",
            data_schema=vol.Schema(
                {
                    vol.Required("device_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=self._device_options(data))
                    ),
                    vol.Required("confirm", default=False): bool,
                }
            ),
        )

    async def async_step_events(self, user_input=None):
        return self.async_show_menu(step_id="events", menu_options=["events_form", "back"])

    async def async_step_events_form(self, user_input=None):
        data = self._ensure_data()
        event_keys = sorted(data[CONF_EVENTS])
        if user_input is not None:
            key = user_input["reason"]
            data[CONF_EVENTS][key].update({"name": user_input["name"], "message": user_input["message"], "enabled": user_input["enabled"], "priority": user_input["priority"]})
            await self._save_options()
            return await self.async_step_events()
        return self.async_show_form(
            step_id="events_form",
            data_schema=vol.Schema(
                {
                    vol.Required("reason"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": key, "label": data[CONF_EVENTS][key]["name"]}
                                for key in event_keys
                            ]
                        )
                    ),
                    vol.Required("name"): str,
                    vol.Required("message"): str,
                    vol.Required("enabled", default=True): bool,
                    vol.Required("priority", default="normal"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["low", "normal", "high", "critical"],
                            translation_key="priority",
                        )
                    ),
                }
            ),
        )

    async def async_step_event_devices(self, user_input=None):
        return self.async_show_menu(
            step_id="event_devices", menu_options=["event_devices_form", "back"]
        )

    async def async_step_event_devices_form(self, user_input=None):
        data = self._ensure_data()
        if not data[CONF_DEVICES]:
            return self.async_abort(reason="no_devices")
        if user_input is not None:
            data[CONF_ROUTES][user_input["reason"]] = user_input.get("devices", [])
            await self._save_options()
            return await self.async_step_event_devices()
        return self.async_show_form(
            step_id="event_devices_form",
            data_schema=vol.Schema(
                {
                    vol.Required("reason"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=self._event_options(data))
                    ),
                    vol.Optional("devices", default=[]): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=self._device_options(data), multiple=True
                        )
                    ),
                }
            ),
        )

    async def async_step_device_events(self, user_input=None):
        return self.async_show_menu(
            step_id="device_events", menu_options=["device_events_form", "back"]
        )

    async def async_step_device_events_form(self, user_input=None):
        data = self._ensure_data()
        if not data[CONF_DEVICES]:
            return self.async_abort(reason="no_devices")
        if user_input is not None:
            profile_id = user_input["device"]
            selected = set(user_input.get("events", []))
            for reason in data[CONF_EVENTS]:
                current = set(data[CONF_ROUTES].get(reason, []))
                if reason in selected: current.add(profile_id)
                else: current.discard(profile_id)
                data[CONF_ROUTES][reason] = sorted(current)
            await self._save_options()
            return await self.async_step_device_events()
        return self.async_show_form(
            step_id="device_events_form",
            data_schema=vol.Schema(
                {
                    vol.Required("device"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=self._device_options(data))
                    ),
                    vol.Optional("events", default=[]): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=self._event_options(data), multiple=True
                        )
                    ),
                }
            ),
        )

    async def async_step_test_device(self, user_input=None):
        return self.async_show_menu(
            step_id="test_device", menu_options=["test_device_form", "back"]
        )

    def _show_test_device_form(self, data, errors=None):
        return self.async_show_form(
            step_id="test_device_form",
            data_schema=vol.Schema(
                {
                    vol.Required(ATTR_DEVICE_ID): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=self._device_options(data))
                    ),
                    vol.Optional(ATTR_MESSAGE, default=TEST_MESSAGE): str,
                    vol.Required(ATTR_CONFIRM, default=False): bool,
                }
            ),
            errors=errors or {},
        )

    async def async_step_test_device_form(self, user_input=None):
        data = self._ensure_data()
        if not data[CONF_DEVICES]:
            return self.async_abort(reason="no_devices")
        if user_input is not None:
            if user_input.get(ATTR_CONFIRM):
                try:
                    await self.hass.services.async_call(DOMAIN, "test_device", {ATTR_DEVICE_ID: user_input[ATTR_DEVICE_ID], ATTR_MESSAGE: user_input.get(ATTR_MESSAGE, TEST_MESSAGE), ATTR_CONFIRM: True}, blocking=True)
                except HomeAssistantError as err:
                    error_key = str(err)
                    if error_key not in {"device_unavailable", "tts_unavailable", "notify_unavailable", "test_failed"}:
                        error_key = "test_failed"
                    return self._show_test_device_form(data, {"base": error_key})
                except Exception:
                    _LOGGER.exception("Unexpected single-device test failure")
                    return self._show_test_device_form(data, {"base": "test_failed"})
            return await self.async_step_test_device()
        return self._show_test_device_form(data)

    async def async_step_test_event(self, user_input=None):
        return self.async_show_menu(
            step_id="test_event", menu_options=["test_event_form", "back"]
        )

    def _show_test_event_form(self, data, errors=None):
        return self.async_show_form(
            step_id="test_event_form",
            data_schema=vol.Schema(
                {
                    vol.Required(ATTR_REASON): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=self._event_options(data))
                    ),
                    vol.Required(ATTR_CONFIRM, default=False): bool,
                }
            ),
            errors=errors or {},
        )

    async def async_step_test_event_form(self, user_input=None):
        data = self._ensure_data()
        if user_input is not None:
            if user_input.get(ATTR_CONFIRM):
                try:
                    await self.hass.services.async_call(DOMAIN, "test_event", {ATTR_REASON: user_input[ATTR_REASON], ATTR_CONFIRM: True}, blocking=True)
                except HomeAssistantError as err:
                    error_key = str(err)
                    if error_key not in {"event_not_found", "message_missing", "no_event_devices", "device_unavailable", "tts_unavailable", "notify_unavailable", "all_deliveries_failed", "partial_delivery"}:
                        error_key = "test_failed"
                    return self._show_test_event_form(data, {"base": error_key})
                except Exception:
                    _LOGGER.exception("Unexpected event test failure")
                    return self._show_test_event_form(data, {"base": "test_failed"})
            return await self.async_step_test_event()
        return self._show_test_event_form(data)
