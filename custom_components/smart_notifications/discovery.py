"""Read-only discovery of notification-like automation and script actions."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml
from homeassistant.core import HomeAssistant


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return value[:48] or "notification"


def _walk_actions(node: Any, path: str = "") -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(_walk_actions(item, f"{path}/{index}"))
    elif isinstance(node, dict):
        service = node.get("service") or node.get("action") or node.get("service_template")
        if isinstance(service, str):
            found.append({"service": service, "data": node.get("data", {}), "target": node.get("target", {}), "path": path})
        for key in ("sequence", "then", "else", "default", "actions", "choose", "parallel", "repeat", "if"):
            if key in node:
                found.extend(_walk_actions(node[key], f"{path}/{key}"))
    return found


def _candidate(source_type: str, source_id: str, action: dict[str, Any]) -> dict[str, Any] | None:
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
    key_material = f"{source_type}:{source_id}:{action['path']}:{service}:{message}:{entity_ids}"
    candidate_id = hashlib.sha256(key_material.encode()).hexdigest()[:24]
    suggested = _slug(message or source_id)
    return {
        "candidate_id": candidate_id,
        "source_type": source_type,
        "source_id": source_id,
        "path": action["path"],
        "service": service,
        "message": message,
        "entity_ids": entity_ids,
        "suggested_reason": suggested,
        "confidence": confidence,
    }


def scan_documents(documents: dict[str, Any]) -> list[dict[str, Any]]:
    """Scan already-loaded automation/script documents without side effects."""
    result: list[dict[str, Any]] = []
    for source_type, sources in documents.items():
        if not isinstance(sources, dict):
            continue
        for source_id, document in sources.items():
            actions = document.get("action", document) if isinstance(document, dict) else document
            for action in _walk_actions(actions):
                item = _candidate(source_type, str(source_id), action)
                if item:
                    result.append(item)
    return result


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
