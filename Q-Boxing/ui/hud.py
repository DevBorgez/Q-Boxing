from __future__ import annotations

import pygame
from core.math_utils import clamp


def draw_text_topleft(surface, font, text, x, y, color, shadow=True):
    if shadow:
        s = font.render(text, True, (0, 0, 0))
        surface.blit(s, (x + 2, y + 2))
    t = font.render(text, True, color)
    surface.blit(t, (x, y))


def draw_text_topright(surface, font, text, x_right, y, color, shadow=True):
    t = font.render(text, True, color)
    rect = t.get_rect()
    rect.topright = (x_right, y)
    if shadow:
        s = font.render(text, True, (0, 0, 0))
        srect = s.get_rect()
        srect.topright = (x_right + 2, y + 2)
        surface.blit(s, srect)
    surface.blit(t, rect)


def draw_text_center(surface, font, text, cx, cy, color, shadow=True):
    t = font.render(text, True, color)
    rect = t.get_rect(center=(cx, cy))
    if shadow:
        s = font.render(text, True, (0, 0, 0))
        srect = s.get_rect(center=(cx + 2, cy + 2))
        surface.blit(s, srect)
    surface.blit(t, rect)


def draw_bar(surface, x, y, w, h, frac, bg, fg, border=(0, 0, 0), border_w=2):
    frac = clamp(frac, 0.0, 1.0)
    pygame.draw.rect(surface, bg, (x, y, w, h), border_radius=8)
    pygame.draw.rect(surface, fg, (x, y, int(w * frac), h), border_radius=8)
    pygame.draw.rect(surface, border, (x, y, w, h), border_w, border_radius=8)


def draw_hud(cfg, surface, font, font_big, font_super,
             red, blue,
             rounds_played: int, max_rounds: int, red_score: int, blue_score: int,
             time_left: int, game_over: bool, round_over: bool,
             now_ms: int, super_punch_until_ms: int):

    hud_h = 112
    pygame.draw.rect(surface, cfg.HUD_BG, (0, 0, cfg.WIDTH, hud_h))

    pad = 14
    label_y = 8

    draw_text_topleft(surface, font, "Red", pad, label_y, (255, 140, 140), shadow=False)
    draw_text_topright(surface, font, "Blue", cfg.WIDTH - pad, label_y, (140, 175, 255), shadow=False)

    bar_w = 300
    bar_x_left = pad
    bar_x_right = cfg.WIDTH - pad - bar_w

    draw_bar(surface, bar_x_left, 30, bar_w, 16, red.life / red.max_life, (70, 30, 30), (40, 190, 70))
    draw_bar(surface, bar_x_left, 52, bar_w, 12, red.energy / red.max_energy, (70, 70, 20), (70, 120, 240))

    draw_bar(surface, bar_x_right, 30, bar_w, 16, blue.life / blue.max_life, (70, 30, 30), (40, 190, 70))
    draw_bar(surface, bar_x_right, 52, bar_w, 12, blue.energy / blue.max_energy, (70, 70, 20), (70, 120, 240))

    center_x = cfg.WIDTH // 2
    draw_text_center(surface, font, f"Round {rounds_played}/{max_rounds}", center_x, 14, (210, 210, 210), shadow=True)
    draw_text_center(surface, font_big, f"{time_left:02d}", center_x, 46, cfg.HUD_FG, shadow=True)
    draw_text_center(surface, font, f"{red_score}   x   {blue_score}", center_x, 74, (230, 230, 230), shadow=True)

    if now_ms < super_punch_until_ms:
        draw_text_center(surface, font_super, "Super Punch!", center_x, 100, cfg.SUPER_PUNCH_GOLD, shadow=True)

    if game_over:
        if red_score > blue_score:
            msg = "VICTORY: RED"
        elif blue_score > red_score:
            msg = "VICTORY: BLUE"
        else:
            msg = "TIE"
        draw_text_center(surface, font_big, msg, center_x, 150, (255, 255, 255), shadow=True)
    elif round_over:
        draw_text_center(surface, font_big, "ROUND OVER", center_x, 150, (255, 255, 255), shadow=True)
