from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from core.math_utils import dist, clamp, closest_point_on_segment, segment_circle_hit
from core.rng import real_random_damage, roll, secrets_uniform
from fx.decals import GroundDecal
from ui.hud import draw_hud
from game.character import Character


@dataclass(frozen=True)
class Fonts:
    small: pygame.font.Font
    big: pygame.font.Font
    super: pygame.font.Font


class Game:
    def __init__(self, cfg, screen: pygame.Surface, clock: pygame.time.Clock, fonts: Fonts, assets):
        self.cfg = cfg
        self.screen = screen
        self.clock = clock
        self.fonts = fonts
        self.assets = assets

        # Spawn
        self.red = Character(
            cfg,
            140, cfg.HEIGHT // 2,
            (255, 0, 0), (255, 200, 160),
            "Vermelho",
            assets.boxer1, assets.ko1,
            assets.impact_imgs, assets.snd_light, assets.snd_mid, assets.snd_heavy,
            assets.red_glove_L, assets.red_glove_R
        )
        self.blue = Character(
            cfg,
            cfg.WIDTH - 140, cfg.HEIGHT // 2,
            (0, 0, 255), (240, 190, 180),
            "Azul",
            assets.boxer2, assets.ko2,
            assets.impact_imgs, assets.snd_light, assets.snd_mid, assets.snd_heavy,
            assets.blue_glove_L, assets.blue_glove_R
        )

        # Game state
        self.rounds_played = 0
        self.red_score = 0
        self.blue_score = 0
        self.game_over = False
        self.round_over = False
        self.round_over_until_ms = 0

        self.time_left = cfg.ROUND_TIME_SEC
        now = pygame.time.get_ticks()
        self.last_second_tick = now
        self.round_start_ms = now

        self.ground_decals: list[GroundDecal] = []
        self.max_distance_allowance = 260.0
        self.super_punch_until_ms = 0

    # ============================================================
    # Audio / Damage
    # ============================================================
    def _play_hit_sound(self, attacker: Character, damage: float):
        if attacker.sound_cd > 0:
            return
        if damage <= 9:
            snd = attacker.snd_light
        elif damage >= 22:
            snd = attacker.snd_heavy
        else:
            snd = attacker.snd_mid

        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass
        attacker.sound_cd = 10

    def _apply_damage(self, attacker: Character, defender: Character, dmg: float, hit_pos: tuple[float, float]):
        defender.life = max(0.0, defender.life - dmg)
        now = pygame.time.get_ticks()

        self.ground_decals.append(GroundDecal(self.cfg, random.choice(attacker.impacts), hit_pos, now))
        defender.start_trail(now)
        self._play_hit_sound(attacker, dmg)

        if random.random() < defender.knockout_vulnerability:
            defender.life = 0.0
            defender.knocked_out = True
            defender.facing_when_ko = defender.facing_direction

        if len(self.ground_decals) > self.cfg.MAX_DECALS:
            del self.ground_decals[:len(self.ground_decals) - self.cfg.MAX_DECALS]

    # ============================================================
    # Reward / Engage
    # ============================================================
    @staticmethod
    def _in_punch_action(action_name: str) -> bool:
        return action_name in ("punch_short", "punch_medium", "punch_long")

    def _compute_reward(self, self_char: Character, opp_char: Character,
                        action_name: str,
                        dmg_dealt: float, dmg_taken: float,
                        dist_before: float, dist_after: float,
                        time_left: int) -> float:
        c = self.cfg
        r = c.R_BASE
        r += c.R_DAMAGE * dmg_dealt
        r -= c.R_TAKEN * dmg_taken

        if dist_before > 210:
            r += c.R_CLOSE * max(0.0, dist_before - dist_after)

        if dist_before > c.ENGAGE_DIST:
            r += c.R_FAR_STEP

        if self._in_punch_action(action_name) and dmg_dealt <= 0.0 and dist_before > c.ARM_LONG + self_char.radius:
            r += c.R_FAR_PUNCH_MISS

        if action_name == "do_nothing" and dist_before > 250 and self_char.energy > 35:
            r += c.R_IDLE_FAR

        if self_char.energy < 15 and action_name in ("punch_long", "dodge", "punch_medium"):
            r += c.R_LOW_ENERGY_WASTE

        if time_left <= 10 and dist_before > self.max_distance_allowance:
            r -= 0.12

        return float(r)

    def _engagement_force(self, a: Character, b: Character, now_ms: int) -> tuple[float, float]:
        c = self.cfg
        dx = b.x - a.x
        dy = b.y - a.y
        d = math.hypot(dx, dy)
        if d < 1e-6:
            return (0.0, 0.0)

        if d < c.ENGAGE_DIST:
            return (0.0, 0.0)

        nx = dx / d
        ny = dy / d
        scale = clamp((d - c.ENGAGE_DIST) / 260.0, 0.0, 1.0)

        opening = (now_ms - self.round_start_ms) < int(c.ENGAGE_OPENING_SEC * 1000)
        f = (c.ENGAGE_OPENING_FORCE if opening else c.ENGAGE_FORCE)

        return (nx * f * scale, ny * f * scale)

    # ============================================================
    # Step (Q-learning)
    # ============================================================
    def _action_to_move(self, action_name: str) -> tuple[float, float]:
        c = self.cfg
        mx = my = 0.0
        if action_name == "move_up":
            my = -c.SPEED
        elif action_name == "move_down":
            my = c.SPEED
        elif action_name == "move_left":
            mx = -c.SPEED
        elif action_name == "move_right":
            mx = c.SPEED

        if action_name in ("move_up", "move_down", "move_left", "move_right") and random.random() < 0.08:
            if random.random() < 0.5:
                mx += random.choice([-1, 1]) * (c.SPEED * 0.18)
            else:
                my += random.choice([-1, 1]) * (c.SPEED * 0.18)

        return mx, my

    def resolve_step(self) -> bool:
        c = self.cfg

        self.red.prev_x, self.red.prev_y = self.red.x, self.red.y
        self.blue.prev_x, self.blue.prev_y = self.blue.x, self.blue.y

        s_red = self.red.get_state(self.blue, self.time_left)
        s_blue = self.blue.get_state(self.red, self.time_left)

        a_red = self.red.choose_action(s_red)
        a_blue = self.blue.choose_action(s_blue)

        self.red.action_idx = a_red
        self.blue.action_idx = a_blue
        act_red = c.ACTIONS[a_red]
        act_blue = c.ACTIONS[a_blue]

        self.red.update_facing(self.blue)
        self.blue.update_facing(self.red)

        dist_before = dist((self.red.x, self.red.y), (self.blue.x, self.blue.y))

        rmx, rmy = self._action_to_move(act_red)
        bmx, bmy = self._action_to_move(act_blue)

        if act_red == "dodge":
            self.red.attempt_dodge((math.cos(self.red.facing_direction + math.pi / 2), math.sin(self.red.facing_direction + math.pi / 2)))
        if act_blue == "dodge":
            self.blue.attempt_dodge((math.cos(self.blue.facing_direction - math.pi / 2), math.sin(self.blue.facing_direction - math.pi / 2)))

        now = pygame.time.get_ticks()
        erx, ery = self._engagement_force(self.red, self.blue, now)
        ebx, eby = self._engagement_force(self.blue, self.red, now)

        r_speed_mult = c.DODGE_SPEED_MULT if self.red.dodge_timer > 0 else 1.0
        b_speed_mult = c.DODGE_SPEED_MULT if self.blue.dodge_timer > 0 else 1.0

        self.red.x += (rmx * r_speed_mult) + (erx * c.SPEED * 1.15)
        self.red.y += (rmy * r_speed_mult) + (ery * c.SPEED * 1.15)
        self.blue.x += (bmx * b_speed_mult) + (ebx * c.SPEED * 1.15)
        self.blue.y += (bmy * b_speed_mult) + (eby * c.SPEED * 1.15)

        self.red.clamp_inside()
        self.blue.clamp_inside()

        # circular collision
        dx = self.blue.x - self.red.x
        dy = self.blue.y - self.red.y
        d = math.hypot(dx, dy)
        min_d = (self.red.radius + self.blue.radius) * 0.98
        if d < min_d and d > 1e-6:
            push = (min_d - d) * 0.5
            nx = dx / d
            ny = dy / d
            self.red.x -= nx * push
            self.red.y -= ny * push
            self.blue.x += nx * push
            self.blue.y += ny * push
            self.red.clamp_inside()
            self.blue.clamp_inside()

        # punches
        red_punch_started = False
        blue_punch_started = False
        if act_red == "punch_short":
            red_punch_started = self.red.attempt_punch("short")
        elif act_red == "punch_medium":
            red_punch_started = self.red.attempt_punch("medium")
        elif act_red == "punch_long":
            red_punch_started = self.red.attempt_punch("long")

        if act_blue == "punch_short":
            blue_punch_started = self.blue.attempt_punch("short")
        elif act_blue == "punch_medium":
            blue_punch_started = self.blue.attempt_punch("medium")
        elif act_blue == "punch_long":
            blue_punch_started = self.blue.attempt_punch("long")

        dmg_red = 0.0
        dmg_blue = 0.0

        red_life_before = self.red.life
        blue_life_before = self.blue.life

        if self.red.life > 0 and self.blue.life > 0:
            # RED -> BLUE
            if red_punch_started:
                (lsx, lsy, lex, ley), (rsx, rsy, rex, rey) = self.red.get_arm_segments()
                if not (self.blue.dodge_timer > 0 and random.random() < c.DODGE_EVADE_PROB):
                    hit_l = segment_circle_hit(lsx, lsy, lex, ley, self.blue.x, self.blue.y, self.blue.radius * 0.92)
                    hit_r = segment_circle_hit(rsx, rsy, rex, rey, self.blue.x, self.blue.y, self.blue.radius * 0.92)
                    if hit_l or hit_r:
                        dist_rb = math.hypot(self.red.x - self.blue.x, self.red.y - self.blue.y)

                        if act_red == "punch_short":
                            dmg_red = real_random_damage(c, c.DMG_SHORT_MIN, c.DMG_SHORT_MAX, self.red.energy, dist_rb, c.IDEAL_DIST_SHORT)
                        elif act_red == "punch_medium":
                            dmg_red = real_random_damage(c, c.DMG_MED_MIN, c.DMG_MED_MAX, self.red.energy, dist_rb, c.IDEAL_DIST_MED)
                        else:
                            dmg_red = real_random_damage(c, c.DMG_LONG_MIN, c.DMG_LONG_MAX, self.red.energy, dist_rb, c.IDEAL_DIST_LONG)

                        if roll(c.SUPER_PUNCH_CHANCE):
                            dmg_red = secrets_uniform(c.SUPER_PUNCH_DMG_MIN, c.SUPER_PUNCH_DMG_MAX)
                            self.super_punch_until_ms = now + c.SUPER_PUNCH_MSG_MS

                        if hit_l:
                            hx, hy = closest_point_on_segment(lsx, lsy, lex, ley, self.blue.x, self.blue.y)
                        else:
                            hx, hy = closest_point_on_segment(rsx, rsy, rex, rey, self.blue.x, self.blue.y)
                        self._apply_damage(self.red, self.blue, dmg_red, (hx, hy))

            # BLUE -> RED
            if blue_punch_started:
                (lsx, lsy, lex, ley), (rsx, rsy, rex, rey) = self.blue.get_arm_segments()
                if not (self.red.dodge_timer > 0 and random.random() < c.DODGE_EVADE_PROB):
                    hit_l = segment_circle_hit(lsx, lsy, lex, ley, self.red.x, self.red.y, self.red.radius * 0.92)
                    hit_r = segment_circle_hit(rsx, rsy, rex, rey, self.red.x, self.red.y, self.red.radius * 0.92)
                    if hit_l or hit_r:
                        dist_rb = math.hypot(self.red.x - self.blue.x, self.red.y - self.blue.y)

                        if act_blue == "punch_short":
                            dmg_blue = real_random_damage(c, c.DMG_SHORT_MIN, c.DMG_SHORT_MAX, self.blue.energy, dist_rb, c.IDEAL_DIST_SHORT)
                        elif act_blue == "punch_medium":
                            dmg_blue = real_random_damage(c, c.DMG_MED_MIN, c.DMG_MED_MAX, self.blue.energy, dist_rb, c.IDEAL_DIST_MED)
                        else:
                            dmg_blue = real_random_damage(c, c.DMG_LONG_MIN, c.DMG_LONG_MAX, self.blue.energy, dist_rb, c.IDEAL_DIST_LONG)

                        if roll(c.SUPER_PUNCH_CHANCE):
                            dmg_blue = secrets_uniform(c.SUPER_PUNCH_DMG_MIN, c.SUPER_PUNCH_DMG_MAX)
                            self.super_punch_until_ms = now + c.SUPER_PUNCH_MSG_MS

                        if hit_l:
                            hx, hy = closest_point_on_segment(lsx, lsy, lex, ley, self.red.x, self.red.y)
                        else:
                            hx, hy = closest_point_on_segment(rsx, rsy, rex, rey, self.red.x, self.red.y)
                        self._apply_damage(self.blue, self.red, dmg_blue, (hx, hy))

        now2 = pygame.time.get_ticks()
        self.red.maybe_drop_trail(now2, self.ground_decals, self.red.impacts)
        self.blue.maybe_drop_trail(now2, self.ground_decals, self.blue.impacts)

        dmg_taken_red = max(0.0, red_life_before - self.red.life)
        dmg_taken_blue = max(0.0, blue_life_before - self.blue.life)

        # regen energia
        red_moved = (rmx != 0.0 or rmy != 0.0) or (self.red.dodge_timer > 0) or (abs(erx) + abs(ery) > 0)
        blue_moved = (bmx != 0.0 or bmy != 0.0) or (self.blue.dodge_timer > 0) or (abs(ebx) + abs(eby) > 0)

        self.red.energy = min(self.red.max_energy, self.red.energy + (c.REGEN_MOVE if red_moved else c.REGEN_IDLE))
        self.blue.energy = min(self.blue.max_energy, self.blue.energy + (c.REGEN_MOVE if blue_moved else c.REGEN_IDLE))

        dist_after = dist((self.red.x, self.red.y), (self.blue.x, self.blue.y))

        self.red.tick_timers()
        self.blue.tick_timers()

        r_red = self._compute_reward(self.red, self.blue, act_red, dmg_red, dmg_taken_red, dist_before, dist_after, self.time_left)
        r_blue = self._compute_reward(self.blue, self.red, act_blue, dmg_blue, dmg_taken_blue, dist_before, dist_after, self.time_left)

        done = False
        if self.red.life <= 0 or self.blue.life <= 0:
            done = True
            if self.red.life <= 0 and self.blue.life <= 0:
                pass
            elif self.blue.life <= 0:
                r_red += c.R_WIN
                r_blue += c.R_LOSE
            else:
                r_blue += c.R_WIN
                r_red += c.R_LOSE

        s2_red = self.red.get_state(self.blue, self.time_left)
        s2_blue = self.blue.get_state(self.red, self.time_left)

        # Q update
        old = self.red.q_table[s_red, a_red]
        nxt = float(self.red.q_table[s2_red].max())
        self.red.q_table[s_red, a_red] = old + c.ALPHA * (r_red + (0.0 if done else c.GAMMA * nxt) - old)

        old = self.blue.q_table[s_blue, a_blue]
        nxt = float(self.blue.q_table[s2_blue].max())
        self.blue.q_table[s_blue, a_blue] = old + c.ALPHA * (r_blue + (0.0 if done else c.GAMMA * nxt) - old)

        self.red.decay_epsilon()
        self.blue.decay_epsilon()

        if self.time_left <= 10:
            self.max_distance_allowance = max(120.0, self.max_distance_allowance - 10.0)

        return done

    # ============================================================
    # Round logic + render
    # ============================================================
    def _end_round_by_time(self, now: int):
        self.round_over = True
        self.round_over_until_ms = now + self.cfg.BETWEEN_ROUND_MS

        if self.red.life > self.blue.life:
            self.red_score += 1
            self.blue.round_lost = True
        elif self.blue.life > self.red.life:
            self.blue_score += 1
            self.red.round_lost = True
        else:
            self.red_score += 1
            self.blue_score += 1

        self.rounds_played += 1
        if self.rounds_played >= self.cfg.MAX_ROUNDS:
            self.game_over = True

    def _end_round_by_ko(self, now: int):
        self.round_over = True
        self.round_over_until_ms = now + self.cfg.BETWEEN_ROUND_MS

        if self.red.life <= 0 and self.blue.life <= 0:
            pass
        elif self.red.life <= 0:
            self.blue_score += 1
            self.red.knockout_vulnerability += 0.001
            self.red.round_lost = True
        elif self.blue.life <= 0:
            self.red_score += 1
            self.blue.knockout_vulnerability += 0.001
            self.blue.round_lost = True

        self.rounds_played += 1
        if self.rounds_played >= self.cfg.MAX_ROUNDS:
            self.game_over = True

    def _reset_round(self, now: int):
        self.red.reset()
        self.blue.reset()
        self.time_left = self.cfg.ROUND_TIME_SEC
        self.last_second_tick = now
        self.round_over = False
        self.max_distance_allowance = 260.0
        self.round_start_ms = now

    def _update_clock(self, now: int):
        if self.game_over or self.round_over:
            return
        if now - self.last_second_tick >= 1000:
            self.last_second_tick += 1000
            self.time_left -= 1
            if self.time_left <= 0:
                self.time_left = 0
                self._end_round_by_time(now)

    def render(self, now: int):
        self.screen.fill(self.cfg.BG)

        self.ground_decals = [d for d in self.ground_decals if d.alive(now)]
        for d in self.ground_decals:
            d.draw(self.screen, now)

        self.red.update_facing(self.blue)
        self.blue.update_facing(self.red)
        self.red.draw(self.screen)
        self.blue.draw(self.screen)

        draw_hud(
            self.cfg,
            self.screen,
            self.fonts.small,
            self.fonts.big,
            self.fonts.super,
            self.red,
            self.blue,
            self.rounds_played,
            self.cfg.MAX_ROUNDS,
            self.red_score,
            self.blue_score,
            self.time_left,
            self.game_over,
            self.round_over,
            now,
            self.super_punch_until_ms,
        )

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            _dt = self.clock.tick(self.cfg.FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            now = pygame.time.get_ticks()
            self._update_clock(now)

            if not self.game_over:
                if not self.round_over:
                    done = self.resolve_step()
                    if done:
                        self._end_round_by_ko(now)
                else:
                    if now >= self.round_over_until_ms:
                        self._reset_round(now)

            self.render(now)
