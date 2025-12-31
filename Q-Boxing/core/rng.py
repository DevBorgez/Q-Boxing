from __future__ import annotations

import secrets
from dataclasses import dataclass

from core.math_utils import clamp


def secrets_unit() -> float:
    return secrets.randbits(53) / (2 ** 53)


def secrets_uniform(a: float, b: float) -> float:
    return a + (b - a) * secrets_unit()


def roll(chance: float) -> bool:
    return secrets_unit() < chance


def rand_triangular(a: float, b: float, mode: float) -> float:
    # Triangular with strong entropy (sum of 2 uniforms)
    u = secrets_unit()
    v = secrets_unit()
    t = u + v
    if t < 1:
        return a + (mode - a) * t
    return b - (b - mode) * (2 - t)


def real_random_damage(cfg, lo: float, hi: float, energy: float, distance: float, ideal_dist: float) -> float:
    mode = lo + (hi - lo) * cfg.DMG_MODE_RATIO
    base = rand_triangular(lo, hi, mode)

    e = clamp(energy / 100.0, 0.0, 1.0)
    energy_mult = cfg.ENERGY_MULT_MIN + (cfg.ENERGY_MULT_MAX - cfg.ENERGY_MULT_MIN) * e

    d = abs(distance - ideal_dist)
    proximity_mult = clamp(1.08 - (d / (ideal_dist * 2.2)), cfg.PROX_MULT_MIN, cfg.PROX_MULT_MAX)

    chaos = cfg.CHAOS_MIN + (secrets.randbits(16) / 65535) * (cfg.CHAOS_MAX - cfg.CHAOS_MIN)
    return base * energy_mult * proximity_mult * chaos
