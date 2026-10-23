"""Config and options flows for Smart Notifications."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
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

    async def async_step_init(self, user_input=None):
        self._ensure_data()
        return self.async_show_menu(step_id="init", menu_options=["settings", "devices", "events", "event_devices", "device_events", "test_device", "test_event"])

    async def async_step_settings(self, user_input=None):
        data = self._ensure_data()
        if user_input is not None:
            data.update(user_input)
            return self.async_create_entry(title="", data=data)
        return self.async_show_form(step_id="settings", data_schema=vol.Schema({vol.Optional(CONF_TTS_ENTITY, default=data.get(CONF_TTS_ENTITY, "")): selector.EntitySelector(selector.EntitySelectorConfig(domain="tts")), vol.Optional(CONF_TITLE, default=data.get(CONF_TITLE, "Home Assistant")): str, vol.Optional(CONF_DEDUP_SECONDS, default=data.get(CONF_DEDUP_SECONDS, 30)): vol.Coerce(int)}))

    async def async_step_devices(self, user_input=None):
        data = self._ensure_data()
        options = discovered_devices(self.hass)
        if user_input is not None:
            entity_id = user_input["entity_id"]
            found = next((x for x in options if x["entity_id"] == entity_id), None)
            if found:
                profile_id = entity_id.replace(".", "_")
                profile = {**found, "enabled": True}
                if user_input.get("physical_group"):
                    profile["physical_key"] = f"manual:{user_input['physical_group'].strip().lower()}"
                    profile["physical_confidence"] = "manual"
                    profile["physical_evidence"] = "Manuell bestätigt"
                data[CONF_DEVICES][profile_id] = profile
            return self.async_create_entry(title="", data=data)
        return self.async_show_form(step_id="devices", data_schema=vol.Schema({
            vol.Required("entity_id"): selector.SelectSelector(selector.SelectSelectorConfig(options=[{"value": x["entity_id"], "label": f"{x['name']} ({x['entity_id']}) – {x['channel']}"} for x in options], mode=selector.SelectSelectorMode.DROPDOWN)),
            vol.Optional("physical_group", default=""): str,
        }))

    async def async_step_events(self, user_input=None):
        data = self._ensure_data()
        event_keys = sorted(data[CONF_EVENTS])
        if user_input is not None:
            key = user_input["reason"]
            data[CONF_EVENTS][key].update({"name": user_input["name"], "message": user_input["message"], "enabled": user_input["enabled"], "priority": user_input["priority"]})
            return self.async_create_entry(title="", data=data)
        return self.async_show_form(step_id="events", data_schema=vol.Schema({vol.Required("reason"): selector.SelectSelector(selector.SelectSelectorConfig(options=[{"value": k, "label": data[CONF_EVENTS][k]["name"]} for k in event_keys])), vol.Required("name"): str, vol.Required("message"): str, vol.Required("enabled", default=True): bool, vol.Required("priority", default="normal"): selector.SelectSelector(selector.SelectSelectorConfig(options=["low", "normal", "high", "critical"]))}))

    async def async_step_event_devices(self, user_input=None):
        data = self._ensure_data()
        if user_input is not None:
            data[CONF_ROUTES][user_input["reason"]] = user_input.get("devices", [])
            return self.async_create_entry(title="", data=data)
        return self.async_show_form(step_id="event_devices", data_schema=vol.Schema({vol.Required("reason"): selector.SelectSelector(selector.SelectSelectorConfig(options=[{"value": k, "label": v["name"]} for k, v in data[CONF_EVENTS].items()])), vol.Optional("devices", default=[]): selector.SelectSelector(selector.SelectSelectorConfig(options=[{"value": k, "label": v["name"]} for k, v in data[CONF_DEVICES].items()], multiple=True))}))

    async def async_step_device_events(self, user_input=None):
        data = self._ensure_data()
        if user_input is not None:
            profile_id = user_input["device"]
            selected = set(user_input.get("events", []))
            for reason in data[CONF_EVENTS]:
                current = set(data[CONF_ROUTES].get(reason, []))
                if reason in selected: current.add(profile_id)
                else: current.discard(profile_id)
                data[CONF_ROUTES][reason] = sorted(current)
            return self.async_create_entry(title="", data=data)
        return self.async_show_form(step_id="device_events", data_schema=vol.Schema({vol.Required("device"): selector.SelectSelector(selector.SelectSelectorConfig(options=[{"value": k, "label": v["name"]} for k, v in data[CONF_DEVICES].items()])), vol.Optional("events", default=[]): selector.SelectSelector(selector.SelectSelectorConfig(options=[{"value": k, "label": v["name"]} for k, v in data[CONF_EVENTS].items()], multiple=True))}))

    async def async_step_test_device(self, user_input=None):
        data = self._ensure_data()
        if user_input is not None:
            if user_input.get(ATTR_CONFIRM):
                await self.hass.services.async_call(DOMAIN, "test_device", {ATTR_DEVICE_ID: user_input[ATTR_DEVICE_ID], ATTR_MESSAGE: user_input.get(ATTR_MESSAGE, TEST_MESSAGE), ATTR_CONFIRM: True}, blocking=True)
            return self.async_create_entry(title="", data=data)
        return self.async_show_form(step_id="test_device", data_schema=vol.Schema({vol.Required(ATTR_DEVICE_ID): selector.SelectSelector(selector.SelectSelectorConfig(options=[{"value": k, "label": v["name"]} for k, v in data[CONF_DEVICES].items()])), vol.Optional(ATTR_MESSAGE, default=TEST_MESSAGE): str, vol.Required(ATTR_CONFIRM, default=False): bool}))

    async def async_step_test_event(self, user_input=None):
        data = self._ensure_data()
        if user_input is not None:
            if user_input.get(ATTR_CONFIRM):
                await self.hass.services.async_call(DOMAIN, "test_event", {ATTR_REASON: user_input[ATTR_REASON], ATTR_CONFIRM: True}, blocking=True)
            return self.async_create_entry(title="", data=data)
        return self.async_show_form(step_id="test_event", data_schema=vol.Schema({vol.Required(ATTR_REASON): selector.SelectSelector(selector.SelectSelectorConfig(options=[{"value": k, "label": v["name"]} for k, v in data[CONF_EVENTS].items()])), vol.Required(ATTR_CONFIRM, default=False): bool}))
