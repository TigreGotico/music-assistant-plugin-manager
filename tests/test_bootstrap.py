"""Tests for the bootstrap install() function and manifest patch."""

import asyncio
import importlib
import json
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import music_assistant_plugin_manager.bootstrap as bootstrap_mod
from music_assistant_plugin_manager.bootstrap import _apply_manifest_patch
from music_assistant_plugin_manager.finder import MassProviderFinder


@pytest.fixture(autouse=True)
def reset_installed():
    original = bootstrap_mod._installed
    bootstrap_mod._installed = False
    yield
    bootstrap_mod._installed = original


@pytest.fixture(autouse=True)
def clean_meta_path():
    original = sys.meta_path[:]
    yield
    sys.meta_path[:] = [f for f in original if not isinstance(f, MassProviderFinder)]


def _fake_mass_sys_modules():
    """Return a sys.modules patch dict that satisfies `import music_assistant.mass`."""
    ma_pkg = types.ModuleType("music_assistant")
    mass_mod = _make_mass_mod()
    ma_pkg.mass = mass_mod
    return {"music_assistant": ma_pkg, "music_assistant.mass": mass_mod}


# --- install() ---

def test_install_is_idempotent():
    ep_map = {"prov": "pkg"}
    with patch.object(bootstrap_mod, "scan_entrypoints", return_value=ep_map), \
         patch.object(bootstrap_mod, "_apply_manifest_patch") as mock_patch, \
         patch.object(bootstrap_mod, "MassProviderFinder", return_value=MagicMock()), \
         patch.dict("sys.modules", _fake_mass_sys_modules()):
        bootstrap_mod.install()
        bootstrap_mod._installed = False  # force second call through
        bootstrap_mod._installed = True   # but idempotent guard should block it
        bootstrap_mod.install()

    assert mock_patch.call_count == 1


def test_install_skips_when_no_entrypoints():
    with patch.object(bootstrap_mod, "scan_entrypoints", return_value={}), \
         patch.object(bootstrap_mod, "_apply_manifest_patch") as mock_patch:
        bootstrap_mod.install()
    mock_patch.assert_not_called()


def test_install_registers_finder_in_meta_path():
    ep_map = {"prov": "pkg"}
    with patch.object(bootstrap_mod, "scan_entrypoints", return_value=ep_map), \
         patch.object(bootstrap_mod, "_apply_manifest_patch"), \
         patch.dict("sys.modules", _fake_mass_sys_modules()):
        bootstrap_mod.install()

    finders = [f for f in sys.meta_path if isinstance(f, MassProviderFinder)]
    assert len(finders) == 1


# --- _apply_manifest_patch() ---

def _make_mass_mod(original_coro=None):
    if original_coro is None:
        async def _original(self):
            self._provider_manifests["builtin"] = "builtin_manifest"
        original_coro = _original

    class FakeMusicAssistant:
        _MusicAssistant__load_provider_manifests = original_coro

    mod = types.ModuleType("music_assistant.mass")
    mod.MusicAssistant = FakeMusicAssistant
    return mod


def _fake_provider_manifest(domain: str, name: str) -> MagicMock:
    m = MagicMock()
    m.domain = domain
    m.name = name
    return m


def _make_ma_models_patch(manifest: MagicMock):
    """Return sys.modules entries that satisfy `from music_assistant_models.provider import ProviderManifest`."""
    models_pkg = types.ModuleType("music_assistant_models")
    provider_mod = types.ModuleType("music_assistant_models.provider")
    provider_mod.ProviderManifest = MagicMock(from_json=MagicMock(return_value=manifest))
    models_pkg.provider = provider_mod
    return {
        "music_assistant_models": models_pkg,
        "music_assistant_models.provider": provider_mod,
    }


def test_apply_patch_replaces_method():
    mass_mod = _make_mass_mod()
    original = mass_mod.MusicAssistant._MusicAssistant__load_provider_manifests

    _apply_manifest_patch(mass_mod, {})

    patched = mass_mod.MusicAssistant._MusicAssistant__load_provider_manifests
    assert patched is not original
    assert patched._mapm_patched is True


def test_apply_patch_is_idempotent():
    mass_mod = _make_mass_mod()
    _apply_manifest_patch(mass_mod, {})
    first = mass_mod.MusicAssistant._MusicAssistant__load_provider_manifests
    _apply_manifest_patch(mass_mod, {})
    second = mass_mod.MusicAssistant._MusicAssistant__load_provider_manifests
    assert first is second


def test_patched_method_injects_community_manifests():
    mass_mod = _make_mass_mod()
    ep_map = {"demo_provider": "demo_ma_provider"}
    manifest_data = {"type": "music", "domain": "demo_provider", "name": "Demo"}
    fake_manifest = _fake_provider_manifest("demo_provider", "Demo")

    instance = MagicMock()
    instance._provider_manifests = {}

    # Keep both patches active during the async call — the closure reads globals at call time
    with patch.object(bootstrap_mod, "load_manifest_json", return_value=manifest_data), \
         patch.dict("sys.modules", _make_ma_models_patch(fake_manifest)):
        _apply_manifest_patch(mass_mod, ep_map)
        asyncio.run(
            mass_mod.MusicAssistant._MusicAssistant__load_provider_manifests(instance)
        )

    assert "demo_provider" in instance._provider_manifests
    assert instance._provider_manifests["demo_provider"] is fake_manifest


def test_patched_method_does_not_override_builtins():
    """Community provider must not replace a domain already loaded by the original method."""
    # The original coro writes "builtin" → "builtin_manifest" into _provider_manifests.
    # A community provider also claims domain "builtin"; the patch must leave the original value.
    mass_mod = _make_mass_mod()
    ep_map = {"builtin": "some_pkg"}
    impostor = _fake_provider_manifest("builtin", "Impostor")

    instance = MagicMock()
    instance._provider_manifests = {}

    with patch.object(bootstrap_mod, "load_manifest_json", return_value={}), \
         patch.dict("sys.modules", _make_ma_models_patch(impostor)):
        _apply_manifest_patch(mass_mod, ep_map)
        asyncio.run(
            mass_mod.MusicAssistant._MusicAssistant__load_provider_manifests(instance)
        )

    # Original wrote "builtin_manifest"; community impostor must not have replaced it
    assert instance._provider_manifests["builtin"] == "builtin_manifest"


def test_patched_method_skips_on_bad_manifest():
    mass_mod = _make_mass_mod()
    ep_map = {"broken": "broken_pkg"}

    with patch.object(bootstrap_mod, "load_manifest_json", side_effect=FileNotFoundError("no manifest")):
        _apply_manifest_patch(mass_mod, ep_map)

    instance = MagicMock()
    instance._provider_manifests = {}

    with patch.dict("sys.modules", _make_ma_models_patch(MagicMock())):
        asyncio.run(
            mass_mod.MusicAssistant._MusicAssistant__load_provider_manifests(instance)
        )

    assert "broken" not in instance._provider_manifests
