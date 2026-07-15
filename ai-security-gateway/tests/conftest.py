"""Shared test fixtures and configuration."""

import pytest


@pytest.fixture(autouse=True)
def reset_detector_registry():
    """
    Reset the detector registry before each test to prevent cross-test pollution.
    Tests that need a clean registry (e.g. extensibility proof) benefit from this.
    """
    from detectors import registry
    original = dict(registry.DETECTOR_REGISTRY)
    original_loaded = registry._detectors_loaded
    yield
    registry.DETECTOR_REGISTRY.clear()
    registry.DETECTOR_REGISTRY.update(original)
    registry._detectors_loaded = original_loaded
