from utils import resource_path

def run_balloon_game(level):
    """
    AR Balloon Rehabilitation Game
    Returns: (score, accuracy, avg_response_time, motor_index)
    Press ESC at any time to exit back to the main UI.
    """
 
    import pygame
    import cv2
    import numpy as np
    import mediapipe as mp
    import math
    import random
    import time
    import os
    from PIL import Image as PILImage
 
    # ── Resolution ────────────────────────────────────────────────────────────
    WIDTH, HEIGHT = 1920, 1080
    FPS = 30

    # ── Level configs per difficulty ──────────────────────────────────────────
    # Each entry: (needed_targets, time_limit_seconds)
    LEVEL_CONFIGS = {
        "Easy": [
            (4,  45.0),
            (5,  43.0),
            (6,  41.0),
            (7,  39.0),
            (8,  37.0),
        ],
        "Medium": [
            (6,  45.0),
            (8,  43.5),
            (10, 41.0),
            (10, 39.5),
            (10, 38.0),
        ],
        "Hard": [
            (6,  35.0),
            (7,  33.0),
            (8,  31.0),
            (9,  30.0),
            (10, 29.0),
        ],
    }

    MAX_LEVELS = 5

    # ── Difficulty spawn / speed settings ────────────────────────────────────
    if level == "Easy":
        spawn_interval  = 20
        target_prob     = 0.45
        balloon_speed   = (0.8, 1.4)
        time_bonus      = 2.0          # seconds added per correct drop
    elif level == "Hard":
        spawn_interval  = 20
        target_prob     = 0.45
        balloon_speed   = (0.8, 1.4)
        time_bonus      = 1.0
    else:  # Medium (default)
        spawn_interval  = 20
        target_prob     = 0.45
        balloon_speed   = (0.8, 1.4)
        time_bonus      = 1.5

    def get_level_config(diff, lvl_index):
        """Return (needed_targets, time_limit) for given difficulty and 0-based level index."""
        configs = LEVEL_CONFIGS.get(diff, LEVEL_CONFIGS["Medium"])
        idx = min(lvl_index, len(configs) - 1)
        return configs[idx]

    # ── Pygame init ───────────────────────────────────────────────────────────
    pygame.init()
    win = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    pygame.display.set_caption("AR Rehab – Balloon")
    clock = pygame.time.Clock()
 
    font          = pygame.font.SysFont("arial", 30, bold=True)
    title_font    = pygame.font.SysFont("arial", 42, bold=True)
    feedback_font = pygame.font.SysFont("arial", 36, bold=True)
    hint_font     = pygame.font.SysFont("arial", 22)
    bar_font      = pygame.font.SysFont("arial", 20, bold=True)

    # ── Camera + MediaPipe ────────────────────────────────────────────────────
    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH,  WIDTH)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
 
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )
 
    # ── Helpers ───────────────────────────────────────────────────────────────
    def dist(p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])
 
    def dynamic_pinch(hand, threshold):
        index  = hand.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
        thumb  = hand.landmark[mp_hands.HandLandmark.THUMB_TIP]
        wrist  = hand.landmark[mp_hands.HandLandmark.WRIST]
        m_mcp  = hand.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
        pd     = dist((index.x, index.y), (thumb.x, thumb.y))
        scale  = dist((wrist.x, wrist.y), (m_mcp.x, m_mcp.y))
        return pd < threshold * scale
 
    def load_image(rel_path, size):
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            full = os.path.join(base, rel_path)
            img  = PILImage.open(full).convert("RGBA")
            data = []
            for px in img.getdata():
                if (px[0] > 220 and px[1] > 220 and px[2] > 220) or \
                   (px[0] < 15  and px[1] < 15  and px[2] < 15):
                    data.append((255, 255, 255, 0))
                else:
                    data.append(px)
            img.putdata(data)
            bb = img.getbbox()
            if bb:
                img = img.crop(bb)
            surf = pygame.image.fromstring(img.tobytes(), img.size, "RGBA").convert_alpha()
            return pygame.transform.smoothscale(surf, size)
        except Exception as e:
            print(f"[BalloonRehab] Image load error: {e}")
            surf = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.circle(surf, (200, 200, 200, 150),
                               (size[0]//2, size[1]//2), size[0]//2)
            return surf
 
    BALLOON_SIZE = (110, 110)
    balloon_images = {
        "red":    load_image(resource_path("Images/red_ballon.png"),    BALLOON_SIZE),
        "green":  load_image(resource_path("Images/Green_ballon.png"),  BALLOON_SIZE),
        "yellow": load_image(resource_path("Images/Yellom_ballon.png"), BALLOON_SIZE),
        "star":   load_image(resource_path("Images/Star_ballon.png"),   BALLOON_SIZE),
        "moon":   load_image(resource_path("Images/Moon_ballon.png"),   BALLOON_SIZE),
        "heart":  load_image(resource_path("Images/Heart_ballon.png"),  BALLOON_SIZE),
    }
    basket_img = load_image(resource_path("Images/Basket.png"), (175, 175))

    # ── Balloon class ─────────────────────────────────────────────────────────
    class Balloon:
        def __init__(self, x, y, pic, vx, vy, is_target):
            self.x, self.y = x, y
            self.pic = pic
            self.vx, self.vy = vx, vy
            self.is_target = is_target
            self.w = pic.get_width()
            self.h = pic.get_height()
            self.spawn_time = time.time()
 
        def update(self):
            self.x += self.vx
            self.y -= self.vy
            if self.x < 0 or self.x > WIDTH - self.w:
                self.vx *= -1
 
        def draw(self):
            win.blit(self.pic, (self.x, self.y))
 
        def rect(self):
            return pygame.Rect(self.x, self.y, self.w, self.h)

    # ── HUD helpers ───────────────────────────────────────────────────────────
    COLOR_GREEN  = (0, 230, 80)
    COLOR_WHITE  = (255, 255, 255)
    COLOR_YELLOW = (255, 220, 0)
    COLOR_RED    = (255, 60, 60)

    # Semi-transparent pill/panel background for HUD
    def draw_hud_panel(x, y, w, h, alpha=160):
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, alpha))
        pygame.draw.rect(panel, (0, 200, 80, 80), (0, 0, w, h), 2, border_radius=12)
        win.blit(panel, (x, y))

    def draw_centered_text(surf, text, color, font_obj, cy, outline_color=(0, 0, 0)):
        """Draw text horizontally centered on surf with a thin outline for readability."""
        tw = font_obj.size(text)[0]
        x  = (WIDTH - tw) // 2
        # Outline
        for dx, dy in ((-1,0),(1,0),(0,-1),(0,1)):
            win.blit(font_obj.render(text, True, outline_color), (x+dx, cy+dy))
        win.blit(font_obj.render(text, True, color), (x, cy))

    def draw_timer_bar(time_left, time_total, bar_y):
        """Draw a green→red progress bar at top-center showing time remaining."""
        BAR_W  = 600
        BAR_H  = 22
        BAR_X  = (WIDTH - BAR_W) // 2
        # Background track
        pygame.draw.rect(win, (40, 40, 40, 200), (BAR_X, bar_y, BAR_W, BAR_H), border_radius=10)
        # Fill
        ratio = max(0.0, time_left / time_total)
        fill_w = int(BAR_W * ratio)
        if ratio > 0.5:
            bar_color = COLOR_GREEN
        elif ratio > 0.25:
            bar_color = COLOR_YELLOW
        else:
            bar_color = COLOR_RED
        if fill_w > 0:
            pygame.draw.rect(win, bar_color, (BAR_X, bar_y, fill_w, BAR_H), border_radius=10)
        # Border
        pygame.draw.rect(win, COLOR_WHITE, (BAR_X, bar_y, BAR_W, BAR_H), 2, border_radius=10)
        # Label
        label = bar_font.render(f"{max(0, time_left):.1f}s", True, COLOR_WHITE)
        win.blit(label, (BAR_X + BAR_W + 10, bar_y + 2))

    # ── Session state ─────────────────────────────────────────────────────────
    balloons         = []
    held_balloon     = None
    hand_trail       = []
    TRAIL_LEN        = 12
 
    target_colour    = random.choice(list(balloon_images.keys()))
    score            = 0
    game_level       = 1          # 1-based display
    level_index      = 0          # 0-based for config lookup
    collected        = 0
 
    needed_per_level, level_time_limit = get_level_config(level, level_index)
    level_start_time = time.time()
    time_bonus_display       = 0.0   # shown in HUD briefly after a correct drop
    time_bonus_display_timer = 0

    # game_over screen state
    game_over          = False
    game_over_choice   = None        # None | "retry" | "quit"
    failed_level_index = 0
    failed_game_level  = 1

    # DDA
    pinch_threshold  = 0.35
    MIN_THRESH       = 0.28
    MAX_THRESH       = 0.55
    hover_start_time = 0
    hover_balloon    = None
 
    feedback_text    = ""
    feedback_color   = COLOR_WHITE
    feedback_timer   = 0

    BASKET_ZONES = [
        (WIDTH - 180, 40),
        (40, 40),
        (WIDTH//2 - 65, 40),
        (40, HEIGHT - 180),
        (WIDTH - 180, HEIGHT - 180),
        (WIDTH//2 - 65, HEIGHT - 180),
    ]
    basket_zone_index  = 0
    basket_moved_timer = 0
    basket_rect        = pygame.Rect(BASKET_ZONES[0][0], BASKET_ZONES[0][1], 130, 130)

    def next_basket_position():
        nonlocal basket_zone_index, basket_rect, basket_moved_timer
        basket_zone_index = (basket_zone_index + 1) % len(BASKET_ZONES)
        bx, by = BASKET_ZONES[basket_zone_index]
        basket_rect        = pygame.Rect(bx, by, 130, 130)
        basket_moved_timer = time.time()

    spawn_timer       = 0
    response_times    = []
    correct_drops     = 0
    total_drops       = 0
    running           = True
    aborted           = False
    wrong_color_drops = 0
    missed_basket     = 0



    # ── Game-over screen helper ───────────────────────────────────────────────
    def draw_game_over_screen(failed_lvl, frame_surf):
        """Blocking loop that shows FAIL screen; returns 'retry' or 'quit'."""
        big_font    = pygame.font.SysFont("arial", 64, bold=True)
        med_font    = pygame.font.SysFont("arial", 36, bold=True)
        small_font  = pygame.font.SysFont("arial", 26)

        BTN_W, BTN_H = 340, 70
        btn_retry = pygame.Rect(WIDTH // 2 - BTN_W - 30, HEIGHT // 2 + 60, BTN_W, BTN_H)
        btn_quit  = pygame.Rect(WIDTH // 2 + 30,          HEIGHT // 2 + 60, BTN_W, BTN_H)

        # Darken the last frame for atmosphere
        dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 180))

        while True:
            win.blit(frame_surf, (0, 0))
            win.blit(dark, (0, 0))

            # Panel
            panel_w, panel_h = 860, 320
            panel_x = (WIDTH - panel_w) // 2
            panel_y = HEIGHT // 2 - 180
            panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel.fill((10, 10, 10, 210))
            pygame.draw.rect(panel, (200, 50, 50, 180), (0, 0, panel_w, panel_h), 3, border_radius=18)
            win.blit(panel, (panel_x, panel_y))

            # Title
            title_surf = big_font.render("⏱  TIME'S UP!", True, COLOR_RED)
            win.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, panel_y + 24))

            # Subtitle
            sub = med_font.render(f"You ran out of time on Level {failed_lvl}", True, COLOR_WHITE)
            win.blit(sub, (WIDTH // 2 - sub.get_width() // 2, panel_y + 110))

            hint = small_font.render("Retry from this level  —  or  —  quit to menu", True, (180, 180, 180))
            win.blit(hint, (WIDTH // 2 - hint.get_width() // 2, panel_y + 158))

            # Buttons
            mouse = pygame.mouse.get_pos()
            for btn, label, col_n, col_h in [
                (btn_retry, "▶  Try Again (Level {})".format(failed_lvl), (0, 150, 60),  (0, 200, 80)),
                (btn_quit,  "✕  Quit to Menu",                             (140, 30, 30), (200, 50, 50)),
            ]:
                color = col_h if btn.collidepoint(mouse) else col_n
                pygame.draw.rect(win, color, btn, border_radius=12)
                pygame.draw.rect(win, COLOR_WHITE, btn, 2, border_radius=12)
                lbl = med_font.render(label, True, COLOR_WHITE)
                win.blit(lbl, (btn.x + (BTN_W - lbl.get_width()) // 2,
                                btn.y + (BTN_H - lbl.get_height()) // 2))

            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return "quit"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_retry.collidepoint(event.pos):
                        return "retry"
                    if btn_quit.collidepoint(event.pos):
                        return "quit"

    # ── Main loop ─────────────────────────────────────────────────────────────
    last_good_frame = None   # keep a snapshot for the game-over screen

    while running:
        ret, frame = cam.read()
        if not ret:
            continue
 
        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (WIDTH, HEIGHT))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame)
 
        frame_surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        last_good_frame = frame_surf.copy()
        win.blit(frame_surf, (0, 0))
 
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 60))
        win.blit(overlay, (0, 0))
 
        hand_pos = None
        pinch    = False

        # ── Time remaining ───────────────────────────────────────────────────
        elapsed   = time.time() - level_start_time
        time_left = max(0.0, level_time_limit - elapsed)

        # ── Events ───────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                aborted = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    aborted = True
                elif event.key == pygame.K_r: target_colour = "red";    balloons.clear(); collected = 0
                elif event.key == pygame.K_g: target_colour = "green";  balloons.clear(); collected = 0
                elif event.key == pygame.K_y: target_colour = "yellow"; balloons.clear(); collected = 0
                elif event.key == pygame.K_s: target_colour = "star";   balloons.clear(); collected = 0
                elif event.key == pygame.K_m: target_colour = "moon";   balloons.clear(); collected = 0
                elif event.key == pygame.K_h: target_colour = "heart";  balloons.clear(); collected = 0

        if aborted:
            break

        # ── Timer expiry → FAIL ───────────────────────────────────────────────
        if time_left <= 0:
            pygame.display.update()          # show last frame before blocking
            choice = draw_game_over_screen(game_level, last_good_frame)
            if choice == "retry":
                # Reset to the level that failed; keep score
                collected        = 0
                balloons.clear()
                held_balloon     = None
                target_colour    = random.choice(list(balloon_images.keys()))
                needed_per_level, level_time_limit = get_level_config(level, level_index)
                level_start_time = time.time()
                next_basket_position()
            else:
                running = False
                aborted = True
            continue

        # ── Balloon spawning ──────────────────────────────────────────────────
        spawn_timer += 1
        if spawn_timer > spawn_interval:
            spawn_timer = 0
            col = target_colour if random.random() < target_prob else \
                  random.choice([c for c in balloon_images if c != target_colour])
            bx  = random.randint(50, WIDTH - 140)
            by  = random.randint(int(HEIGHT * 0.5), HEIGHT - 120)
            vx  = random.uniform(-0.5, 0.5)
            vy  = random.uniform(*balloon_speed)
            balloons.append(
                Balloon(bx, by, balloon_images[col], vx, vy, col == target_colour)
            )

        # ── Hand tracking ─────────────────────────────────────────────────────
        if results.multi_hand_landmarks:
            hand = results.multi_hand_landmarks[0]
            t = (int(hand.landmark[4].x  * WIDTH), int(hand.landmark[4].y  * HEIGHT))
            i = (int(hand.landmark[8].x  * WIDTH), int(hand.landmark[8].y  * HEIGHT))
            m = (int(hand.landmark[12].x * WIDTH), int(hand.landmark[12].y * HEIGHT))
            hand_pos = ((t[0]+i[0]+m[0])//3, (t[1]+i[1]+m[1])//3)

            hand_trail.append(hand_pos)
            if len(hand_trail) > TRAIL_LEN:
                hand_trail.pop(0)
            for idx, p in enumerate(hand_trail):
                pygame.draw.circle(win, (0, 150, 255), p, int(2 + idx / 2))

            pinch = dynamic_pinch(hand, pinch_threshold)

            if not held_balloon:
                hovering = False
                for b in balloons:
                    if b.rect().collidepoint(hand_pos):
                        hovering = True
                        if hover_balloon != b:
                            hover_balloon     = b
                            hover_start_time  = time.time()
                        if time.time() - hover_start_time > 1.2:
                            pinch_threshold = min(pinch_threshold + 0.01, MAX_THRESH)
                        break
                if not hovering:
                    hover_balloon = None

            c = COLOR_GREEN if pinch else COLOR_WHITE
            w = 3 if pinch else 1
            pygame.draw.line(win, c, t, i, w)
            pygame.draw.line(win, c, i, m, w)
            pygame.draw.line(win, c, m, t, w)

            if pinch and held_balloon is None:
                for b in balloons:
                    if b.rect().collidepoint(hand_pos):
                        held_balloon = b
                        balloons.remove(b)
                        break

            if held_balloon:
                held_balloon.x = hand_pos[0] - held_balloon.w // 2
                held_balloon.y = hand_pos[1] - held_balloon.h // 2
                held_balloon.draw()

                if not pinch:
                    total_drops += 1
                    bc = (held_balloon.x + held_balloon.w // 2,
                          held_balloon.y + held_balloon.h // 2)
                    if basket_rect.collidepoint(bc):
                        if held_balloon.is_target:
                            score     += 10
                            collected += 1
                            correct_drops += 1
                            rt = time.time() - held_balloon.spawn_time
                            response_times.append(rt)
                            pinch_threshold = max(pinch_threshold - 0.005, MIN_THRESH)
                            # ── Time bonus ──────────────────────────────────
                            level_time_limit      += time_bonus
                            time_bonus_display     = time_bonus
                            time_bonus_display_timer = time.time()
                            feedback_text, feedback_color = "✓ CORRECT!", COLOR_GREEN
                        else:
                            feedback_text, feedback_color = "✗ WRONG COLOR!", (255, 165, 0)
                    else:
                        feedback_text, feedback_color = "MISSED BASKET!", COLOR_RED
                    feedback_timer = time.time()
                    held_balloon   = None
        else:
            hand_trail.clear()

        # ── Render balloons ───────────────────────────────────────────────────
        win.blit(basket_img, (basket_rect.x, basket_rect.y))

        if time.time() - basket_moved_timer < 1.5:
            pulse = int(abs(math.sin(time.time() * 6)) * 255)
            flash = pygame.Surface((130, 130), pygame.SRCALPHA)
            flash.fill((255, 255, 0, pulse // 3))
            win.blit(flash, (basket_rect.x, basket_rect.y))
            arrow = feedback_font.render("DROP HERE!", True, COLOR_YELLOW)
            win.blit(arrow, (basket_rect.x - 20, basket_rect.y + 138))

        for b in balloons[:]:
            b.update()
            b.draw()
            if b.y + b.h < 0:
                balloons.remove(b)

        # ── Feedback text (near basket) ───────────────────────────────────────
        if time.time() - feedback_timer < 1.2:
            fb = feedback_font.render(feedback_text, True, feedback_color)
            win.blit(fb, (basket_rect.x - 20, basket_rect.y + 140))

        # ── Time-bonus pop-up (near bar) ─────────────────────────────────────
        if time_bonus_display > 0 and time.time() - time_bonus_display_timer < 1.0:
            bonus_surf = bar_font.render(f"+{time_bonus_display:.1f}s", True, COLOR_GREEN)
            bx = WIDTH // 2 + 320
            by = 84
            win.blit(bonus_surf, (bx, by))

        # ══════════════════════════════════════════════════════════════════════
        # ── TOP-CENTER HUD ────────────────────────────────────────────────────
        # ══════════════════════════════════════════════════════════════════════
        HUD_PANEL_W = 760
        HUD_PANEL_H = 110
        HUD_PANEL_X = (WIDTH - HUD_PANEL_W) // 2
        HUD_PANEL_Y = 8
        draw_hud_panel(HUD_PANEL_X, HUD_PANEL_Y, HUD_PANEL_W, HUD_PANEL_H)

        # Row 1: Target | Score | Level
        assist_pct = int(((pinch_threshold - MIN_THRESH) / (MAX_THRESH - MIN_THRESH)) * 100)
        row1 = f"🎈 Target: {target_colour.upper()}   |   Score: {score}   |   Level: {game_level}"
        draw_centered_text(win, row1, COLOR_GREEN, font, HUD_PANEL_Y + 10)

        # Row 2: Collected progress
        row2 = f"Collected: {collected} / {needed_per_level}   |   Assist: {assist_pct}%"
        draw_centered_text(win, row2, COLOR_WHITE, font, HUD_PANEL_Y + 46)

        # Row 3: Timer bar
        draw_timer_bar(time_left, level_time_limit, HUD_PANEL_Y + 84)

        # ── TOP-CENTER: Target change key hints ───────────────────────────────
        HINT_PANEL_W = 680
        HINT_PANEL_H = 32
        HINT_PANEL_X = (WIDTH - HINT_PANEL_W) // 2
        HINT_PANEL_Y = HUD_PANEL_Y + HUD_PANEL_H + 6
        draw_hud_panel(HINT_PANEL_X, HINT_PANEL_Y, HINT_PANEL_W, HINT_PANEL_H, alpha=120)
        hint_text = "Change Target → R: Red  G: Green  Y: Yellow  S: Star  M: Moon  H: Heart"
        draw_centered_text(win, hint_text, COLOR_WHITE, hint_font, HINT_PANEL_Y + 6)

        # ── Bottom ESC hint ───────────────────────────────────────────────────
        win.blit(hint_font.render("ESC = exit to menu", True, (180, 180, 180)), (16, HEIGHT - 34))

        # ── Level progression (target count reached) ──────────────────────────
        if collected >= needed_per_level:
            level_index      = min(level_index + 1, MAX_LEVELS - 1)
            game_level      += 1
            collected        = 0
            target_colour    = random.choice(list(balloon_images.keys()))
            balloons.clear()
            next_basket_position()
            needed_per_level, level_time_limit = get_level_config(level, level_index)
            level_start_time = time.time()

        pygame.display.update()
        clock.tick(FPS)
 
    # ── Cleanup ───────────────────────────────────────────────────────────────
    cam.release()
    cv2.destroyAllWindows()
    pygame.quit()
 
    # ── Metrics ───────────────────────────────────────────────────────────────
    accuracy    = (correct_drops / total_drops * 100) if total_drops > 0 else 0.0
    avg_rt      = (sum(response_times) / len(response_times)) if response_times else 0.0
    motor_index = (accuracy * 0.5) + ((1.0 / avg_rt) * 50 if avg_rt > 0 else 0)
 
    return score, accuracy, avg_rt, motor_index