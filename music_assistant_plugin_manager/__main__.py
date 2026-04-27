"""Wrapper launcher: apply community-plugin patches then start Music Assistant."""

from __future__ import annotations

import sys


def main() -> int:
    from music_assistant_plugin_manager.bootstrap import install  # noqa: PLC0415
    install()

    from music_assistant.__main__ import main as ma_main  # noqa: PLC0415
    return ma_main()


if __name__ == "__main__":
    sys.exit(main())
