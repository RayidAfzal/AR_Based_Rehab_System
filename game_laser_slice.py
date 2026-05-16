from utils import resource_path


def run_laser_game(level):
    """
    AR Laser Slice Rehabilitation Game
    Returns: (score, accuracy, avg_response_time, motor_index)
    Press ESC at any time to exit back to the main UI.
    """
 
    import pygame
    import cv2
    import numpy as np
    from random import randint
    import mediapipe as mp
    import time
    import math
 
    # ── Resolution ────────────────────────────────────────────────────────────
    W, H = 1920, 1080
 
    # ── Difficulty ───────────────────────────────────────────────────────────
    if level == "Easy":
        session_duration = 30
        spawn_every      = 60   # frames
        fruit_speed      = 8
    elif level == "Hard":
        session_duration = 30
        spawn_every      = 35
        fruit_speed      = 12
    else:  # Medium
        session_duration = 30
        spawn_every      = 45
        fruit_speed      = 10
 
    # ── Pygame init ───────────────────────────────────────────────────────────
    pygame.init()
    pygame.mixer.init()
    clock = pygame.time.Clock()
 
    mono24  = pygame.font.SysFont("monospace", 24)
    mono36  = pygame.font.SysFont("monospace", 36, bold=True)   # bigger HUD
    mono48  = pygame.font.SysFont("monospace", 48, bold=True)
    hint28  = pygame.font.SysFont("monospace", 28, bold=True)   # bigger hint
 
    win = pygame.display.set_mode((W, H), pygame.FULLSCREEN)
    pygame.display.set_caption("AR Rehab – Laser Slice")
 
    # ── Camera + MediaPipe ────────────────────────────────────────────────────
    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH,  W)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, H)
 
    mp_hands = mp.solutions.hands
    hands    = mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.85
    )
 
    # ── Asset helpers ─────────────────────────────────────────────────────────
    def load_image(path, size):
        try:
            return pygame.transform.scale(pygame.image.load(path), size)
        except Exception:
            s = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.circle(s, (200, 100, 50, 200),
                               (size[0]//2, size[1]//2), size[0]//2)
            return s
 
    def load_sound(path):
        try:
            return pygame.mixer.Sound(resource_path(path))
        except Exception:
            return None
 
    # Hologram hand
    def draw_hologram_hand(surface, hand_landmarks, t):
        pts = [(int(lm.x * W), int(lm.y * H))
               for lm in hand_landmarks.landmark]
        pulse = int(120 + 100 * math.sin(t * 3))
        for a, b in mp_hands.HAND_CONNECTIONS:
            pygame.draw.line(surface, (0, pulse, 255),      pts[a], pts[b], 6)
            pygame.draw.line(surface, (0, pulse//2, 180),   pts[a], pts[b], 2)
        for x, y in pts:
            pygame.draw.circle(surface, (0, pulse, 255), (x, y), 6)
            pygame.draw.circle(surface, (0, 180, 255),   (x, y), 3)
 
    # ── Assets ────────────────────────────────────────────────────────────────
    FRUIT_SIZE = (140, 140)
    watermelon = load_image(resource_path("images/watermelon1.png"), FRUIT_SIZE)
    berry      = load_image(resource_path("images/berry1.png"),      FRUIT_SIZE)
    orange     = load_image(resource_path("images/orange1.png"),     FRUIT_SIZE)
    fruits     = [watermelon, berry, orange]
 
    slice_snd  = load_sound("sounds/pidiche.wav")
    miss_snd   = load_sound("sounds/miss.wav")
 
    # ── Fruit class ───────────────────────────────────────────────────────────
    class Fruit:
        def __init__(self, x, y, pic, speed):
            self.x, self.y = x, y
            self.pic       = pic
            self.speed     = speed
            self.spawn_t   = time.time()
 
        def update(self):
            self.y += self.speed
 
        def draw(self):
            win.blit(self.pic, (self.x, self.y))
 
        def rect(self):
            return pygame.Rect(self.x, self.y,
                               self.pic.get_width(), self.pic.get_height())
 
    # ── Session variables ─────────────────────────────────────────────────────
    score           = 0
    fruits_list     = []
    spawn_timer     = 0
    reaction_times  = []
    total_spawned   = 0
 
    # Hand smoothing
    smx = smy = None
    smooth_alpha = 0.3

    # ── Pronation / supination gate ───────────────────────────────────────────
    # "Neutral" = hand flat / laser pointing straight up  (angle ≈ -π/2 ± threshold)
    NEUTRAL_THRESHOLD = 0.35          # radians (~20°) tolerance around -π/2
    NEUTRAL_ANGLE     = -math.pi / 2  # laser pointing straight up
    ready             = True          # True  → can slice & will spawn fruits
                                      # False → must return to neutral first
 
    # Laser circle (bottom-centre zone)
    cx = W // 2
    cy = int(H * 0.82)
    cr = 250        # radius (bigger on 1080p)
    LINE_LEN = 1750
 
    session_start = time.time()
    session_over  = False
    aborted       = False
 
    btn_rect = pygame.Rect(W//2 - 120, H//2 + 120, 240, 70)
 
    # ── Collision helper ──────────────────────────────────────────────────────
    def line_hits_rect(x1, y1, x2, y2, rect, steps=25):
        for i in range(steps + 1):
            t_ = i / steps
            px = x1 + (x2 - x1) * t_
            py = y1 + (y2 - y1) * t_
            if rect.collidepoint(px, py):
                return True
        return False
 
    def reset():
        nonlocal score, fruits_list, spawn_timer, reaction_times
        nonlocal total_spawned, smx, smy, session_start, session_over, ready
        score = spawn_timer = total_spawned = 0
        fruits_list = []
        reaction_times = []
        smx = smy = None
        session_start = time.time()
        session_over  = False
        ready         = True
 
    # ── Main loop ─────────────────────────────────────────────────────────────
    while True:
        ret, frame = cam.read()
        if not ret:
            continue
 
        frame      = cv2.flip(frame, 1)
        rgb_frame  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results    = hands.process(rgb_frame)
 
        hand_in_circle = False
        line_angle     = None
        hx = hy        = None
 
        # ── Hand tracking ─────────────────────────────────────────────────────
        if results.multi_hand_landmarks:
            for hl in results.multi_hand_landmarks:
                draw_hologram_hand(win, hl, time.time())
 
                imcp  = hl.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
                pmcp  = hl.landmark[mp_hands.HandLandmark.PINKY_MCP]
                wrist = hl.landmark[mp_hands.HandLandmark.WRIST]
 
                px = (imcp.x + pmcp.x + wrist.x) / 3
                py = (imcp.y + pmcp.y + wrist.y) / 3
                rx, ry = int(px * W), int(py * H)
 
                if smx is None:
                    smx, smy = rx, ry
                else:
                    smx = int(smooth_alpha * rx + (1 - smooth_alpha) * smx)
                    smy = int(smooth_alpha * ry + (1 - smooth_alpha) * smy)
 
                hx, hy = smx, smy
                hand_in_circle = math.hypot(hx - cx, hy - cy) < cr
 
                dx = imcp.x - pmcp.x
                dy = imcp.y - pmcp.y
                line_angle = math.atan2(dy, dx)

                # Gate: if not ready, check whether hand has returned to neutral
                if not ready and line_angle is not None:
                    if abs(line_angle - NEUTRAL_ANGLE) < NEUTRAL_THRESHOLD:
                        ready = True
 
        # ── Events ───────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                aborted = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    aborted = True
 
        if aborted:
            break
 
        # ── Render camera frame ───────────────────────────────────────────────
        frame_rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_surf = pygame.surfarray.make_surface(
            cv2.resize(frame_rgb, (W, H)).swapaxes(0, 1)
        )
        win.blit(frame_surf, (0, 0))
 
        elapsed   = time.time() - session_start
        remaining = max(0, int(session_duration - elapsed))
        if remaining == 0:
            session_over = True
 
        # ── Results screen ────────────────────────────────────────────────────
        if session_over:
            avg_rt = (sum(reaction_times) / len(reaction_times)
                      if reaction_times else 0.0)
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            win.blit(overlay, (0, 0))
 
            title = mono48.render("Session Complete!", True, (0, 150, 255))
            win.blit(title, (W//2 - title.get_width()//2, 220))
 
            for i, txt in enumerate([
                f"Score: {score}",
                f"Avg Reaction: {avg_rt:.2f}s",
                f"Fruits sliced: {score}",
            ]):
                s = mono24.render(txt, True, (0, 200, 255))
                win.blit(s, (W//2 - s.get_width()//2, 340 + i * 46))
 
            pygame.draw.rect(win, (0, 150, 255), btn_rect, 3, border_radius=10)
            bt = mono24.render("New Game", True, (0, 150, 255))
            win.blit(bt, (btn_rect.x + (btn_rect.w - bt.get_width())//2,
                          btn_rect.y + 20))
 
            if hx and hy and btn_rect.collidepoint(hx, hy):
                reset()
 
            pygame.display.update()
            clock.tick(30)
            continue
 
        # ── Spawn (only when ready — user is at neutral position) ────────────
        if ready:
            spawn_timer += 1
            if spawn_timer >= spawn_every:
                spawn_timer = 0
                side = randint(0, 1)
                fx   = randint(50, cx - cr - 60) if side == 0 \
                       else randint(cx + cr + 60, W - 100)
                fruits_list.append(
                    Fruit(fx, 0, fruits[randint(0, 2)], fruit_speed)
                )
                total_spawned += 1
 
        # ── Activation circle ─────────────────────────────────────────────────
        # Green  = ready to slice   Orange = must return to neutral first
        if not hand_in_circle:
            circ_col = (120, 120, 120)          # grey when hand is outside
        elif ready:
            circ_col = (0, 255, 0)              # green  – slice!
        else:
            circ_col = (255, 140, 0)            # orange – return to neutral
        pygame.draw.circle(win, circ_col, (cx, cy), cr, 4)
        # Inner glow
        inner_surf = pygame.Surface((cr*2, cr*2), pygame.SRCALPHA)
        pygame.draw.circle(inner_surf, (*circ_col[:3], 35), (cr, cr), cr)
        win.blit(inner_surf, (cx - cr, cy - cr))

        # Neutral-position indicator: small arc at top of circle showing target zone
        arc_rect = pygame.Rect(cx - cr, cy - cr, cr * 2, cr * 2)
        pygame.draw.arc(win, (255, 255, 100), arc_rect,
                        math.pi/2 - NEUTRAL_THRESHOLD,
                        math.pi/2 + NEUTRAL_THRESHOLD, 6)
 
        # ── Laser beam + collision ────────────────────────────────────────────
        remove = []
        if hand_in_circle and line_angle is not None:
            x1, y1 = cx, cy
            x2 = int(x1 + LINE_LEN * math.cos(line_angle))
            y2 = int(y1 + LINE_LEN * math.sin(line_angle))

            if ready:
                # Active laser – bright green, slicing enabled
                for col_, thick in [
                    ((0,  40,   0), 28),
                    ((0,  80,   0), 18),
                    ((0,  160,  0), 12),
                    ((0,  255,  0),  6),
                ]:
                    pygame.draw.line(win, col_, (x1, y1), (x2, y2), thick)

                sliced_this_frame = False
                for f in fruits_list:
                    if line_hits_rect(x1, y1, x2, y2, f.rect()):
                        score += 1
                        reaction_times.append(time.time() - f.spawn_t)
                        if slice_snd:
                            slice_snd.play()
                        remove.append(f)
                        sliced_this_frame = True
                if sliced_this_frame:
                    ready = False   # must return to neutral before next fruit
            else:
                # Inactive laser – dimmed orange, no collision
                for col_, thick in [
                    ((60,  20,   0), 28),
                    ((120, 50,   0), 18),
                    ((200, 100,  0), 12),
                    ((255, 140,  0),  6),
                ]:
                    pygame.draw.line(win, col_, (x1, y1), (x2, y2), thick)
 
        # ── Draw & update fruits ──────────────────────────────────────────────
        for f in fruits_list:
            f.update()
            f.draw()
            if f.y > H:
                if miss_snd:
                    miss_snd.play()
                remove.append(f)
 
        for item in remove:
            if item in fruits_list:
                fruits_list.remove(item)
 
        # ── HUD (top-left, bigger font with drop-shadow) ──────────────────────
        hud = [
            (f"Score:  {score}",                  (255, 255,  80)),
            (f"Time:   {remaining}s",              (80,  220, 255)),
            (f"Level:  {level}",                   (255, 200,   0)),
            (f"Sliced: {score}/{total_spawned}",   (80,  255, 160)),
        ]
        for idx, (txt_, col_) in enumerate(hud):
            shadow = mono36.render(txt_, True, (0, 0, 0))
            label  = mono36.render(txt_, True, col_)
            win.blit(shadow, (22, 22 + idx * 52))
            win.blit(label,  (20, 20 + idx * 52))

        # Status badge: tells user what to do next
        if not hand_in_circle:
            status_txt = "Move hand into circle"
            status_col = (200, 200, 200)
        elif ready:
            status_txt = "SLICE!  Tilt hand to aim"
            status_col = (0, 255, 80)
        else:
            status_txt = "Return to neutral (straight up)"
            status_col = (255, 160, 0)
        s_shadow = hint28.render(status_txt, True, (0, 0, 0))
        s_label  = hint28.render(status_txt, True, status_col)
        win.blit(s_shadow, (W - s_label.get_width() - 18, 22))
        win.blit(s_label,  (W - s_label.get_width() - 20, 20))

        # ESC hint below status
        esc_s = hint28.render("ESC = exit", True, (160, 160, 160))
        win.blit(esc_s, (W - esc_s.get_width() - 20, 58))
 
        pygame.display.update()
        clock.tick(30)
 
    # ── Cleanup ───────────────────────────────────────────────────────────────
    cam.release()
    cv2.destroyAllWindows()
    pygame.quit()
 
    # ── Metrics ───────────────────────────────────────────────────────────────
    hits     = len(reaction_times)
    spawned  = max(total_spawned, hits)
    accuracy = (hits / spawned * 100) if spawned > 0 else 0.0
    avg_rt   = (sum(reaction_times) / hits) if hits > 0 else 0.0
    motor    = (accuracy * 0.5) + ((1.0 / avg_rt) * 50 if avg_rt > 0 else 0)
 
    return score, accuracy, avg_rt, motor