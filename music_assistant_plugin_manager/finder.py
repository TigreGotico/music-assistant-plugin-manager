"""importlib meta-path finder that redirects music_assistant.providers.<domain> imports."""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import sys
from types import ModuleType

_PREFIX = "music_assistant.providers."


class MassProviderFinder(importlib.abc.MetaPathFinder):
    """Redirect music_assistant.providers.<domain> to the real plugin module."""

    def __init__(self, entrypoint_map: dict[str, str]) -> None:
        self._map = entrypoint_map  # {domain: module_name}

    def find_spec(self, fullname: str, path, target=None):
        if not fullname.startswith(_PREFIX):
            return None
        domain = fullname[len(_PREFIX):]
        if "." in domain:
            # sub-module of a provider — redirect transparently
            top_domain, rest = domain.split(".", 1)
            if top_domain not in self._map:
                return None
            real_parent = self._map[top_domain]
            real_fullname = f"{real_parent}.{rest}"
        else:
            if domain not in self._map:
                return None
            real_fullname = self._map[domain]

        real_spec = importlib.util.find_spec(real_fullname)
        if real_spec is None:
            return None

        # wrap loader so the module ends up registered under the MA name too
        return importlib.machinery.ModuleSpec(
            fullname,
            _AliasLoader(real_fullname, real_spec),
            origin=real_spec.origin,
            is_package=real_spec.submodule_search_locations is not None,
        )


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, real_fullname: str, real_spec) -> None:
        self._real = real_fullname
        self._real_spec = real_spec

    def create_module(self, spec):
        return None  # use default semantics

    def exec_module(self, module: ModuleType) -> None:
        # load the real module first (or reuse if already cached)
        real = importlib.import_module(self._real)
        # copy all attributes so MA sees a fully-populated module
        module.__dict__.update(
            {k: v for k, v in real.__dict__.items() if k != "__name__"}
        )
        # also register the real module under its original name
        sys.modules.setdefault(self._real, real)
