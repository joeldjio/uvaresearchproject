"""
Tests for tools.ui.service_locator.ServiceLocator.

Pure-Python DI container — no Qt needed for the basic API. The
``build_default_locator()`` test does import the actual contexts; if PyQt6
is missing it's skipped.
"""
from __future__ import annotations

import pytest

from tools.ui.service_locator import ServiceLocator


# ── Basic API ───────────────────────────────────────────────────────────────


def test_register_and_get_returns_same_instance():
    loc = ServiceLocator()
    obj = object()
    loc.register("foo", obj)
    assert loc.get("foo") is obj
    # Idempotent
    assert loc.get("foo") is obj


def test_get_missing_key_raises():
    loc = ServiceLocator()
    with pytest.raises(KeyError, match="not registered"):
        loc.get("nope")


def test_has_returns_true_for_instance_and_factory():
    loc = ServiceLocator()
    loc.register("a", object())
    loc.register_factory("b", lambda: object())
    assert loc.has("a")
    assert loc.has("b")
    assert not loc.has("c")


def test_factory_is_lazy():
    """Factory must not run until first .get()."""
    calls = []

    def factory():
        calls.append(1)
        return "instance"

    loc = ServiceLocator()
    loc.register_factory("svc", factory)
    assert calls == []  # not built yet

    out = loc.get("svc")
    assert out == "instance"
    assert calls == [1]


def test_factory_result_is_cached():
    """Calling .get() twice must not re-invoke the factory."""
    counter = {"n": 0}

    def factory():
        counter["n"] += 1
        return object()

    loc = ServiceLocator()
    loc.register_factory("svc", factory)
    a = loc.get("svc")
    b = loc.get("svc")
    assert a is b
    assert counter["n"] == 1


def test_eager_init_instantiates_all_factories():
    built = []
    loc = ServiceLocator()
    loc.register_factory("a", lambda: built.append("a") or "A")
    loc.register_factory("b", lambda: built.append("b") or "B")
    loc.eager_init()
    assert set(built) == {"a", "b"}
    # Subsequent eager_init is a no-op (instances cached)
    loc.eager_init()
    assert set(built) == {"a", "b"}


def test_items_yields_only_instantiated_services():
    loc = ServiceLocator()
    loc.register("eager", "eager_inst")
    loc.register_factory("lazy", lambda: "lazy_inst")

    # Before .get(), 'lazy' is not in items()
    keys_before = {k for k, _ in loc.items()}
    assert keys_before == {"eager"}

    # After .get(), it is
    loc.get("lazy")
    keys_after = {k for k, _ in loc.items()}
    assert keys_after == {"eager", "lazy"}


def test_dunder_getitem_and_contains():
    loc = ServiceLocator()
    loc.register("x", 42)
    assert loc["x"] == 42
    assert "x" in loc
    assert "y" not in loc


def test_register_overrides_previous_instance():
    """Re-registering an instance under the same key replaces it."""
    loc = ServiceLocator()
    loc.register("svc", "first")
    loc.register("svc", "second")
    assert loc.get("svc") == "second"


# ── build_default_locator (integration with real contexts) ──────────────────


def test_build_default_locator_registers_expected_keys(qapp):
    """All five context factories must be registered."""
    pytest.importorskip("PyQt6")
    from tools.ui.service_locator import build_default_locator

    loc = build_default_locator()
    for key in ("swarm", "telemetryModel", "experiment", "safety", "ros2"):
        assert loc.has(key), f"missing service: {key}"


def test_build_default_locator_factories_are_lazy(qapp):
    """No service should be constructed before eager_init()."""
    pytest.importorskip("PyQt6")
    from tools.ui.service_locator import build_default_locator

    loc = build_default_locator()
    # Nothing instantiated yet → items() is empty
    assert list(loc.items()) == []
