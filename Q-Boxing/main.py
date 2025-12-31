from __future__ import annotations

import sys
import pygame
from dotenv import load_dotenv

from config import CFG
from assets.loader import load_assets
from game.match import Game, Fonts

def main():
    load_dotenv()
    cfg = CFG()

    pygame.init()
    try:
        pygame.mixer.init()
    except Exception:
        pass

    screen = pygame.display.set_mode((cfg.WIDTH, cfg.HEIGHT))
    pygame.display.set_caption("Red vs Blue - Q-Learning Boxing Fight")
    clock = pygame.time.Clock()

    fonts = Fonts(
        small=pygame.font.Font(None, 26),
        big=pygame.font.Font(None, 56),
        super=pygame.font.Font(None, 44),
    )

    # IMPORTANT: load_assets should occur after set_mode (because of convert_alpha)
    assets = load_assets(cfg)

    game = Game(cfg, screen, clock, fonts, assets)
    game.run()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
