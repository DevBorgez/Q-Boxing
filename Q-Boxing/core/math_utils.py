from __future__ import annotations

import math
from typing import Tuple


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def sign3(x: float) -> int:
    if x > 12:
        return 1
    if x < -12:
        return -1
    return 0


def dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def closest_point_on_segment(ax: float, ay: float, bx: float, by: float, px: float, py: float) -> Tuple[float, float]:
    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay
    ab_len2 = abx * abx + aby * aby
    if ab_len2 <= 1e-9:
        return ax, ay
    t = (apx * abx + apy * aby) / ab_len2
    t = clamp(t, 0.0, 1.0)
    return ax + t * abx, ay + t * aby


def segment_circle_hit(ax: float, ay: float, bx: float, by: float, cx: float, cy: float, r: float) -> bool:
    px, py = closest_point_on_segment(ax, ay, bx, by, cx, cy)
    dx = cx - px
    dy = cy - py
    return (dx * dx + dy * dy) <= (r * r)


def rotate_vec(vx: float, vy: float, angle_deg: float) -> tuple[float, float]:
    # rotation in screen coordinates (compatible with pygame.transform.rotate)
    rad = math.radians(angle_deg)
    cosr = math.cos(rad)
    sinr = math.sin(rad)
    return (vx * cosr - vy * sinr, vx * sinr + vy * cosr)
