"""Constants for Smart Notifications."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "smart_notifications"
NAME = "Smart Notifications"
VERSION = "0.1.0-beta.10"
PLATFORMS: list[str] = []

SERVICE_SEND = "send"
SERVICE_TEST_DEVICE = "test_device"
SERVICE_TEST_EVENT = "test_event"
CONF_EVENTS = "events"
CONF_DEVICES = "devices"
CONF_ROUTES = "routes"
CONF_DISCOVERY = "discovery"
CONF_TTS_ENTITY = "tts_entity"
CONF_TITLE = "title"
CONF_DEDUP_SECONDS = "dedup_seconds"

DEFAULT_DEDUP_SECONDS = 30
DEFAULT_TITLE = "Home Assistant"
ATTR_REASON = "reason"
ATTR_CONTEXT = "context"
ATTR_VARIABLES = "variables"
ATTR_EVENT_KEY = "event_key"
ATTR_DEVICE_ID = "device_id"
ATTR_MESSAGE = "message"
CONF_MESSAGE_TYPE = "message_type"
CONF_PARAMETERS = "parameters"
ATTR_CONFIRM = "confirm"
TEST_MESSAGE = "Dies ist eine Testnachricht von Smart Notifications."

EVENT_DEFINITIONS = {
    "fridge_open": ("Kühlschrank noch offen", "Der Kühlschrank ist noch offen."),
    "water_running": ("Wasser läuft noch", "Das Wasser läuft noch."),
    "smoke_detected": ("Rauch erkannt", "Rauch wurde erkannt."),
    "washer_finished": ("Waschmaschine fertig", "Die Waschmaschine ist fertig."),
    "dryer_finished": ("Trockner fertig", "Der Trockner ist fertig."),
    "doorbell_pressed": ("Türklingel betätigt", "Die Türklingel wurde betätigt."),
    "garage_opened": ("Garage geöffnet", "Die Garage wurde geöffnet."),
    "garage_closed": ("Garage geschlossen", "Die Garage wurde geschlossen."),
    "window_open": ("Fenster noch offen", "Ein Fenster ist noch offen."),
    "custom_event": ("Benutzerdefiniertes Ereignis", "Eine Benachrichtigung wurde ausgelöst."),
}

DEFAULT_CONFIG = {
    CONF_EVENTS: {
        key: {"name": name, "message": message, "enabled": True, "priority": "normal"}
        for key, (name, message) in EVENT_DEFINITIONS.items()
    },
    CONF_DEVICES: {},
    CONF_ROUTES: {},
    CONF_DISCOVERY: {"candidates": {}},
    CONF_TTS_ENTITY: "",
    CONF_DEDUP_SECONDS: DEFAULT_DEDUP_SECONDS,
    CONF_TITLE: DEFAULT_TITLE,
}

DEDUP_WINDOW = timedelta(seconds=DEFAULT_DEDUP_SECONDS)
