"""Shared message model, validation and Home Assistant template rendering."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.template import Template, TemplateError

MESSAGE_STATIC = "static"
MESSAGE_TEMPLATE = "template"
MESSAGE_PARAMETERS = "parameters"
MESSAGE_COMBINED = "combined"
MESSAGE_TYPES = (MESSAGE_STATIC, MESSAGE_TEMPLATE, MESSAGE_PARAMETERS, MESSAGE_COMBINED)


def infer_message_type(message: str) -> str:
    """Classify legacy text without changing its stored representation."""
    if "{{" in message or "{%" in message or "{#" in message:
        return MESSAGE_TEMPLATE
    return MESSAGE_STATIC


def normalize_parameters(parameters: Any) -> dict[str, dict[str, Any]]:
    """Normalize parameter definitions while retaining only supported fields."""
    if not isinstance(parameters, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for name, definition in parameters.items():
        if not isinstance(name, str) or not name.strip():
            continue
        definition = definition if isinstance(definition, dict) else {}
        parameter_type = str(definition.get("type", "text"))
        if parameter_type not in {"text", "number", "boolean"}:
            parameter_type = "text"
        item = {
            "type": parameter_type,
            "required": bool(definition.get("required", False)),
        }
        if "default" in definition:
            item["default"] = definition["default"]
        normalized[name.strip()] = item
    return normalized


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    """Return a backward-compatible event view with the common message fields."""
    normalized = dict(event)
    message = str(normalized.get("message", ""))
    message_type = normalized.get("message_type") or infer_message_type(message)
    if message_type not in MESSAGE_TYPES:
        message_type = infer_message_type(message)
    normalized["message_type"] = message_type
    normalized["parameters"] = normalize_parameters(normalized.get("parameters"))
    return normalized


def validate_message(hass: HomeAssistant, event: dict[str, Any], variables: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate a message through HA's supported Jinja engine, without rendering delivery."""
    normalized = normalize_event(event)
    message = str(normalized.get("message", ""))
    if not message.strip():
        raise ServiceValidationError("message_missing")
    try:
        template = Template(message, hass)
        template.ensure_valid()
    except TemplateError as err:
        raise ServiceValidationError("template_invalid") from err
    supplied = dict(variables or {})
    definitions = normalized["parameters"]
    missing = [name for name, definition in definitions.items() if definition.get("required") and name not in supplied and "default" not in definition]
    if missing:
        raise ServiceValidationError(f"missing_parameters:{','.join(missing)}")
    for name, definition in definitions.items():
        if name not in supplied and "default" not in definition:
            continue
        value = supplied.get(name, definition.get("default"))
        parameter_type = definition["type"]
        if parameter_type == "number":
            try:
                float(value)
            except (TypeError, ValueError) as err:
                raise ServiceValidationError(f"parameter_invalid:{name}") from err
        elif parameter_type == "boolean" and not isinstance(value, bool):
            raise ServiceValidationError(f"parameter_invalid:{name}")
    return normalized


async def async_render_message(hass: HomeAssistant, event: dict[str, Any], variables: dict[str, Any] | None = None) -> str:
    """Render every message kind through one HA Template pipeline."""
    normalized = validate_message(hass, event, variables)
    render_variables = dict(variables or {})
    for name, definition in normalized["parameters"].items():
        if name not in render_variables and "default" in definition:
            render_variables[name] = definition["default"]
    try:
        rendered = Template(normalized["message"], hass).async_render(
            render_variables, parse_result=False, strict=True
        )
    except (TemplateError, ValueError, TypeError) as err:
        raise ServiceValidationError("template_render_failed") from err
    result = str(rendered).strip()
    if not result:
        raise ServiceValidationError("rendered_message_empty")
    if result in {"unknown", "unavailable"}:
        raise ServiceValidationError("rendered_message_unavailable")
    return result
