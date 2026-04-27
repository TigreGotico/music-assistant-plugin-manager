"""Tests for the __main__ wrapper launcher."""

import sys
import types
from unittest.mock import patch

from music_assistant_plugin_manager.__main__ import main


def _ma_main_sys_modules(return_code: int = 0) -> dict:
    ma_pkg = types.ModuleType("music_assistant")
    ma_main = types.ModuleType("music_assistant.__main__")
    ma_main.main = lambda: return_code
    ma_pkg.__main__ = ma_main
    return {"music_assistant": ma_pkg, "music_assistant.__main__": ma_main}


def test_main_calls_install():
    with patch("music_assistant_plugin_manager.bootstrap.install") as mock_install, \
         patch.dict("sys.modules", _ma_main_sys_modules()):
        main()
    mock_install.assert_called_once()


def test_main_returns_ma_exit_code():
    with patch("music_assistant_plugin_manager.bootstrap.install"), \
         patch.dict("sys.modules", _ma_main_sys_modules(return_code=42)):
        assert main() == 42


def test_main_zero_exit_on_success():
    with patch("music_assistant_plugin_manager.bootstrap.install"), \
         patch.dict("sys.modules", _ma_main_sys_modules(return_code=0)):
        assert main() == 0
