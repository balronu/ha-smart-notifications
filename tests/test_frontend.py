from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components import frontend as ha_frontend
from smart_notifications.const import DOMAIN
from smart_notifications.frontend import CARD_RESOURCE_URL, async_setup_frontend


def test_card_contains_editor_and_deliberate_test_api():
    source = Path("custom_components/smart_notifications/frontend/smart-notifications-card.js").read_text()
    assert "smart-notifications-card-editor" in source
    assert "smart_notifications/status" in source
    assert "smart_notifications/test" in source
    assert "smart_notifications/discovery" in source
    assert "Als deaktiviertes Ereignis übernehmen" in source
    assert "Start scan" in source
    assert "config-changed" in source
    assert "message_type" in source
    assert "event-parameters" in source
    assert "smart_notifications/preview" in source
    assert "data-adopt-device" in source
    assert 'card.type==="smart-notifications-card"' in source
    assert 'customElements.define("smart-notifications-card"' in source
    assert 'getConfigElement()' in source
    assert CARD_RESOURCE_URL.endswith("?v=0.1.0-beta.10")


@pytest.mark.asyncio
async def test_frontend_registration_uses_current_ha_api_and_is_idempotent():
    static = SimpleNamespace(async_register_static_paths=AsyncMock(), register_view=Mock())
    hass = SimpleNamespace(http=static, data={})
    with patch("smart_notifications.frontend.ha_frontend.add_extra_js_url") as add_extra_js_url:
        await async_setup_frontend(hass)
        await async_setup_frontend(hass)
    assert static.async_register_static_paths.await_count == 1
    assert static.register_view.call_count == 4
    add_extra_js_url.assert_called_once_with(hass, CARD_RESOURCE_URL)


@pytest.mark.asyncio
async def test_real_ha_frontend_extra_module_registration():
    # The fixture intentionally omits the separately packaged hass_frontend
    # bundle; exercise the real URL manager and registration helper directly.
    static = SimpleNamespace(async_register_static_paths=AsyncMock(), register_view=Mock())
    runtime = {ha_frontend.DATA_EXTRA_MODULE_URL: ha_frontend.UrlManager(lambda *_: None, [])}
    runtime[DOMAIN] = {}
    isolated_hass = SimpleNamespace(http=static, data=runtime)
    await async_setup_frontend(isolated_hass)
    assert CARD_RESOURCE_URL in runtime[ha_frontend.DATA_EXTRA_MODULE_URL].urls
