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
