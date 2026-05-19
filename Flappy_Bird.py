"""
Flappy Bird — Python/Pygame
4 levels: Easy → Medium → Hard → Expert
Controls: SPACE or Left Click to flap
"""

import pygame
import sys
import random
import math

pygame.init()

# ──────────────────────────────────────────────
# SCREEN & TIMING
# ──────────────────────────────────────────────
SCREEN_W, SCREEN_H = 480, 700
FPS = 60
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Flappy Bird")
clock = pygame.time.Clock()

# ──────────────────────────────────────────────
# COLORS
# ──────────────────────────────────────────────
WHITE       = (255, 255, 255)
BLACK       = (0,   0,   0  )
YELLOW      = (255, 220, 50 )
ORANGE      = (255, 140, 0  )
RED         = (220, 50,  50 )
PIPE_GREEN  = (83,  183, 52 )
PIPE_DARK   = (55,  130, 30 )
PIPE_LIGHT  = (110, 220, 80 )
GROUND_TAN  = (222, 184, 135)
GROUND_DARK = (180, 140, 90 )
GROUND_TOP  = (100, 180, 60 )

# ──────────────────────────────────────────────
# FONTS
# ──────────────────────────────────────────────
font_xl    = pygame.font.SysFont("Arial", 72, bold=True)
font_large = pygame.font.SysFont("Arial", 48, bold=True)
font_med   = pygame.font.SysFont("Arial", 32, bold=True)
font_small = pygame.font.SysFont("Arial", 22, bold=True)
font_tiny  = pygame.font.SysFont("Arial", 16)

# ──────────────────────────────────────────────
# PHYSICS
# ──────────────────────────────────────────────
GRAVITY      = 0.5
FLAP         = -9.5
GROUND_Y     = SCREEN_H - 80   # top of ground strip

# ──────────────────────────────────────────────
# LEVEL CONFIG
# ──────────────────────────────────────────────
#  pipe_speed  : px/frame the pipes scroll left
#  gap         : vertical gap in pixels between top/bot pipe
#  pipe_freq   : frames between pipe spawns
#  moving      : whether pipes oscillate vertically (level 4)
#  score_next  : score needed to advance to next level
#  sky_top/bot : gradient top/bottom colour for sky
LEVEL_CFG = {
    1: dict(pipe_speed=3.0, gap=165, pipe_freq=90,  moving=False,
            score_next=5,
            sky_top=(100, 190, 240), sky_bot=(60, 120, 180),
            name="Easy",   badge=(50,  200, 80 )),
    2: dict(pipe_speed=4.0, gap=140, pipe_freq=80,  moving=False,
            score_next=12,
            sky_top=(80,  160, 220), sky_bot=(40, 90,  170),
            name="Medium", badge=(50,  130, 255)),
    3: dict(pipe_speed=5.2, gap=118, pipe_freq=68,  moving=False,
            score_next=22,
            sky_top=(70,  110, 200), sky_bot=(30, 60,  150),
            name="Hard",   badge=(255, 140, 40 )),
    4: dict(pipe_speed=6.8, gap=98,  pipe_freq=58,  moving=True,
            score_next=9999,
            sky_top=(45,  60,  150), sky_bot=(20, 30,  100),
            name="Expert", badge=(220, 50,  50 )),
}

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def rrect(surf, color, rect, r=10, border=None, bw=2):
    """Rounded rectangle, optional border."""
    pygame.draw.rect(surf, color, rect, border_radius=r)
    if border:
        pygame.draw.rect(surf, border, rect, bw, border_radius=r)

def text_shadow(surf, font, txt, color, x, y, shadow=(0, 0, 0), offset=2):
    s = font.render(txt, True, shadow)
    surf.blit(s, (x + offset, y + offset))
    t = font.render(txt, True, color)
    surf.blit(t, (x, y))
    return t.get_width(), t.get_height()

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


