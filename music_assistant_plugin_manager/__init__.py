"""music-assistant-plugin-manager — entrypoint-based provider discovery for Music Assistant."""

from __future__ import annotations

from .entrypoints import scan_entrypoints
from .manifest import load_manifest_json


def find_providers() -> dict[str, str]:
    """Return {domain: module_name} for all entrypoint-registered MA providers."""
    return scan_entrypoints()


def load_provider(domain: str):
    """Import and return the provider module for the given domain, or None."""
    import importlib

    ep_map = scan_entrypoints()
    module_name = ep_map.get(domain)
    if module_name is None:
        return None
    return importlib.import_module(module_name)


__all__ = ["find_providers", "load_provider", "load_manifest_json", "scan_entrypoints"]
