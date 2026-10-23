from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from smart_notifications.frontend import async_setup_frontend


def test_card_contains_editor_and_deliberate_test_api():
    source = Path("custom_components/smart_notifications/frontend/smart-notifications-card.js").read_text()
    assert "smart-notifications-card-editor" in source
    assert "smart_notifications/status" in source
    assert "smart_notifications/test" in source
    assert "smart_notifications/discovery" in source
    assert "Als deaktiviertes Ereignis übernehmen" in source
    assert "Start scan" in source
    assert "config-changed" in source


@pytest.mark.asyncio
async def test_frontend_registration_uses_current_ha_api_and_is_idempotent():
    static = SimpleNamespace(async_register_static_paths=AsyncMock(), register_view=Mock())
    hass = SimpleNamespace(http=static, data={})
    await async_setup_frontend(hass)
    await async_setup_frontend(hass)
    assert static.async_register_static_paths.await_count == 1
    assert static.register_view.call_count == 3
