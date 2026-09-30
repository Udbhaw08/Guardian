"""
detectors/registry.py
---------------------
Self-registration system for detectors.

HOW IT WORKS
------------
1. Each detector module decorates its class with @register("detector_name").
2. The decorator instantiates the class and stores it in DETECTOR_REGISTRY.
3. scanner.py calls load_all_detectors() once at startup, which imports every
   module in the detectors/ package (except base and registry themselves).
4. Because each import triggers the module-level @register call, the registry
   is fully populated with zero explicit imports in scanner.py.

ADDING A NEW DETECTOR
---------------------
1. Create detectors/my_new_detector.py
2. Subclass BaseDetector, implement detect(), decorate with @register("my_new_detector")
3. That's it — zero edits to scanner.py, registry.py, or any other file.

ARCHITECTURAL CONSTRAINT: No MCP, SSE, OAuth, or Starlette types here.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from detectors.base import BaseDetector

# The global registry: detector_name -> instantiated detector object
DETECTOR_REGISTRY: dict[str, "BaseDetector"] = {}

# Track whether we've already done the one-time auto-import
_detectors_loaded: bool = False

# Modules in this package that are NOT detectors.
# This includes helper/internal modules called from prompt_injection.py
# that should NOT be auto-registered as standalone detectors.
_EXCLUDED_MODULES: frozenset[str] = frozenset({
    "base",
    "registry",
    "injection_rules",   # pipeline helper — rule signal contributions
    "verifier",          # pipeline helper — context intent verifier
    "aggregator",        # pipeline helper — confidence aggregator
})


def register(name: str):
    """
    Class decorator that registers a detector under *name* in DETECTOR_REGISTRY.

    Usage:
        @register("api_key")
        class ApiKeyDetector(BaseDetector):
            ...
    """
    def decorator(cls):
        instance = cls()
        if name in DETECTOR_REGISTRY:
            raise ValueError(
                f"Detector '{name}' is already registered. "
                f"Each detector must have a unique name."
            )
        DETECTOR_REGISTRY[name] = instance
        return cls

    return decorator


def load_all_detectors() -> None:
    """
    Import every module in the detectors/ package (excluding base and registry).

    Idempotent — safe to call multiple times; subsequent calls are no-ops.
    The side effect of each import is that each module's @register decorator
    fires, populating DETECTOR_REGISTRY automatically.
    """
    global _detectors_loaded
    if _detectors_loaded:
        return

    import detectors as _pkg  # noqa: PLC0415 — intentional late import

    for _finder, module_name, _ispkg in pkgutil.iter_modules(_pkg.__path__):
        if module_name not in _EXCLUDED_MODULES:
            importlib.import_module(f"detectors.{module_name}")

    _detectors_loaded = True


def get_registered_detectors() -> dict[str, "BaseDetector"]:
    """
    Return the current contents of DETECTOR_REGISTRY.

    Callers should call load_all_detectors() first to ensure all detectors
    are present (scanner.py does this automatically).
    """
    return dict(DETECTOR_REGISTRY)
