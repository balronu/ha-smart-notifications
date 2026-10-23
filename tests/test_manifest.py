import json
from pathlib import Path


def test_manifest_version_and_domain():
    data = json.loads(Path("custom_components/smart_notifications/manifest.json").read_text())
    assert data["domain"] == "smart_notifications"
    assert data["version"] == "0.1.0-beta.4"
    assert data["config_flow"] is True


def test_translations_are_valid_json():
    for path in Path("custom_components/smart_notifications").rglob("*.json"):
        json.loads(path.read_text())


def test_config_flow_translations_have_no_runtime_placeholders():
    for path in (
        Path("custom_components/smart_notifications/strings.json"),
        Path("custom_components/smart_notifications/translations/de.json"),
        Path("custom_components/smart_notifications/translations/en.json"),
    ):
        assert "device_count" not in path.read_text()
