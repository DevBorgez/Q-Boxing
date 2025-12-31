from __future__ import annotations

import random
import pygame


class GroundDecal:
    def __init__(self, cfg, base_img: pygame.Surface, pos: tuple[float, float], born_ms: int):
        self.cfg = cfg
        self.pos = (float(pos[0]), float(pos[1]))
        self.born_ms = int(born_ms)
        self.die_ms = self.born_ms + int(cfg.DECAL_LIFETIME_MS)

        ang = random.uniform(0, 360)
        scale = random.uniform(0.85, 1.12)
        w, h = base_img.get_size()
        img = pygame.transform.smoothscale(base_img, (max(1, int(w * scale)), max(1, int(h * scale))))
        self.img = pygame.transform.rotate(img, ang).convert_alpha()

    def alive(self, now_ms: int) -> bool:
        return now_ms < self.die_ms

    def draw(self, surface: pygame.Surface, now_ms: int):
        remaining = self.die_ms - now_ms
        if remaining <= self.cfg.DECAL_FADE_MS:
            alpha = int(255 * max(0.0, remaining / self.cfg.DECAL_FADE_MS))
            self.img.set_alpha(alpha)
        else:
            self.img.set_alpha(255)

        rect = self.img.get_rect(center=(int(self.pos[0]), int(self.pos[1])))
        surface.blit(self.img, rect)
