"""
Canonical formation-offset geometry — single source of truth.

All swarm formation logic (SDK ``SwarmAPI``, ``CoordinatorUAVModel`` and the
UI ``SwarmContext``) should derive their (north_m, east_m) offsets from
:func:`formation_offsets` instead of re-implementing the math.

Convention
----------
* Returned tuples are ``(north_m, east_m)`` relative to the leader.
* Followers always trail / surround the leader; the leader's own slot is
  the origin (0, 0) and is **not** included in the returned list.
* ``count`` is the number of *followers* (not including the leader).
* All factors use proper trigonometry (e.g. V uses 60°: cos=0.5, sin=0.866).
"""
from __future__ import annotations

import math
from typing import List, Tuple

Offset = Tuple[float, float]  # (north_m, east_m)

# Canonical shape names — accepted by formation_offsets(). Aliases are
# normalized via :func:`_normalize_shape`.
SHAPES: tuple[str, ...] = ("line", "v", "grid", "circle", "wedge")


def _normalize_shape(shape: str) -> str:
    s = (shape or "").strip().lower()
    aliases = {
        "v-shape":  "v",
        "vshape":   "v",
        "vee":      "v",
    }
    return aliases.get(s, s)


def formation_offsets(shape: str, count: int, spacing: float) -> List[Offset]:
    """Return ``count`` follower offsets (north_m, east_m) for ``shape``.

    Unknown shapes fall back to ``"line"`` (followers trail directly behind).
    """
    if count <= 0 or spacing <= 0:
        return []
    s = _normalize_shape(shape)
    d = float(spacing)

    if s == "v":
        # 60° V: leader at apex, followers fan out behind on both sides.
        offs: List[Offset] = []
        for i in range(count):
            rank = (i // 2) + 1
            side = -1 if (i % 2 == 0) else 1
            offs.append((-rank * d * math.cos(math.radians(30)),
                         side * rank * d * math.sin(math.radians(30))))
        return offs

    if s == "circle":
        # Followers on a ring around the leader. Radius scales with count
        # so adjacent followers stay ~``spacing`` metres apart.
        radius = d * count / (2 * math.pi) if count > 1 else d
        return [
            (radius * math.cos(2 * math.pi * i / count),
             radius * math.sin(2 * math.pi * i / count))
            for i in range(count)
        ]

    if s == "grid":
        cols = max(1, int(math.ceil(math.sqrt(count + 1))))
        offs: List[Offset] = []
        for i in range(count):
            idx = i + 1  # leader occupies slot 0
            r = idx // cols
            c = idx % cols
            offs.append((-r * d, (c - cols / 2.0 + 0.5) * d))
        return offs

    if s == "wedge":
        # Like V but tighter: 0.5 * d on lateral, 0.8 * d on longitudinal.
        offs: List[Offset] = []
        for i in range(count):
            rank = i + 1
            side = -1 if (i % 2 == 0) else 1
            offs.append((-rank * d * 0.8, side * rank * d * 0.5))
        return offs

    # Default / "line": followers trail directly behind the leader.
    return [(-(i + 1) * d, 0.0) for i in range(count)]


__all__ = ["formation_offsets", "SHAPES", "Offset"]
