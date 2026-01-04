from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CFG:
    WIDTH: int = 800
    HEIGHT: int = 600
    FPS: int = 90

    MAX_ROUNDS: int = 12
    ROUND_TIME_SEC: int = 60
    BETWEEN_ROUND_MS: int = 1400

    BG: tuple[int, int, int] = (25, 25, 25)
    HUD_BG: tuple[int, int, int] = (16, 16, 18)
    HUD_FG: tuple[int, int, int] = (235, 235, 235)

    # Fighter
    HEAD_SIZE: int = 110
    MAX_LIFE: float = 200.0
    MAX_ENERGY: float = 100.0
    SPEED: float = 4.15

    # Punch
    ARM_RETRACT: float = 28.0
    ARM_SHORT: float = 82.0
    ARM_MED: float = 105.0
    ARM_LONG: float = 132.0
    ARM_WIDTH: int = 40

    PUNCH_FRAMES: int = 10
    CD_SHORT: int = 42
    CD_MED: int = 68
    CD_LONG: int = 86

    COST_SHORT: float = 20.0
    COST_MED: float = 30.0
    COST_LONG: float = 50.0

    # Same-side vulnerability counter
    COUNTER_DAMAGE_BONUS: float = 0.25
    COUNTER_ARM_LOCK_FRAMES: int = 14
    R_COUNTER: float = 3.5                      # extra reward for exploiting the vulnerability
    R_COUNTERED: float = -3.5                   # extra penalty for being countered (on top of dmg_taken)

    # Dodge / Counter attack after real dodge
    DODGE_FRAMES: int = 14
    DODGE_CD: int = 90 * 2
    DODGE_COST: float = 24.0
    DODGE_SPEED_MULT: float = 2.1
    DODGE_EVADE_PROB: float = 0.75

    COUNTER_WINDOW_FRAMES: int = 36
    COUNTER_ATTACK_MULT: float = 1.50

    # message duration for dodge event
    DODGE_MSG_MS: int = 900

    # Regen
    REGEN_IDLE: float = 0.55
    REGEN_MOVE: float = 0.20

    # Q-learning actions (side-aware)
    ACTIONS: tuple[str, ...] = (
        "move_up", "move_down", "move_left", "move_right",
        "punch_short_L", "punch_short_R",
        "punch_medium_L", "punch_medium_R",
        "punch_long_L", "punch_long_R",
        "dodge", "do_nothing",
    )

    # State discretization
    DIST_BINS: int = 10
    DXDY_BINS: int = 9
    ENERGY_BINS: int = 6
    CD_BINS: int = 4
    TIME_BINS: int = 4
    # bits: punch_ready, dodge_ready, counter_window_active, low_energy, any_arm_locked
    BOOL_BITS: int = 5

    # Q-learning hyperparams
    ALPHA: float = 0.13
    GAMMA: float = 0.92
    EPSILON_START: float = 0.26
    EPSILON_MIN: float = 0.06
    EPSILON_DECAY: float = 0.99955

    # Rewards
    R_BASE: float = -0.06
    R_DAMAGE: float = 1.15
    R_TAKEN: float = 1.30
    R_CLOSE: float = 0.085
    R_FAR_PUNCH_MISS: float = -1.05
    R_IDLE_FAR: float = -0.12
    R_FAR_STEP: float = -0.10
    R_LOW_ENERGY_WASTE: float = -0.12

    R_SAMESIDE_COUNTER: float = 3.5
    R_GOT_SAMESIDE_COUNTERED: float = -3.5

    R_REAL_DODGE: float = 2.2
    R_GOT_REAL_DODGED: float = -2.2

    R_COUNTER_ATTACK_HIT: float = 4.0

    R_WIN: float = 70.0
    R_LOSE: float = -70.0

    # Engage
    ENGAGE_DIST: float = 360.0
    ENGAGE_FORCE: float = 0.58
    ENGAGE_OPENING_SEC: float = 2.0
    ENGAGE_OPENING_FORCE: float = 0.95

    # Carry
    CARRY_DAMAGE_PER_LOSS: float = 18.0
    MIN_START_LIFE: float = 70.0

    # Decals
    DECAL_LIFETIME_MS: int = 12000
    DECAL_FADE_MS: int = 2500
    MAX_DECALS: int = 450

    # Trail
    TRAIL_DURATION_MS: int = 2400
    TRAIL_DROP_EVERY_MS: int = 80
    TRAIL_DROP_MIN_DIST: float = 14.0
    TRAIL_BACK_OFFSET: float = 18.0

    # Damage ranges
    DMG_SHORT_MIN: float = 5.0
    DMG_SHORT_MAX: float = 18.0
    DMG_MED_MIN: float = 9.0
    DMG_MED_MAX: float = 28.0
    DMG_LONG_MIN: float = 14.0
    DMG_LONG_MAX: float = 40.0

    IDEAL_DIST_SHORT: float = 95.0
    IDEAL_DIST_MED: float = 115.0
    IDEAL_DIST_LONG: float = 140.0

    DMG_MODE_RATIO: float = 0.55
    ENERGY_MULT_MIN: float = 0.82
    ENERGY_MULT_MAX: float = 1.18
    PROX_MULT_MIN: float = 0.90
    PROX_MULT_MAX: float = 1.32
    CHAOS_MIN: float = 0.96
    CHAOS_MAX: float = 1.06

    # Super Punch
    SUPER_PUNCH_CHANCE: float = 0.012
    SUPER_PUNCH_DMG_MIN: float = 160.0
    SUPER_PUNCH_DMG_MAX: float = 180.0
    SUPER_PUNCH_MSG_MS: int = 900
    SUPER_PUNCH_GOLD: tuple[int, int, int] = (255, 205, 90)

    # Knockout Punch (ends match immediately)
    KNOCKOUT_PUNCH_CHANCE: float = 0.001
    KNOCKOUT_PUNCH_MSG_MS: int = 1200

    # Spacing / hit geometry
    BODY_GAP_PX: float = 14.0
    PUNCH_CONTACT_GAP_PX: float = 3.0
    HIT_RADIUS_MULT: float = 0.92

    # Gloves (from .env)
    RED_GLOVE_L_PATH: str | None = field(default_factory=lambda: os.environ.get("LEFT_RED_GLOVE"))
    RED_GLOVE_R_PATH: str | None = field(default_factory=lambda: os.environ.get("RIGHT_RED_GLOVE"))
    BLUE_GLOVE_L_PATH: str | None = field(default_factory=lambda: os.environ.get("LEFT_BLUE_GLOVE"))
    BLUE_GLOVE_R_PATH: str | None = field(default_factory=lambda: os.environ.get("RIGHT_BLUE_GLOVE"))

    GLOVE_SCALE_RED: float = 0.11
    GLOVE_SCALE_BLUE: float = 0.11

    GLOVE_PIVOT_X_FRAC: float = 0.0
    GLOVE_PIVOT_Y_FRAC: float = 0.01
    GLOVE_FORWARD_PUSH_PX: float = 10.0

    GLOVE_BASE_ROT_DEG: float = 90.0
    GLOVE_CACHE_STEP_DEG: int = 6
