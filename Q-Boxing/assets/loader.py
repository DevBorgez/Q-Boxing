from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pygame


@dataclass(frozen=True)
class Assets:
    impact_imgs: list[pygame.Surface]
    boxer1: pygame.Surface
    boxer2: pygame.Surface
    ko1: pygame.Surface
    ko2: pygame.Surface

    snd_light: Optional[pygame.mixer.Sound]
    snd_mid: Optional[pygame.mixer.Sound]
    snd_heavy: Optional[pygame.mixer.Sound]

    red_glove_L: pygame.Surface
    red_glove_R: pygame.Surface
    blue_glove_L: pygame.Surface
    blue_glove_R: pygame.Surface


def safe_load_img(path: str | None) -> pygame.Surface:
    try:
        if not path:
            raise FileNotFoundError("path vazio")
        return pygame.image.load(path).convert_alpha()
    except Exception:
        # placeholder
        s = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.circle(s, (220, 220, 220, 140), (32, 32), 26, 3)
        pygame.draw.line(s, (220, 220, 220, 140), (32, 10), (32, 54), 2)
        pygame.draw.line(s, (220, 220, 220, 140), (10, 32), (54, 32), 2)
        return s


def scale_smooth(img: pygame.Surface, scale: float) -> pygame.Surface:
    w, h = img.get_size()
    nw = max(1, int(w * scale))
    nh = max(1, int(h * scale))
    return pygame.transform.smoothscale(img, (nw, nh))


def safe_load_snd(path: str | None):
    try:
        if not path:
            raise FileNotFoundError("path vazio")
        return pygame.mixer.Sound(path)
    except Exception:
        return None


def load_assets(cfg) -> Assets:
    impact_imgs = [
        pygame.transform.smoothscale(safe_load_img(os.environ.get("TRAIL_OF_DAMAGE_1")), (40, 40)),
        pygame.transform.smoothscale(safe_load_img(os.environ.get("TRAIL_OF_DAMAGE_2")), (40, 40)),
        pygame.transform.smoothscale(safe_load_img(os.environ.get("TRAIL_OF_DAMAGE_3")), (40, 40)),
        pygame.transform.smoothscale(safe_load_img(os.environ.get("TRAIL_OF_DAMAGE_4")), (40, 40)),
    ]

    boxer1 = pygame.transform.smoothscale(safe_load_img(os.environ.get("BOXER_1")), (cfg.HEAD_SIZE, cfg.HEAD_SIZE))
    boxer2 = pygame.transform.smoothscale(safe_load_img(os.environ.get("BOXER_2")), (cfg.HEAD_SIZE, cfg.HEAD_SIZE))
    ko1 = pygame.transform.smoothscale(safe_load_img(os.environ.get("KNOCKED_OUT_1")), (cfg.HEAD_SIZE, cfg.HEAD_SIZE))
    ko2 = pygame.transform.smoothscale(safe_load_img(os.environ.get("KNOCKED_OUT_2")), (cfg.HEAD_SIZE, cfg.HEAD_SIZE))

    snd_light = safe_load_snd(os.environ.get("WEAK_PUNCH_SOUND"))
    snd_mid = safe_load_snd(os.environ.get("MEDIUM_PUNCH_SOUND"))
    snd_heavy = safe_load_snd(os.environ.get("STRONG_PUNCH_SOUND"))

    red_glove_L = scale_smooth(safe_load_img(cfg.RED_GLOVE_L_PATH), cfg.GLOVE_SCALE_RED)
    red_glove_R = scale_smooth(safe_load_img(cfg.RED_GLOVE_R_PATH), cfg.GLOVE_SCALE_RED)
    blue_glove_L = scale_smooth(safe_load_img(cfg.BLUE_GLOVE_L_PATH), cfg.GLOVE_SCALE_BLUE)
    blue_glove_R = scale_smooth(safe_load_img(cfg.BLUE_GLOVE_R_PATH), cfg.GLOVE_SCALE_BLUE)

    return Assets(
        impact_imgs=impact_imgs,
        boxer1=boxer1,
        boxer2=boxer2,
        ko1=ko1,
        ko2=ko2,
        snd_light=snd_light,
        snd_mid=snd_mid,
        snd_heavy=snd_heavy,
        red_glove_L=red_glove_L,
        red_glove_R=red_glove_R,
        blue_glove_L=blue_glove_L,
        blue_glove_R=blue_glove_R,
    )
