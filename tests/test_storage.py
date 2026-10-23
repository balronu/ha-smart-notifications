from smart_notifications.const import EVENT_DEFINITIONS
from smart_notifications.storage import default_config, discovered_tts_entities, merged_config, route_map


def test_default_catalog_contains_required_events():
    config = default_config()
    assert set(EVENT_DEFINITIONS).issubset(config["events"])
    assert all(item["message"] for item in config["events"].values())


def test_options_are_merged_without_mutating_defaults():
    config = merged_config({"routes": {"washer_finished": ["media_player_kitchen"]}})
    assert route_map(config, "washer_finished") == ["media_player_kitchen"]
    assert route_map(default_config(), "washer_finished") == []


def test_same_event_has_one_shared_message_field():
    event = default_config()["events"]["washer_finished"]
    assert set(event) == {"name", "message", "enabled", "priority"}


def test_partial_beta1_options_keep_default_catalog():
    config = merged_config({"events": {"washer_finished": {"message": "Neu"}}})
    assert config["events"]["washer_finished"]["message"] == "Neu"
    assert config["events"]["smoke_detected"]["message"]


def test_tts_engines_are_discovered_from_live_tts_states(hass):
    hass.states.async_set("tts.piper", "2026-10-23T00:00:00+00:00", {"friendly_name": "Piper"})
    assert discovered_tts_entities(hass) == [{"entity_id": "tts.piper", "name": "Piper"}]
