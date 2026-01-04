from __future__ import annotations

import math
import random
from typing import Dict, Tuple

import numpy as np
import pygame

from core.math_utils import clamp, sign3, rotate_vec
from fx.decals import GroundDecal


class Character:
    def __init__(
        self,
        cfg,
        x,
        y,
        color,
        arm_color,
        name,
        head_image,
        ko_image,
        impacts,
        snd_light,
        snd_mid,
        snd_heavy,
        glove_left_img,
        glove_right_img,
    ):
        self.cfg = cfg
        self.name = name
        self.color = color
        self.arm_color = arm_color

        self.x = float(x)
        self.y = float(y)
        self.initial_x = float(x)
        self.initial_y = float(y)

        self.head_size = cfg.HEAD_SIZE
        self.radius = cfg.HEAD_SIZE / 2.0

        self.head_image = head_image
        self.ko_image = ko_image

        self.life = float(cfg.MAX_LIFE)
        self.max_life = float(cfg.MAX_LIFE)
        self.energy = float(cfg.MAX_ENERGY)
        self.max_energy = float(cfg.MAX_ENERGY)

        self.facing_direction = 0.0
        self.facing_when_ko = 0.0

        # arms
        self.arm_width = cfg.ARM_WIDTH
        self.arm_len_left = cfg.ARM_RETRACT
        self.arm_len_right = cfg.ARM_RETRACT
        self.punch_timer_left = 0
        self.punch_timer_right = 0
        self.punch_cd = 0

        # arm lock (used by "same side" vulnerability / counter)
        self.arm_lock_left = 0
        self.arm_lock_right = 0

        # dodge
        self.dodge_cd = 0
        self.dodge_timer = 0

        # áudio/fx
        self.sound_cd = 0
        self.impacts = impacts
        self.snd_light = snd_light
        self.snd_mid = snd_mid
        self.snd_heavy = snd_heavy

        # knockout
        self.knocked_out = False
        self.knockout_vulnerability = 0.001

        # Q-learning
        self.epsilon = cfg.EPSILON_START
        self.action_idx = 0
        self.n_states = self._calc_n_states()
        self.q_table = np.zeros((self.n_states, len(cfg.ACTIONS)), dtype=np.float32)

        # round flags
        self.round_lost = False
        self.carry_damage = 0.0

        # trail
        self.trail_until_ms = 0
        self.trail_next_drop_ms = 0
        self.last_trail_drop_pos = (self.x, self.y)
        self.prev_x = self.x
        self.prev_y = self.y

        # gloves
        self.glove_left_img = glove_left_img
        self.glove_right_img = glove_right_img

        self.counter_window = 0

        # cache: rotated surfaces keyed by (id(surface), quant_angle_deg)
        self._rot_cache: Dict[Tuple[int, int], pygame.Surface] = {}

    # ============================================================
    # State
    # ============================================================
    def _calc_n_states(self) -> int:
        c = self.cfg
        base = (c.DIST_BINS * c.DXDY_BINS * c.ENERGY_BINS * c.ENERGY_BINS * c.CD_BINS * c.TIME_BINS)
        bools = 2 ** c.BOOL_BITS
        return base * bools

    def get_state(self, opponent, time_left: int) -> int:
        c = self.cfg
        dx = opponent.x - self.x
        dy = opponent.y - self.y

        d = math.hypot(dx, dy)
        max_d = math.hypot(c.WIDTH, c.HEIGHT)
        dist_bin = int((d / max_d) * (c.DIST_BINS - 1))
        dist_bin = int(clamp(dist_bin, 0, c.DIST_BINS - 1))

        sx = sign3(dx) + 1
        sy = sign3(dy) + 1
        dxdy_bin = int(sy * 3 + sx)

        e_bin = int((self.energy / self.max_energy) * (c.ENERGY_BINS - 1))
        oe_bin = int((opponent.energy / opponent.max_energy) * (c.ENERGY_BINS - 1))
        e_bin = int(clamp(e_bin, 0, c.ENERGY_BINS - 1))
        oe_bin = int(clamp(oe_bin, 0, c.ENERGY_BINS - 1))

        if self.punch_cd == 0:
            cd_bin = 0
        elif self.punch_cd < 25:
            cd_bin = 1
        elif self.punch_cd < 55:
            cd_bin = 2
        else:
            cd_bin = 3

        tl = int(clamp(time_left, 0, c.ROUND_TIME_SEC))
        frac = tl / c.ROUND_TIME_SEC
        if frac > 0.75:
            t_bin = 0
        elif frac > 0.50:
            t_bin = 1
        elif frac > 0.25:
            t_bin = 2
        else:
            t_bin = 3

        punch_ready = 1 if self.punch_cd == 0 else 0
        dodge_ready = 1 if self.dodge_cd == 0 else 0
        counter_ready = 1 if self.counter_window > 0 else 0
        low_energy = 1 if self.energy < 18 else 0
        any_arm_locked = 1 if (self.arm_lock_left > 0 or self.arm_lock_right > 0) else 0

        b = (punch_ready << 4) | (dodge_ready << 3) | (counter_ready << 2) | (low_energy << 1) | (any_arm_locked << 0)

        idx = dist_bin
        idx = idx * c.DXDY_BINS + dxdy_bin
        idx = idx * c.ENERGY_BINS + e_bin
        idx = idx * c.ENERGY_BINS + oe_bin
        idx = idx * c.CD_BINS + cd_bin
        idx = idx * c.TIME_BINS + t_bin
        idx = idx * (2 ** c.BOOL_BITS) + b
        return int(idx)

    # ============================================================
    # Q-learning helpers
    # ============================================================
    def choose_action(self, state_idx: int) -> int:
        if random.random() < self.epsilon:
            return random.randint(0, len(self.cfg.ACTIONS) - 1)
        return int(np.argmax(self.q_table[state_idx]))

    def decay_epsilon(self):
        self.epsilon = max(self.cfg.EPSILON_MIN, self.epsilon * self.cfg.EPSILON_DECAY)

    # ============================================================
    # Movement / Timers
    # ============================================================
    def update_facing(self, opponent):
        dx = opponent.x - self.x
        dy = opponent.y - self.y
        self.facing_direction = math.atan2(dy, dx)

    def clamp_inside(self):
        half = self.radius
        self.x = clamp(self.x, half, self.cfg.WIDTH - half)
        self.y = clamp(self.y, half, self.cfg.HEIGHT - half)

    def tick_timers(self):
        c = self.cfg
        if self.punch_cd > 0:
            self.punch_cd -= 1
        if self.dodge_cd > 0:
            self.dodge_cd -= 1
        if self.dodge_timer > 0:
            self.dodge_timer -= 1
        if self.sound_cd > 0:
            self.sound_cd -= 1

        if self.punch_timer_left > 0:
            self.punch_timer_left -= 1
            if self.punch_timer_left == 0:
                self.arm_len_left = c.ARM_RETRACT
        if self.punch_timer_right > 0:
            self.punch_timer_right -= 1
            if self.punch_timer_right == 0:
                self.arm_len_right = c.ARM_RETRACT

        if self.life <= 0 and not self.knocked_out:
            self.life = 0.0
            self.knocked_out = True
            self.facing_when_ko = self.facing_direction

        if self.arm_lock_left > 0:
            self.arm_lock_left -= 1
        if self.arm_lock_right > 0:
            self.arm_lock_right -= 1
        
        if self.counter_window > 0:
            self.counter_window -= 1

    def attempt_dodge(self, move_vec):
        c = self.cfg
        if self.energy >= c.DODGE_COST and self.dodge_cd == 0:
            self.energy -= c.DODGE_COST
            self.dodge_cd = c.DODGE_CD
            self.dodge_timer = c.DODGE_FRAMES

            if move_vec[0] == 0 and move_vec[1] == 0:
                ang = self.facing_direction + (math.pi / 2 if random.random() < 0.5 else -math.pi / 2)
                move_vec = (math.cos(ang), math.sin(ang))

            self.x += move_vec[0] * c.SPEED * c.DODGE_SPEED_MULT * 6.0
            self.y += move_vec[1] * c.SPEED * c.DODGE_SPEED_MULT * 6.0
            self.clamp_inside()
            return True
        return False

    # ============================================================
    # Punch / Arms
    # ============================================================
    def attempt_punch(self, kind: str, preferred_arm: str | None = None) -> tuple[bool, str | None]:
        c = self.cfg

        if self.punch_cd != 0:
            return (False, None)

        if kind == "short":
            cost, cd, arm_len = c.COST_SHORT, c.CD_SHORT, c.ARM_SHORT
        elif kind == "medium":
            cost, cd, arm_len = c.COST_MED, c.CD_MED, c.ARM_MED
        else:
            cost, cd, arm_len = c.COST_LONG, c.CD_LONG, c.ARM_LONG

        if self.energy < cost:
            return (False, None)

        # evita overlapping de animações (mantém simples e previsível)
        if self.punch_timer_left > 0 or self.punch_timer_right > 0:
            return (False, None)

        # braços disponíveis (não travados)
        available: list[str] = []
        if self.arm_lock_left == 0:
            available.append("left")
        if self.arm_lock_right == 0:
            available.append("right")

        if not available:
            return (False, None)

        if preferred_arm is not None:
            if preferred_arm not in available:
                return (False, None)
            arm = preferred_arm
        else:
            arm = random.choice(available)

        self.energy -= cost
        self.punch_cd = cd

        if arm == "left":
            self.arm_len_left = arm_len
            self.punch_timer_left = c.PUNCH_FRAMES
        else:
            self.arm_len_right = arm_len
            self.punch_timer_right = c.PUNCH_FRAMES

        return (True, arm)

    def cancel_punch_arm(self, arm: str) -> None:
        c = self.cfg
        if arm == "left":
            self.punch_timer_left = 0
            self.arm_len_left = float(c.ARM_RETRACT)
        else:
            self.punch_timer_right = 0
            self.arm_len_right = float(c.ARM_RETRACT)


    def glove_forward_extra_px(self) -> float:
        """
        As glove advances forward beyond the end of the arm: 
        push + (pivot -> tip of glove).
        """
        img = self.glove_left_img
        _w, h = img.get_size()
        pivot_y = float(self.cfg.GLOVE_PIVOT_Y_FRAC) * float(h)
        tip_from_pivot = (0.5 * float(h)) - pivot_y
        tip_from_pivot = max(0.0, tip_from_pivot)
        return float(self.cfg.GLOVE_FORWARD_PUSH_PX) + tip_from_pivot

    def get_arm_segments(self):
        left_shoulder_angle = self.facing_direction + math.pi / 4
        right_shoulder_angle = self.facing_direction - math.pi / 4

        half = self.radius
        lsx = self.x + half * math.cos(left_shoulder_angle)
        lsy = self.y + half * math.sin(left_shoulder_angle)
        rsx = self.x + half * math.cos(right_shoulder_angle)
        rsy = self.y + half * math.sin(right_shoulder_angle)

        fx = math.cos(self.facing_direction)
        fy = math.sin(self.facing_direction)

        lex = lsx + self.arm_len_left * fx
        ley = lsy + self.arm_len_left * fy
        rex = rsx + self.arm_len_right * fx
        rey = rsy + self.arm_len_right * fy

        return (lsx, lsy, lex, ley), (rsx, rsy, rex, rey)

    def reset(self):
        c = self.cfg
        if self.round_lost:
            self.carry_damage += c.CARRY_DAMAGE_PER_LOSS

        max_carry = max(0.0, self.max_life - c.MIN_START_LIFE)
        self.carry_damage = clamp(self.carry_damage, 0.0, max_carry)

        self.life = max(c.MIN_START_LIFE, self.max_life - self.carry_damage)
        self.energy = self.max_energy
        self.knocked_out = False

        self.x = self.initial_x
        self.y = self.initial_y

        self.punch_cd = 0
        self.dodge_cd = 0
        self.dodge_timer = 0

        self.arm_len_left = c.ARM_RETRACT
        self.arm_len_right = c.ARM_RETRACT
        self.punch_timer_left = 0
        self.punch_timer_right = 0

        self.arm_lock_left = 0
        self.arm_lock_right = 0

        self.trail_until_ms = 0
        self.trail_next_drop_ms = 0
        self.prev_x = self.x
        self.prev_y = self.y
        self.last_trail_drop_pos = (self.x, self.y)

        self.round_lost = False
        self.facing_when_ko = self.facing_direction

        self.counter_window = 0
        self.arm_lock_left = 0
        self.arm_lock_right = 0

    def start_trail(self, now_ms: int):
        self.trail_until_ms = now_ms + self.cfg.TRAIL_DURATION_MS
        self.trail_next_drop_ms = now_ms
        self.last_trail_drop_pos = (self.x, self.y)

    def maybe_drop_trail(self, now_ms: int, decals_list, impact_imgs: list):
        c = self.cfg
        if now_ms >= self.trail_until_ms:
            return
        if now_ms < self.trail_next_drop_ms:
            return

        lx, ly = self.last_trail_drop_pos
        moved = math.hypot(self.x - lx, self.y - ly)
        if moved < c.TRAIL_DROP_MIN_DIST:
            return

        vx = self.x - self.prev_x
        vy = self.y - self.prev_y
        vlen = math.hypot(vx, vy)

        ox = oy = 0.0
        if vlen > 1e-6:
            nx = vx / vlen
            ny = vy / vlen
            ox = -nx * c.TRAIL_BACK_OFFSET
            oy = -ny * c.TRAIL_BACK_OFFSET

        pos = (self.x + ox + random.uniform(-4, 4), self.y + oy + random.uniform(-4, 4))
        img = random.choice(impact_imgs)
        decals_list.append(GroundDecal(c, img, pos, now_ms))

        self.last_trail_drop_pos = (self.x, self.y)
        self.trail_next_drop_ms = now_ms + c.TRAIL_DROP_EVERY_MS

    def lock_arm(self, arm: str, frames: int) -> None:
        frames = max(0, int(frames))
        if arm == "left":
            self.arm_lock_left = max(self.arm_lock_left, frames)
            self.arm_lock_right = 0
        else:
            self.arm_lock_right = max(self.arm_lock_right, frames)
            self.arm_lock_left = 0

    # ============================================================
    # Rotation cache
    # ============================================================
    def _quant_angle(self, angle_deg: float) -> int:
        step = max(1, int(self.cfg.GLOVE_CACHE_STEP_DEG))
        return int(round(angle_deg / step) * step)

    def _rot_cached(self, img: pygame.Surface, angle_deg: float) -> tuple[pygame.Surface, int]:
        qa = self._quant_angle(angle_deg)
        key = (id(img), qa)
        r = self._rot_cache.get(key)
        if r is None:
            r = pygame.transform.rotate(img, qa).convert_alpha()
            self._rot_cache[key] = r
        return r, qa

    # ============================================================
    # Draw
    # ============================================================
    def draw(self, surface):
        if self.life <= 0:
            img = self.ko_image
            ang = self.facing_when_ko
        else:
            img = self.head_image
            ang = self.facing_direction

        angle_deg = -math.degrees(ang) + 90
        rotated, _qa = self._rot_cached(img, angle_deg)
        rect = rotated.get_rect(center=(self.x, self.y))
        surface.blit(rotated, rect)

        if self.life > 0:
            self.draw_arms(surface)
            if self.dodge_timer > 0:
                pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), int(self.radius), 2)

    def draw_arms(self, surface):
        c = self.cfg
        (lsx, lsy, lex, ley), (rsx, rsy, rex, rey) = self.get_arm_segments()

        glove_angle = -math.degrees(self.facing_direction) + c.GLOVE_BASE_ROT_DEG

        fx = math.cos(self.facing_direction)
        fy = math.sin(self.facing_direction)
        push = c.GLOVE_FORWARD_PUSH_PX
        handL = (lex + fx * push, ley + fy * push)
        handR = (rex + fx * push, rey + fy * push)

        lw, lh = self.glove_left_img.get_size()
        rw, rh = self.glove_right_img.get_size()
        pivotL = (c.GLOVE_PIVOT_X_FRAC * lw, c.GLOVE_PIVOT_Y_FRAC * lh)
        pivotR = (c.GLOVE_PIVOT_X_FRAC * rw, c.GLOVE_PIVOT_Y_FRAC * rh)

        rotL, qaL = self._rot_cached(self.glove_left_img, glove_angle)
        pvxL, pvyL = rotate_vec(pivotL[0], pivotL[1], qaL)
        rectL = rotL.get_rect(center=(int(handL[0] - pvxL), int(handL[1] - pvyL)))
        surface.blit(rotL, rectL)

        rotR, qaR = self._rot_cached(self.glove_right_img, glove_angle)
        pvxR, pvyR = rotate_vec(pivotR[0], pivotR[1], qaR)
        rectR = rotR.get_rect(center=(int(handR[0] - pvxR), int(handR[1] - pvyR)))
        surface.blit(rotR, rectR)

