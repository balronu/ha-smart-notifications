"""Read-only discovery of notification-like automation and script actions."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from homeassistant.core import HomeAssistant


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return value[:48] or "notification"


def _summarize(value: Any, limit: int = 500) -> Any:
    """Keep source metadata useful without copying arbitrary YAML into storage."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value[:limit] if isinstance(value, str) else value
    if isinstance(value, list):
        return [_summarize(item, limit) for item in value[:12]]
    if isinstance(value, dict):
        return {str(key): _summarize(item, limit) for key, item in list(value.items())[:24]}
    return str(value)[:limit]


def _templates(value: Any) -> list[str]:
    """Find templates in nested action data without evaluating them."""
    if isinstance(value, str):
        return [value] if any(marker in value for marker in ("{{", "{%", "{#")) else []
    if isinstance(value, list):
        return [template for item in value for template in _templates(item)]
    if isinstance(value, dict):
        return [template for item in value.values() for template in _templates(item)]
    return []


def _template_variables(templates: list[str]) -> list[str]:
    names: set[str] = set()
    for template in templates:
        cleaned = re.sub(r"(['\"]).*?\1", "", template)
        names.update(re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", cleaned))
    return sorted(name for name in names if name not in {"states", "state_attr", "is_state", "now", "true", "false", "if", "else", "endif", "float", "int", "default"})


def _walk_actions(node: Any, path: str = "", context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    context = context or {}
    if isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(_walk_actions(item, f"{path}/{index}", context))
    elif isinstance(node, dict):
        service = node.get("service") or node.get("action") or node.get("service_template")
        if isinstance(service, str):
            found.append({"service": service, "data": node.get("data", {}), "target": node.get("target", {}), "path": path, **context})
        next_context = dict(context)
        if "condition" in node or "conditions" in node:
            next_context["conditions"] = _summarize(node.get("condition", node.get("conditions")))
        if "trigger" in node:
            next_context["trigger"] = _summarize(node["trigger"])
        for key in ("sequence", "then", "else", "default", "actions", "choose", "parallel", "repeat", "if"):
            if key in node:
                found.extend(_walk_actions(node[key], f"{path}/{key}", next_context))
    return found


def _candidate(source_type: str, source_id: str, source: dict[str, Any], action: dict[str, Any]) -> dict[str, Any] | None:
    service = action["service"]
    service_lower = service.lower()
    recognized = service_lower in {"tts.speak", "notify.send_message", "smart_notifications.send", "media_player.play_media"} or service_lower.startswith(("notify.mobile_app_", "notify.", "script."))
    if not recognized:
        return None
    data = action.get("data") or {}
    message = data.get("message") or data.get("title") or ""
    targets = action.get("target") or {}
    entity_ids = targets.get("entity_id", []) if isinstance(targets, dict) else []
    if isinstance(entity_ids, str):
        entity_ids = [entity_ids]
    confidence = "high" if service_lower in {"tts.speak", "notify.send_message", "smart_notifications.send"} and message else "possible"
    output_type = "tts" if service_lower == "tts.speak" else "push" if service_lower.startswith("notify.") else "music_assistant" if "music_assistant" in service_lower else "other"
    templates = _templates(data)
    source_name = source.get("alias") or source.get("name")
    display_name = source_name or f"Technische {source_type}-ID: {source_id}"
    grouping_material = json.dumps([source_type, source_id, message, action.get("conditions"), action.get("trigger")], sort_keys=True, default=str)
    group_id = hashlib.sha256(grouping_material.encode()).hexdigest()[:24]
    key_material = f"{source_type}:{source_id}:{action['path']}:{service}:{message}:{entity_ids}"
    candidate_id = hashlib.sha256(key_material.encode()).hexdigest()[:24]
    suggested = _slug(source.get("alias") or source.get("name") or source_id)
    return {
        "candidate_id": candidate_id,
        "source_type": source_type,
        "source_id": source_id,
        "source_name": display_name,
        "source_name_quality": "configured" if source_name else "technical_fallback",
        "path": action["path"],
        "service": service,
        "output_type": output_type,
        "output_target": service.removeprefix("notify.mobile_app_") if service_lower.startswith("notify.mobile_app_") else None,
        "message": message,
        "message_is_template": bool(templates),
        "templates": templates,
        "template_variables": _template_variables(templates),
        "unresolved_variables": _template_variables(templates),
        "message_type": "template" if templates else "static",
        "entity_ids": entity_ids,
        "suggested_reason": suggested,
        "confidence": confidence,
        "trigger": action.get("trigger"),
        "conditions": action.get("conditions"),
        "group_id": group_id,
        "last_seen": datetime.now(UTC).isoformat(),
    }


def scan_documents(documents: dict[str, Any]) -> list[dict[str, Any]]:
    """Scan already-loaded automation/script documents without side effects."""
    result: list[dict[str, Any]] = []
    for source_type, sources in documents.items():
        if not isinstance(sources, dict):
            continue
        for source_id, document in sources.items():
            actions = document.get("action", document) if isinstance(document, dict) else document
            source_context = {}
            if isinstance(document, dict):
                if "trigger" in document:
                    source_context["trigger"] = _summarize(document["trigger"])
                if "condition" in document or "conditions" in document:
                    source_context["conditions"] = _summarize(document.get("condition", document.get("conditions")))
            for action in _walk_actions(actions, context=source_context):
                item = _candidate(source_type, str(source_id), document if isinstance(document, dict) else {}, action)
                if item:
                    result.append(item)
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in result:
        groups.setdefault(item["group_id"], []).append(item)
    for members in groups.values():
        member_targets = sorted({target for member in members for target in member.get("entity_ids", []) if target})
        member_targets.extend(sorted({member["output_target"] for member in members if member.get("output_target")}))
        services = sorted({member["service"] for member in members})
        for item in members:
            item["group_size"] = len(members)
            item["group_members"] = [member["candidate_id"] for member in members]
            item["grouped_targets"] = sorted(set(member_targets))
            item["grouped_services"] = services
            item["grouping_note"] = "Gleiche Quelle, Nachricht und erkannter Anlass" if len(members) > 1 else "Einzelne Ausgabe; keine automatische Zusammenfassung"
    return result


def candidate_display_name(candidate: dict[str, Any]) -> str:
    """Return a safe user-facing name, never an invented automation title."""
    return str(candidate.get("source_name") or f"Technische ID: {candidate.get('source_id', '')}")


def apply_candidate_action(
    config: dict[str, Any], candidate_id: str, action: str, edits: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Apply discovery state or create a disabled event; shared by flow and API."""
    candidates = config.get("discovery", {}).get("candidates", {})
    candidate = candidates.get(candidate_id)
    if not candidate:
        return None
    group_id = candidate.get("group_id")
    grouped = [candidate] if not group_id else [item for item in candidates.values() if item.get("group_id") == group_id]
    if action == "ignore":
        for item in grouped:
            item["status"] = "ignored"
    elif action == "review":
        for item in grouped:
            item["status"] = "review"
    elif action == "adopt":
        edits = edits or {}
        reason = str(edits.get("reason") or candidate.get("suggested_reason") or "notification").strip().lower()
        reason = re.sub(r"[^a-z0-9_]+", "_", reason).strip("_") or "notification"
        base_name = str(edits.get("name") or candidate_display_name(candidate))
        config["events"].setdefault(reason, {
            "name": base_name,
            "message": str(edits.get("message", candidate.get("message", ""))),
            "message_type": str(edits.get("message_type", candidate.get("message_type", "static"))),
            "parameters": edits.get("parameters", {name: {"type": "text", "required": True} for name in candidate.get("template_variables", [])}),
            "enabled": False,
            "priority": str(edits.get("priority") or "normal"),
            "description": "Aus Discovery übernommen; ursprüngliche Quelle bleibt unverändert.",
        })
        if edits.get("devices") is not None:
            config["routes"][reason] = list(edits["devices"])
        for item in grouped:
            item["status"] = "adopted"
            item["adopted_reason"] = reason
    else:
        raise ValueError(f"unsupported discovery action: {action}")
    return candidate


def _read_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None


async def async_scan(hass: HomeAssistant, previous: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Read configured YAML sources in an executor and classify candidates."""
    root = Path(hass.config.path())
    automation_data, script_data = await hass.async_add_executor_job(
        lambda: (_read_yaml(root / "automations.yaml"), _read_yaml(root / "scripts.yaml"))
    )
    documents = {
        "automation": {
            str(item.get("id") or item.get("alias") or index): item
            for index, item in enumerate(automation_data or [])
            if isinstance(item, dict)
        },
        "script": script_data or {},
    }
    old = (previous or {}).get("candidates", {})
    results = []
    for item in scan_documents(documents):
        prior = old.get(item["candidate_id"], {})
        item["status"] = "unchanged" if prior else "new"
        if prior and any(prior.get(key) != item.get(key) for key in ("message", "service", "entity_ids")):
            item["status"] = "changed"
        if prior.get("status") in {"adopted", "ignored"}:
            item["status"] = prior["status"]
        results.append(item)
    seen = {item["candidate_id"] for item in results}
    for candidate_id, prior in old.items():
        if candidate_id in seen or not isinstance(prior, dict):
            continue
        missing = dict(prior)
        missing["candidate_id"] = candidate_id
        if missing.get("status") not in {"adopted", "ignored"}:
            missing["status"] = "not_found"
        results.append(missing)
    return results
