import pytest
from homeassistant import loader

pytest_plugins = ("pytest_homeassistant_custom_component",)


@pytest.fixture
def integration_frame_path() -> str:
    return "custom_components/smart_notifications"


@pytest.fixture(autouse=True)
def load_local_integration(hass):
    """Make the repository custom component visible to the HA fixture."""
    hass.data.pop(loader.DATA_CUSTOM_COMPONENTS, None)
    hass.data[loader.DATA_CUSTOM_COMPONENTS] = loader._get_custom_components(hass)
