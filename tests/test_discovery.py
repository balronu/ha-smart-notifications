from unittest.mock import patch

import pytest
from smart_notifications.discovery import async_scan, scan_documents


def test_scan_detects_nested_tts_push_and_smart_notifications_actions():
    candidates = scan_documents(
        {
            "automation": {
                "fridge": {
                    "action": [
                        {"choose": [{"sequence": [{"service": "tts.speak", "data": {"message": "Kühlschrank offen"}}]}]},
                        {"service": "notify.mobile_app_phone", "data": {"message": "Kühlschrank offen"}},
                    ]
                }
            },
            "script": {"announce": {"sequence": [{"action": "smart_notifications.send", "data": {"reason": "fridge_open"}}]}},
        }
    )
    assert {item["service"] for item in candidates} == {"tts.speak", "notify.mobile_app_phone", "smart_notifications.send"}
    assert all(item["candidate_id"] for item in candidates)


def test_scan_ignores_unrelated_media_and_supports_repeat():
    candidates = scan_documents({"automation": {"x": {"action": [{"service": "light.turn_on"}, {"repeat": {"sequence": [{"service": "notify.send_message", "data": {"message": "Fertig"}}]}}]}}})
    assert len(candidates) == 1
    assert candidates[0]["confidence"] == "high"


def test_discovery_groups_same_message_and_keeps_different_messages_separate():
    candidates = scan_documents({"automation": {"house": {"alias": "Haushaltsmeldung", "action": [
        {"service": "notify.mobile_app_michael", "data": {"message": "Tür offen"}},
        {"service": "notify.mobile_app_michaela", "data": {"message": "Tür offen"}},
        {"service": "notify.mobile_app_michael", "data": {"message": "Fenster offen"}},
    ]}}})
    assert len({item["group_id"] for item in candidates}) == 2
    same = [item for item in candidates if item["message"] == "Tür offen"]
    assert len(same) == 2
    assert {item["group_size"] for item in same} == {2}
    assert all(item["source_name"] == "Haushaltsmeldung" for item in candidates)


def test_discovery_marks_templates_and_technical_fallback_name():
    candidates = scan_documents({"script": {"notify_later": {"sequence": [{"action": "tts.speak", "data": {"message": "{{ states('sensor.foo') }}"}}]}}})
    assert candidates[0]["source_name_quality"] == "technical_fallback"
    assert candidates[0]["message_is_template"] is True
    assert candidates[0]["templates"]
    assert candidates[0]["template_variables"] == []


def test_discovery_reports_unresolved_script_variables_without_inventing_values():
    candidates = scan_documents({"script": {"alarm": {"sequence": [{"action": "notify.send_message", "data": {"message": "{{ msg_text }}"}}]}}})
    assert candidates[0]["message_type"] == "template"
    assert candidates[0]["template_variables"] == ["msg_text"]
    assert candidates[0]["suggested_reason"] == "alarm"


def test_automation_trigger_and_conditions_are_carried_into_group_identity():
    documents = {"automation": {
        "one": {"alias": "Meldung", "trigger": [{"platform": "state", "entity_id": "sensor.a"}], "condition": [{"condition": "state", "entity_id": "input_boolean.x", "state": "on"}], "action": [{"service": "notify.send_message", "data": {"message": "Gleich"}}]},
        "two": {"alias": "Meldung", "trigger": [{"platform": "state", "entity_id": "sensor.b"}], "condition": [{"condition": "state", "entity_id": "input_boolean.x", "state": "on"}], "action": [{"service": "notify.send_message", "data": {"message": "Gleich"}}]},
    }}
    candidates = scan_documents(documents)
    assert candidates[0]["trigger"] != candidates[1]["trigger"]
    assert candidates[0]["conditions"] == candidates[1]["conditions"]
    assert candidates[0]["group_id"] != candidates[1]["group_id"]


@pytest.mark.asyncio
async def test_async_scan_marks_removed_candidates_as_not_found(hass, tmp_path):
    (tmp_path / "automations.yaml").write_text(
        "- id: current\n  action:\n    - service: notify.send_message\n      data:\n        message: Current\n",
        encoding="utf-8",
    )
    (tmp_path / "scripts.yaml").write_text("{}\n", encoding="utf-8")
    hass.config.path = lambda *parts: str(tmp_path.joinpath(*parts))
    previous = {
        "candidates": {
            "old-id": {
                "candidate_id": "old-id",
                "source_type": "automation",
                "source_id": "old",
                "service": "notify.send_message",
                "message": "Old",
                "status": "unchanged",
            }
        }
    }
    with patch.object(hass, "async_add_executor_job", wraps=hass.async_add_executor_job):
        result = await async_scan(hass, previous)
    assert any(item["candidate_id"] == "old-id" and item["status"] == "not_found" for item in result)