# ══════════════════════════════════════════════
# BIRD
# ══════════════════════════════════════════════
class Bird:
    HITBOX = 15     # collision radius (smaller than visual for fairness)

    def __init__(self, x=110, y=350):
        self.x  = float(x)
        self.y  = float(y)
        self.vy = 0.0
        self.angle   = 0.0        # tilt in degrees (positive = nose-up)
        self.frame   = 0          # wing frame 0/1/2
        self.f_timer = 0
        self.alive   = True
        self._build_surfaces()

    # ── pre-render wing frames ──────────────────
    def _build_surfaces(self):
        self.frames = []
        wing_positions = [
            ("up",   (5,  7,  22, 10)),   # wing up
            ("mid",  (5,  14, 22, 10)),   # wing mid
            ("down", (5,  20, 22, 10)),   # wing down
        ]
        for _, wing_rect in wing_positions:
            s = pygame.Surface((48, 40), pygame.SRCALPHA)
            # body
            pygame.draw.ellipse(s, (255, 200, 50), (4, 8, 38, 26))
            pygame.draw.ellipse(s, (210, 155, 20), (4, 8, 38, 26), 2)
            # belly patch
            pygame.draw.ellipse(s, (255, 240, 180), (14, 14, 20, 14))
            # wing
            pygame.draw.ellipse(s, (230, 155, 20), wing_rect)
            pygame.draw.ellipse(s, (170, 110, 10), wing_rect, 1)
            # eye white
            pygame.draw.circle(s, WHITE,         (33, 13), 8)
            # pupil
            pygame.draw.circle(s, BLACK,         (35, 13), 5)
            # shine
            pygame.draw.circle(s, WHITE,         (37, 11), 2)
            # beak
            pygame.draw.polygon(s, ORANGE, [(40, 16), (48, 18), (40, 22)])
            pygame.draw.polygon(s, (200, 100, 0), [(40, 16), (48, 18), (40, 22)], 1)
            self.frames.append(s)

    def flap(self):
        self.vy    = FLAP
        self.frame = 0      # snap to wing-up on flap

    def update(self):
        self.vy    += GRAVITY
        self.y     += self.vy
        # tilt: nose up when rising, nose down when falling
        target = 30 if self.vy < 0 else max(-80, -self.vy * 4)
        self.angle += (target - self.angle) * 0.12
        # wing animation (cycles slower when falling)
        self.f_timer += 1
        if self.f_timer >= 7:
            self.f_timer = 0
            self.frame   = (self.frame + 1) % 3

    def draw(self, surf):
        bx, by = int(self.x), int(self.y)
        img = self.frames[self.frame]
        rot = pygame.transform.rotate(img, self.angle)
        r   = rot.get_rect(center=(bx, by))
        surf.blit(rot, r)

    @property
    def rect(self):
        """Shrunken hitbox for fairness."""
        h = self.HITBOX
        return pygame.Rect(self.x - h, self.y - h, h * 2, h * 2)


