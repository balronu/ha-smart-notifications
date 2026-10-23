from pathlib import Path


def test_card_contains_editor_and_deliberate_test_api():
    source = Path("custom_components/smart_notifications/frontend/smart-notifications-card.js").read_text()
    assert "smart-notifications-card-editor" in source
    assert "smart_notifications/status" in source
    assert "smart_notifications/test" in source
    assert "config-changed" in source
