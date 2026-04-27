"""Apply patches to Music Assistant at process start.

Called explicitly by __main__.py before MA's own startup runs.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys

from .entrypoints import scan_entrypoints
from .finder import MassProviderFinder
from .manifest import load_manifest_json

_logger = logging.getLogger("music_assistant_plugin_manager")
_installed = False


def install() -> None:
    """Patch MA's provider discovery to include entrypoint-registered plugins.

    Idempotent — safe to call multiple times.
    """
    global _installed  # noqa: PLW0603
    if _installed:
        return
    _installed = True

    ep_map = scan_entrypoints()
    if not ep_map:
        _logger.debug("No community providers found via entrypoints.")
        return

    _logger.debug("Community providers found: %s", list(ep_map))

    sys.meta_path.insert(0, MassProviderFinder(ep_map))

    import music_assistant.mass as mass_mod  # noqa: PLC0415
    _apply_manifest_patch(mass_mod, ep_map)


def _apply_manifest_patch(mass_mod, ep_map: dict[str, str]) -> None:
    """Monkey-patch MusicAssistant.__load_provider_manifests to inject community providers."""
    MusicAssistant = mass_mod.MusicAssistant
    mangled = "_MusicAssistant__load_provider_manifests"
    original = getattr(MusicAssistant, mangled, None)
    if original is None or getattr(original, "_mapm_patched", False):
        return

    async def _patched_load_manifests(self):
        await original(self)
        from music_assistant_models.provider import ProviderManifest  # noqa: PLC0415
        for domain, module_name in ep_map.items():
            if domain in self._provider_manifests:
                continue
            try:
                data = load_manifest_json(module_name)
                manifest = ProviderManifest.from_json(json.dumps(data))
                self._provider_manifests[manifest.domain] = manifest
                _logger.debug("Loaded community provider: %s (%s)", manifest.name, manifest.domain)
            except Exception as exc:  # noqa: BLE001
                _logger.warning("Failed to load manifest for '%s': %s", domain, exc)

    _patched_load_manifests._mapm_patched = True
    setattr(MusicAssistant, mangled, _patched_load_manifests)
    _logger.debug("Patched MusicAssistant manifest loader")