# ══════════════════════════════════════════════
# PIPE PAIR
# ══════════════════════════════════════════════
class Pipe:
    W = 65      # pipe width

    def __init__(self, gap_cy, gap, speed, moving=False):
        self.x       = float(SCREEN_W + 10)
        self.gap_cy  = float(gap_cy)    # centre Y of gap
        self.gap     = gap
        self.speed   = speed
        self.moving  = moving
        self.mv_dir  = 1
        self.passed  = False

    def update(self):
        self.x -= self.speed
        if self.moving:
            self.gap_cy += self.mv_dir * 1.4
            if self.gap_cy < 160 or self.gap_cy > GROUND_Y - 160:
                self.mv_dir *= -1

    def draw(self, surf):
        top_h = self.gap_cy - self.gap // 2
        bot_y = self.gap_cy + self.gap // 2
        bot_h = GROUND_Y - bot_y
        self._segment(surf, self.x, 0,     self.W, top_h, cap_bottom=True)
        self._segment(surf, self.x, bot_y, self.W, bot_h, cap_bottom=False)

    @staticmethod
    def _segment(surf, x, y, w, h, cap_bottom):
        if h <= 0:
            return
        CAP_H = 22
        CAP_X = x - 7
        CAP_W = w + 14
        # body
        pygame.draw.rect(surf, PIPE_GREEN, (x, y, w, h))
        pygame.draw.rect(surf, PIPE_LIGHT, (x + 5, y, 10, h))          # highlight
        pygame.draw.rect(surf, PIPE_DARK,  (x + w - 10, y, 10, h))     # shadow
        pygame.draw.rect(surf, (35, 95, 15), (x, y, w, h), 2)          # outline
        # cap
        cap_y = (y + h - CAP_H) if cap_bottom else y
        pygame.draw.rect(surf, PIPE_GREEN, (CAP_X, cap_y, CAP_W, CAP_H))
        pygame.draw.rect(surf, PIPE_LIGHT, (CAP_X + 6, cap_y, 12, CAP_H))
        pygame.draw.rect(surf, PIPE_DARK,  (CAP_X + CAP_W - 12, cap_y, 12, CAP_H))
        pygame.draw.rect(surf, (35, 95, 15), (CAP_X, cap_y, CAP_W, CAP_H), 2)

    def rects(self):
        """Two collision rects (top pipe + bottom pipe)."""
        top_h = int(self.gap_cy - self.gap / 2)
        bot_y = int(self.gap_cy + self.gap / 2)
        bot_h = GROUND_Y - bot_y
        cx    = int(self.x) - 7
        cw    = self.W + 14
        rs = []
        if top_h > 0: rs.append(pygame.Rect(cx, 0, cw, top_h))
        if bot_h > 0: rs.append(pygame.Rect(cx, bot_y, cw, bot_h))
        return rs

    @property
    def off_screen(self):
        return self.x + self.W + 20 < 0


