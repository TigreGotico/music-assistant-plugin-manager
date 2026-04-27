"""Tests for entrypoint scanning."""

from unittest.mock import MagicMock, patch

from music_assistant_plugin_manager.entrypoints import ENTRYPOINT_GROUP, scan_entrypoints


def _make_ep(name: str, value: str) -> MagicMock:
    ep = MagicMock()
    ep.name = name
    ep.value = value
    return ep


def test_scan_returns_empty_when_no_plugins():
    with patch("music_assistant_plugin_manager.entrypoints.entry_points", return_value=[]):
        assert scan_entrypoints() == {}


def test_scan_returns_domain_to_module_map():
    eps = [_make_ep("my_provider", "my_provider_module")]
    with patch("music_assistant_plugin_manager.entrypoints.entry_points", return_value=eps):
        result = scan_entrypoints()
    assert result == {"my_provider": "my_provider_module"}


def test_scan_multiple_plugins():
    eps = [
        _make_ep("provider_a", "pkg_a"),
        _make_ep("provider_b", "pkg_b.sub"),
    ]
    with patch("music_assistant_plugin_manager.entrypoints.entry_points", return_value=eps):
        result = scan_entrypoints()
    assert result == {"provider_a": "pkg_a", "provider_b": "pkg_b.sub"}


def test_scan_queries_correct_group():
    with patch("music_assistant_plugin_manager.entrypoints.entry_points", return_value=[]) as mock_ep:
        scan_entrypoints()
    mock_ep.assert_called_once_with(group=ENTRYPOINT_GROUP)
