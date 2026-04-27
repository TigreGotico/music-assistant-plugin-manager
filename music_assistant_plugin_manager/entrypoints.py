"""Scan the music_assistant.provider entrypoint group."""

from __future__ import annotations

from importlib.metadata import entry_points

ENTRYPOINT_GROUP = "music_assistant.provider"


def scan_entrypoints() -> dict[str, str]:
    """Return {domain: module_name} for all installed MA provider plugins."""
    result: dict[str, str] = {}
    for ep in entry_points(group=ENTRYPOINT_GROUP):
        # ep.name is the provider domain, ep.value is the module name
        result[ep.name] = ep.value
    return result
