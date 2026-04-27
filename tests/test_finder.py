"""Tests for the MassProviderFinder import hook."""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from music_assistant_plugin_manager.finder import MassProviderFinder

EP_MAP = {"demo_provider": "demo_ma_provider", "another": "another_pkg"}


@pytest.fixture
def finder():
    return MassProviderFinder(EP_MAP)


def test_returns_none_for_unrelated_module(finder):
    assert finder.find_spec("os", None) is None
    assert finder.find_spec("music_assistant.mass", None) is None


def test_returns_none_for_unknown_domain(finder):
    assert finder.find_spec("music_assistant.providers.spotify", None) is None


def test_returns_spec_for_known_domain(finder):
    real_spec = MagicMock()
    real_spec.origin = "/some/path.py"
    real_spec.submodule_search_locations = None

    with patch("importlib.util.find_spec", return_value=real_spec):
        spec = finder.find_spec("music_assistant.providers.demo_provider", None)

    assert spec is not None
    assert spec.name == "music_assistant.providers.demo_provider"


def test_returns_none_when_real_module_not_found(finder):
    with patch("importlib.util.find_spec", return_value=None):
        spec = finder.find_spec("music_assistant.providers.demo_provider", None)
    assert spec is None


def test_submodule_redirect(finder):
    real_spec = MagicMock()
    real_spec.origin = "/some/sub.py"
    real_spec.submodule_search_locations = None

    with patch("importlib.util.find_spec", return_value=real_spec) as mock_find:
        finder.find_spec("music_assistant.providers.demo_provider.helpers", None)

    mock_find.assert_called_once_with("demo_ma_provider.helpers")


def test_unknown_submodule_returns_none(finder):
    spec = finder.find_spec("music_assistant.providers.spotify.client", None)
    assert spec is None


def test_loader_exec_module_copies_attributes(finder):
    # Build a fake real module
    real_mod = types.ModuleType("demo_ma_provider")
    real_mod.SUPPORTED_FEATURES = {"search"}
    real_mod.setup = lambda: None

    target_mod = types.ModuleType("music_assistant.providers.demo_provider")

    real_spec = MagicMock()
    real_spec.origin = "/fake.py"
    real_spec.submodule_search_locations = None

    with patch("importlib.util.find_spec", return_value=real_spec):
        spec = finder.find_spec("music_assistant.providers.demo_provider", None)

    with patch("importlib.import_module", return_value=real_mod):
        spec.loader.exec_module(target_mod)

    assert target_mod.SUPPORTED_FEATURES == {"search"}
    assert target_mod.setup is real_mod.setup
