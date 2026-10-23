import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from smart_notifications.message import async_render_message, normalize_event


@pytest.mark.asyncio
async def test_static_and_entity_template_use_same_render_pipeline(hass: HomeAssistant):
    hass.states.async_set("sensor.bathroom", "21")
    assert await async_render_message(hass, {"message": "Fertig."}) == "Fertig."
    assert await async_render_message(
        hass, {"message": "Im Bad sind {{ states('sensor.bathroom') }} Grad.", "message_type": "template"}
    ) == "Im Bad sind 21 Grad."


@pytest.mark.asyncio
async def test_runtime_parameters_support_required_optional_and_defaults(hass: HomeAssistant):
    event = normalize_event({
        "message": "{{ geraet }}: {{ meldung }} ({{ versuche }} Versuch)",
        "message_type": "parameters",
        "parameters": {
            "geraet": {"type": "text", "required": True},
            "meldung": {"type": "text", "required": True},
            "versuche": {"type": "number", "required": False, "default": 1},
        },
    })
    assert await async_render_message(hass, event, {"geraet": "Waschmaschine", "meldung": "Fertig"}) == "Waschmaschine: Fertig (1 Versuch)"
    with pytest.raises(ServiceValidationError, match="missing_parameters"):
        await async_render_message(hass, event, {"geraet": "Waschmaschine"})
    with pytest.raises(ServiceValidationError, match="parameter_invalid"):
        await async_render_message(hass, event, {"geraet": "Waschmaschine", "meldung": "Fertig", "versuche": "viele"})


@pytest.mark.asyncio
async def test_invalid_template_and_empty_result_are_blocked(hass: HomeAssistant):
    with pytest.raises(ServiceValidationError, match="template_invalid"):
        await async_render_message(hass, {"message": "{{ invalid"})
    with pytest.raises(ServiceValidationError, match="rendered_message_empty"):
        await async_render_message(hass, {"message": "{{ '' }}"})
