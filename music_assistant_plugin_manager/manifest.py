"""Load a ProviderManifest from an installed plugin package."""

from __future__ import annotations

import importlib
import importlib.resources
import json
from pathlib import Path


def load_manifest_json(module_name: str) -> dict:
    """Return the parsed manifest.json for the given plugin module."""
    mod = importlib.import_module(module_name)
    try:
        # Pass the module object — avoids a second import inside resources.files()
        pkg_files = importlib.resources.files(mod)
        manifest_text = (pkg_files / "manifest.json").read_text(encoding="utf-8")
        return json.loads(manifest_text)
    except (FileNotFoundError, TypeError, AttributeError):
        pass
    # Fallback: look next to the module's __init__.py on disk
    if mod.__file__:
        manifest_path = Path(mod.__file__).parent / "manifest.json"
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"manifest.json not found for plugin module '{module_name}'")
