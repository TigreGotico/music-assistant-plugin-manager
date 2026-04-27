"""Tests for manifest loading."""

import importlib
import importlib.resources
import json
import types
from unittest.mock import MagicMock, patch

import pytest

from music_assistant_plugin_manager.manifest import load_manifest_json


def _make_module(tmp_path) -> types.ModuleType:
    mod = types.ModuleType("fake_module")
    mod.__file__ = str(tmp_path / "__init__.py")
    mod.__spec__ = MagicMock()
    mod.__spec__.submodule_search_locations = [str(tmp_path)]
    return mod


def test_load_via_importlib_resources(tmp_path):
    data = {"type": "music", "domain": "test_provider", "name": "Test"}
    mod = _make_module(tmp_path)

    fake_path = MagicMock()
    fake_path.read_text.return_value = json.dumps(data)
    fake_files = MagicMock()
    fake_files.__truediv__ = MagicMock(return_value=fake_path)

    with patch.object(importlib, "import_module", return_value=mod), \
         patch.object(importlib.resources, "files", return_value=fake_files):
        result = load_manifest_json("fake_module")

    assert result == data


def test_load_fallback_to_file_path(tmp_path):
    data = {"type": "music", "domain": "fallback_provider", "name": "Fallback"}
    (tmp_path / "manifest.json").write_text(json.dumps(data))
    mod = _make_module(tmp_path)

    with patch.object(importlib, "import_module", return_value=mod), \
         patch.object(importlib.resources, "files", side_effect=TypeError("no resources")):
        result = load_manifest_json("fake_module")

    assert result == data


def test_raises_when_manifest_missing(tmp_path):
    mod = _make_module(tmp_path)
    # No manifest.json in tmp_path

    with patch.object(importlib, "import_module", return_value=mod), \
         patch.object(importlib.resources, "files", side_effect=TypeError("no resources")):
        with pytest.raises(FileNotFoundError):
            load_manifest_json("fake_module")