# ══════════════════════════════════════════════
# CLOUD
# ══════════════════════════════════════════════
class Cloud:
    def __init__(self, x=None):
        self.x    = float(x if x is not None else SCREEN_W + random.randint(10, 300))
        self.y    = float(random.randint(40, GROUND_Y - 250))
        self.s    = random.randint(28, 70)
        self.spd  = random.uniform(0.25, 0.65)

    def update(self, pipe_spd):
        self.x -= self.spd * (pipe_spd / 3.0)

    def draw(self, surf):
        x, y, s = int(self.x), int(self.y), self.s
        c = (240, 245, 255)
        pygame.draw.ellipse(surf, c, (x,         y,         s * 2, s    ))
        pygame.draw.ellipse(surf, c, (x + s//3,  y - s//2,  s,     s    ))
        pygame.draw.ellipse(surf, c, (x + s,     y - s//4,  int(s*.8), int(s*.8)))

    @property
    def off_screen(self):
        return self.x + self.s * 3 < 0


# ══════════════════════════════════════════════
# PARTICLE
# ══════════════════════════════════════════════
class Particle:
    def __init__(self, x, y, color):
        angle = random.uniform(0, math.tau)
        spd   = random.uniform(1.5, 5.5)
        self.x   = float(x)
        self.y   = float(y)
        self.vx  = math.cos(angle) * spd
        self.vy  = math.sin(angle) * spd - random.uniform(1, 3)
        self.color = color
        self.life  = random.randint(30, 55)
        self.maxl  = self.life
        self.r     = random.randint(3, 7)

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.18
        self.life -= 1

    def draw(self, surf):
        a = int(255 * self.life / self.maxl)
        r = max(1, int(self.r * (self.life / self.maxl)))
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, a), (r, r), r)
        surf.blit(s, (int(self.x - r), int(self.y - r)))

    @property
    def dead(self):
        return self.life <= 0


# ══════════════════════════════════════════════
# SCORE POP  (floating "+1" text)
# ══════════════════════════════════════════════
class ScorePop:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.life = 45

    def update(self):
        self.y   -= 1.1
        self.life -= 1

    def draw(self, surf):
        a = int(255 * self.life / 45)
        s = font_small.render("+1", True, YELLOW)
        s.set_alpha(a)
        surf.blit(s, (int(self.x) - s.get_width()//2, int(self.y)))

    @property
    def dead(self):
        return self.life <= 0


# ══════════════════════════════════════════════
# CACHED GRADIENT BACKGROUNDS
# ══════════════════════════════════════════════
_bg_cache: dict = {}

def get_bg(level: int) -> pygame.Surface:
    if level not in _bg_cache:
        cfg = LEVEL_CFG[level]
        s   = pygame.Surface((SCREEN_W, SCREEN_H))
        top = cfg["sky_top"]
        bot = cfg["sky_bot"]
        for i in range(SCREEN_H):
            t = i / SCREEN_H
            pygame.draw.line(s, lerp_color(top, bot, t), (0, i), (SCREEN_W, i))
        _bg_cache[level] = s
    return _bg_cache[level]


# ══════════════════════════════════════════════
# MAIN GAME CLASS
# ══════════════════════════════════════════════
class Game:
    # states: "menu" | "playing" | "dead" | "level_up"
    def __init__(self):
        self.hi_score  = 0
        self.state     = "menu"
        self.menu_bird = Bird(SCREEN_W // 2, SCREEN_H // 2)
        self.menu_clouds = [Cloud(random.randint(0, SCREEN_W)) for _ in range(6)]
        self._reset(1)

    # ── level / game reset ─────────────────────
    def _reset(self, level=1):
        cfg = LEVEL_CFG[level]
        self.level        = level
        self.score        = 0
        self.bird         = Bird()
        self.pipes        : list[Pipe]      = []
        self.particles    : list[Particle]  = []
        self.score_pops   : list[ScorePop]  = []
        self.clouds       : list[Cloud]     = [
            Cloud(random.randint(0, SCREEN_W)) for _ in range(5)
        ]
        self.pipe_timer   = 0
        self.ground_off   = 0.0   # scrolling offset for ground stripes
        self.death_timer  = 0
        self.lu_timer     = 0     # level-up overlay timer

    # ── public entry points ────────────────────
    def handle_event(self, ev):
        flap_keys  = {pygame.K_SPACE, pygame.K_UP, pygame.K_w}
        flap_mouse = {1}   # left button

        if ev.type == pygame.KEYDOWN:
            if self.state == "menu" and ev.key in flap_keys:
                self._start()
            elif self.state == "playing" and ev.key in flap_keys:
                self.bird.flap()
            elif self.state == "dead" and self.death_timer > 70:
                if ev.key in flap_keys:
                    self._reset(1); self.state = "playing"
                elif ev.key == pygame.K_m:
                    self._reset(1); self.state = "menu"

        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button in flap_mouse:
            if self.state == "menu":
                self._start()
            elif self.state == "playing":
                self.bird.flap()
            elif self.state == "dead" and self.death_timer > 70:
                mx, my = ev.pos
                r_btn, m_btn = self._dead_buttons()
                if r_btn.collidepoint(mx, my):
                    self._reset(1); self.state = "playing"
                elif m_btn.collidepoint(mx, my):
                    self._reset(1); self.state = "menu"

    def update(self):
        cfg = LEVEL_CFG[self.level]

        # ── MENU idle animation ──────────────────
        if self.state == "menu":
            t = pygame.time.get_ticks() / 1000
            self.menu_bird.y  = SCREEN_H // 2 + math.sin(t * 2.2) * 18
            self.menu_bird.angle = math.sin(t * 2.2) * 12
            for c in self.menu_clouds:
                c.update(3)
            self.menu_clouds = [c for c in self.menu_clouds if not c.off_screen]
            if len(self.menu_clouds) < 7 and random.random() < 0.015:
                self.menu_clouds.append(Cloud())
            return

        # ── LEVEL-UP pause ───────────────────────
        if self.state == "level_up":
            self.lu_timer -= 1
            self._update_particles()
            if self.lu_timer <= 0:
                nxt = self.level + 1
                self._reset(nxt)
                self.state = "playing"
            return

        # ── DEAD ─────────────────────────────────
        if self.state == "dead":
            self.death_timer += 1
            self.bird.update()          # let bird fall naturally
            self.bird.y = min(self.bird.y, GROUND_Y - Bird.HITBOX)
            self._update_particles()
            return

        # ── PLAYING ──────────────────────────────
        self.bird.update()
        self.ground_off = (self.ground_off - cfg["pipe_speed"]) % 32

        # clouds
        for c in self.clouds:
            c.update(cfg["pipe_speed"])
        self.clouds = [c for c in self.clouds if not c.off_screen]
        if len(self.clouds) < 6 and random.random() < 0.012:
            self.clouds.append(Cloud())

        # pipes
        self.pipe_timer += 1
        if self.pipe_timer >= cfg["pipe_freq"]:
            self.pipe_timer = 0
            gap_cy = random.randint(170, GROUND_Y - 170)
            self.pipes.append(
                Pipe(gap_cy, cfg["gap"], cfg["pipe_speed"], cfg["moving"])
            )

        for p in self.pipes:
            p.update()
            if not p.passed and p.x + p.W < self.bird.x:
                p.passed = True
                self.score += 1
                self.score_pops.append(ScorePop(self.bird.x, self.bird.y - 35))
                self._burst(self.bird.x, self.bird.y, YELLOW, 8)

        self.pipes = [p for p in self.pipes if not p.off_screen]

        # ── COLLISION ────────────────────────────
        brc = self.bird.rect.inflate(-4, -4)   # extra shrink = more forgiving
        hit = False

        # ground
        if self.bird.y + Bird.HITBOX >= GROUND_Y:
            hit = True
        # ceiling
        if self.bird.y - Bird.HITBOX <= 0:
            hit = True
        # pipes
        if not hit:
            for p in self.pipes:
                for pr in p.rects():
                    if brc.colliderect(pr):
                        hit = True
                        break

        if hit:
            self._die()
            return

        # ── LEVEL UP CHECK ───────────────────────
        if self.score >= cfg["score_next"] and self.level < 4:
            self.state    = "level_up"
            self.lu_timer = 130
            self._burst(SCREEN_W // 2, SCREEN_H // 2, (255, 210, 50), 55)
            self._burst(SCREEN_W // 4, SCREEN_H // 3, (100, 200, 255), 25)
            self._burst(3 * SCREEN_W // 4, SCREEN_H // 3, (255, 120, 50), 25)

        self._update_particles()

    def draw(self, surf):
        if self.state == "menu":
            self._draw_menu(surf)
        elif self.state in ("playing", "dead", "level_up"):
            self._draw_game(surf)

    # ── PRIVATE ───────────────────────────────────────────────────────────────
    def _start(self):
        self._reset(1)
        self.state = "playing"

    def _die(self):
        self.state       = "dead"
        self.death_timer = 0
        if self.score > self.hi_score:
            self.hi_score = self.score
        self._burst(self.bird.x, self.bird.y, (255, 70, 50), 30)

    def _burst(self, x, y, color, n=12):
        for _ in range(n):
            self.particles.append(Particle(x, y, color))

    def _update_particles(self):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if not p.dead]
        for sp in self.score_pops:
            sp.update()
        self.score_pops = [sp for sp in self.score_pops if not sp.dead]

    # ── DRAW HELPERS ──────────────────────────────────────────────────────────
    def _draw_ground(self, surf):
        pygame.draw.rect(surf, GROUND_TOP,  (0, GROUND_Y,      SCREEN_W, 14))
        pygame.draw.rect(surf, GROUND_TAN,  (0, GROUND_Y + 14, SCREEN_W, SCREEN_H - GROUND_Y))
        stripe_w = 32
        for i in range(-1, SCREEN_W // stripe_w + 2):
            sx = i * stripe_w + int(self.ground_off)
            pygame.draw.rect(surf, GROUND_DARK, (sx, GROUND_Y + 14, 16, SCREEN_H - GROUND_Y))

    def _draw_hud(self, surf):
        cfg   = LEVEL_CFG[self.level]
        # Score (centered, large)
        sw, _ = text_shadow(
            surf, font_xl, str(self.score), WHITE,
            SCREEN_W // 2 - font_xl.size(str(self.score))[0] // 2, 20
        )
        # Level badge
        colors = {1:(50,200,80), 2:(50,130,255), 3:(255,140,40), 4:(220,50,50)}
        lc     = colors[self.level]
        badge  = pygame.Rect(10, 10, 130, 36)
        rrect(surf, lc, badge, 10, BLACK, 2)
        text_shadow(surf, font_small, f"LV{self.level}  {cfg['name']}",
                    WHITE, badge.x + 8, badge.y + 7, offset=1)
        # Score pops
        for sp in self.score_pops:
            sp.draw(surf)

    def _dead_buttons(self):
        cy     = SCREEN_H // 2 + 90
        r_btn  = pygame.Rect(SCREEN_W // 2 - 140, cy, 125, 50)
        m_btn  = pygame.Rect(SCREEN_W // 2 + 15,  cy, 125, 50)
        return r_btn, m_btn

    # ── SCENE DRAWS ───────────────────────────────────────────────────────────
    def _draw_menu(self, surf):
        surf.blit(get_bg(1), (0, 0))

        for c in self.menu_clouds:
            c.draw(surf)

        # ground (no scroll on menu)
        pygame.draw.rect(surf, GROUND_TOP,  (0, GROUND_Y, SCREEN_W, 14))
        pygame.draw.rect(surf, GROUND_TAN,  (0, GROUND_Y + 14, SCREEN_W, 200))

        # title card
        card = pygame.Rect(SCREEN_W // 2 - 175, 60, 350, 120)
        rrect(surf, (0, 0, 0), card, 18, WHITE, 3)
        text_shadow(surf, font_large, "FLAPPY",  YELLOW,
                    SCREEN_W // 2 - font_large.size("FLAPPY")[0] // 2, 70)
        text_shadow(surf, font_large, "BIRD",    WHITE,
                    SCREEN_W // 2 - font_large.size("BIRD")[0]   // 2, 118)

        # animated bird
        self.menu_bird.draw(surf)

        # start prompt  (pulsing)
        a = int(180 + 75 * math.sin(pygame.time.get_ticks() / 400))
        btn = pygame.Rect(SCREEN_W // 2 - 140, 415, 280, 58)
        rrect(surf, (40, 175, 40), btn, 16, WHITE, 3)
        ps = font_med.render("SPACE / CLICK", True, WHITE)
        ps.set_alpha(a)
        surf.blit(ps, (SCREEN_W // 2 - ps.get_width() // 2, 428))

        # level info cards
        lv_colors = [(50,200,80),(50,130,255),(255,140,40),(220,50,50)]
        for i, (lv, lcfg) in enumerate(LEVEL_CFG.items()):
            lx = 14 + i * 115
            ly = 510
            r  = pygame.Rect(lx, ly, 108, 68)
            rrect(surf, lv_colors[i], r, 10, WHITE, 2)
            text_shadow(surf, font_small, f"Lv {lv}", WHITE,
                        lx + 54 - font_small.size(f"Lv {lv}")[0]//2, ly + 6, offset=1)
            nt = font_tiny.render(lcfg["name"], True, WHITE)
            surf.blit(nt, (lx + 54 - nt.get_width()//2, ly + 36))
            # score threshold label
            sc_lbl = font_tiny.render(
                "∞" if lcfg["score_next"] > 900 else f">{lcfg['score_next']}pts", True, (220,220,220))
            surf.blit(sc_lbl, (lx + 54 - sc_lbl.get_width()//2, ly + 50))

        # high score
        if self.hi_score > 0:
            text_shadow(surf, font_small, f"Best  {self.hi_score}", YELLOW,
                        SCREEN_W // 2 - font_small.size(f"Best  {self.hi_score}")[0] // 2,
                        600, offset=1)

    def _draw_game(self, surf):
        cfg = LEVEL_CFG[self.level]
        surf.blit(get_bg(self.level), (0, 0))

        for c in self.clouds:
            c.draw(surf)
        for p in self.pipes:
            p.draw(surf)
        for pt in self.particles:
            pt.draw(surf)

        self._draw_ground(surf)
        self.bird.draw(surf)
        self._draw_hud(surf)

        if self.state == "dead":
            self._draw_dead_overlay(surf)

        if self.state == "level_up":
            self._draw_level_up_overlay(surf)

    def _draw_dead_overlay(self, surf):
        # dim
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        surf.blit(ov, (0, 0))

        panel = pygame.Rect(SCREEN_W//2 - 185, SCREEN_H//2 - 190, 370, 330)
        rrect(surf, (22, 22, 50), panel, 20, WHITE, 3)

        text_shadow(surf, font_large, "GAME OVER", RED,
                    SCREEN_W//2 - font_large.size("GAME OVER")[0]//2,
                    SCREEN_H//2 - 180, offset=2)

        text_shadow(surf, font_med, f"Score  {self.score}", WHITE,
                    SCREEN_W//2 - font_med.size(f"Score  {self.score}")[0]//2,
                    SCREEN_H//2 - 105, offset=2)

        text_shadow(surf, font_med, f"Best   {self.hi_score}", YELLOW,
                    SCREEN_W//2 - font_med.size(f"Best   {self.hi_score}")[0]//2,
                    SCREEN_H//2 - 60, offset=2)

        lvl_cfg = LEVEL_CFG[self.level]
        lv_colors = {1:(50,200,80), 2:(50,130,255), 3:(255,140,40), 4:(220,50,50)}
        lc = lv_colors[self.level]
        lt = font_small.render(f"Level {self.level}  —  {lvl_cfg['name']}", True, lc)
        surf.blit(lt, (SCREEN_W//2 - lt.get_width()//2, SCREEN_H//2 - 10))

        if self.death_timer > 70:
            r_btn, m_btn = self._dead_buttons()
            rrect(surf, (45, 175, 45), r_btn, 13, WHITE, 2)
            rrect(surf, (70,  70, 180), m_btn, 13, WHITE, 2)
            rt = font_small.render("RETRY",  True, WHITE)
            mt = font_small.render("MENU",   True, WHITE)
            surf.blit(rt, (r_btn.centerx - rt.get_width()//2, r_btn.centery - rt.get_height()//2))
            surf.blit(mt, (m_btn.centerx - mt.get_width()//2, m_btn.centery - mt.get_height()//2))

            ht = font_tiny.render("SPACE = Retry   |   M = Menu", True, (170, 170, 170))
            surf.blit(ht, (SCREEN_W//2 - ht.get_width()//2, SCREEN_H//2 + 150))

    def _draw_level_up_overlay(self, surf):
        t = self.lu_timer / 130       # 1 → 0 as timer runs down
        # flash background
        glow = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        glow.fill((255, 215, 40, int(60 * t)))
        surf.blit(glow, (0, 0))

        nxt = self.level + 1
        panel = pygame.Rect(SCREEN_W//2 - 175, SCREEN_H//2 - 130, 350, 240)
        rrect(surf, (15, 15, 40), panel, 22, YELLOW, 4)

        text_shadow(surf, font_large, "LEVEL UP!", YELLOW,
                    SCREEN_W//2 - font_large.size("LEVEL UP!")[0]//2,
                    SCREEN_H//2 - 120, offset=3)

        if nxt <= 4:
            ncfg = LEVEL_CFG[nxt]
            lv_colors = {1:(50,200,80), 2:(50,130,255), 3:(255,140,40), 4:(220,50,50)}
            lc  = lv_colors[nxt]
            lt  = font_med.render(f"Level {nxt}  —  {ncfg['name']}", True, lc)
            surf.blit(lt, (SCREEN_W//2 - lt.get_width()//2, SCREEN_H//2 - 45))

            tips = {
                2: "Pipes are faster!",
                3: "Narrower gaps!",
                4: "Pipes move vertically!",
            }
            tip = font_small.render(tips.get(nxt, ""), True, WHITE)
            surf.blit(tip, (SCREEN_W//2 - tip.get_width()//2, SCREEN_H//2 + 5))

        # countdown bar
        bar_w = int(300 * t)
        pygame.draw.rect(surf, (80, 80, 80), (SCREEN_W//2 - 150, SCREEN_H//2 + 60, 300, 12), border_radius=6)
        pygame.draw.rect(surf, YELLOW,        (SCREEN_W//2 - 150, SCREEN_H//2 + 60, bar_w, 12), border_radius=6)


# ══════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════
def main():
    game = Game()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            game.handle_event(ev)

        game.update()
        game.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()