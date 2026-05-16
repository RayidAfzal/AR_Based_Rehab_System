from utils import resource_path


def run_fruit_ninja(level):
    import pygame
    import cv2
    import numpy as np
    from random import randint, uniform
    import mediapipe as mp
    import math
    import time
    import os
 
    # -------------------------
    # Initialization
    # -------------------------
    cam = cv2.VideoCapture(0)
 
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        max_num_hands=1,  # Only one hand needed for casual mode
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )
    mp_draw = mp.solutions.drawing_utils
 
    pygame.init()
    pygame.mixer.init()
 
    clock = pygame.time.Clock()
 
    myfont = pygame.font.SysFont("monospace", 32, bold=True)
    title_font = pygame.font.SysFont("monospace", 64, bold=True)
    intro_font = pygame.font.SysFont("monospace", 32)
    hud_font = pygame.font.SysFont("monospace", 36, bold=True)
 
    def draw_text_outlined(surface, text, font, color, outline_color, x, y, center=False):
        """Renders text with a solid outline so it's visible over any background."""
        rendered = font.render(text, True, color)
        outline = font.render(text, True, outline_color)
        if center:
            x = x - rendered.get_width() // 2
        for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(-2,2),(2,2)]:
            surface.blit(outline, (x + dx, y + dy))
        surface.blit(rendered, (x, y))

    win_width, win_height = 1280, 720
    win = pygame.display.set_mode((win_width, win_height), pygame.FULLSCREEN)
 
    # Helper function to load images.
    def load_image(path, size):
        try:
            return pygame.transform.scale(pygame.image.load(path), size)
        except Exception as e:
            print(f"Error loading image {path}: {e}")
            return pygame.Surface(size)
 
    # Load images.
    bg = load_image(resource_path('images/bg.jpg'), (win_width, win_height))
    watermelon = [load_image(resource_path(f'images/watermelon{i}.png'), (100, 100)) for i in range(1, 4)]
    berry = [load_image(resource_path(f'images/berry{i}.png'), (100, 100)) for i in range(1, 4)]
    orange = [load_image(resource_path(f'images/orange{i}.png'), (100, 100)) for i in range(1, 4)]
    bomb = load_image(resource_path('images/bomb.png'), (100, 100))
 
    blade_path = resource_path('images/star1.png')
    star = load_image(blade_path, (40, 40)) if os.path.exists(blade_path) else pygame.Surface((40, 40))
 
    # Helper function to load sounds.
    def load_sound(path):
        try:
            return pygame.mixer.Sound(resource_path(path))
        except Exception as e:
            print(f"Error loading sound {path}: {e}")
            return None
 
    slash_sound = load_sound('sounds/slash.wav')
    bomb_sound = load_sound('sounds/bomb.wav')
    game_start_sound = load_sound('sounds/game_start.wav')
    game_end_sound = load_sound('sounds/game_end.wav')
 
    explosion_img = load_image(resource_path('images/explosion.png'), (100, 100))
 
    # -------------------------
    # Mode Selection Layout
    # Two icons centered horizontally: Casual Mode (left) and Quit Game (right)
    # -------------------------
    icon_width, icon_height = 100, 100
    horizontal_gap = 190  # Gap between the two icons
 
    group_width = 2 * icon_width + horizontal_gap
    start_x = (win_width - group_width) // 2
    base_y = win_height // 2 - icon_height // 2
 
    # Positions for the two menu options
    casual_fruit_pos = (start_x, base_y)
    quit_game_pos = (start_x + icon_width + horizontal_gap, base_y)
 
    # Load images for menu icons
    casual_fruit = load_image(resource_path('images/berry1.png'), (icon_width, icon_height))
    quit_game_image = load_image(resource_path('images/bomb.png'), (icon_width, icon_height))
 
    # -------------------------
    # Class Definitions
    # -------------------------
    class Img:
        def __init__(self, x, y, pic, u=12, g=0.4, is_bomb=False):
            self.x = x
            self.y = y
            self.pic = pic
            self.u = u
            self.vx = uniform(-2, 2)
            self.g = g
            self.is_bomb = is_bomb
            self.explosion_start_time = None
 
        def show(self, win, angle):
            rotated_pic = pygame.transform.rotate(self.pic, angle)
            win.blit(rotated_pic, (self.x, self.y))
 
        def update(self):
            self.x += self.vx
            self.y -= self.u
            self.u -= self.g
            # Bounce off walls
            if self.x < 0:
                self.x = 0
                self.vx = -self.vx
            elif self.x + self.pic.get_width() > win_width:
                self.x = win_width - self.pic.get_width()
                self.vx = -self.vx
 
        def show_explosion(self, win):
            if self.explosion_start_time is None:
                self.explosion_start_time = time.time()
            win.blit(explosion_img, (self.x, self.y))
 
        def explosion_finished(self):
            return self.explosion_start_time is not None and (time.time() - self.explosion_start_time) > 2
 
    # -------------------------
    # Global Variables
    # -------------------------
    hand_positions = []
    prev_hand_positions = []
    run = True
    angle = 0
 
    # Lives and timer duration based on difficulty
    lives_map         = {"easy": 10, "medium": 7,  "hard": 5}
    timer_map         = {"easy": 60, "medium": 45, "hard": 30}
    level_key         = str(level).lower()
    starting_lives    = lives_map.get(level_key, 7)
    game_duration_sec = timer_map.get(level_key, 75)
    score_casual, lives_casual = 0, starting_lives
 
    game_started, game_over, game_end_sound_played = False, False, False
    mode_selected = False
    selected_mode = None
    game_start_time = None   # set when gameplay begins
 
    go_again_fruit = orange[0]
    go_again_pos = [win_width // 2 - 120, win_height // 2 + 60]
    quit_game_fruit = berry[0]
    quit_game_over_pos = [win_width // 2 + 40, win_height // 2 + 60]
 
    a_casual = []
    sliced_fruits = []
    slashes, explosions = [], []
 
    spawn_timer_casual = 0
 
    # Hover-to-select timer (user must hover over icon for 1 second to select)
    hover_start_times = {}
 
    # -------------------------
    # Utility Functions
    # -------------------------
    def reset_game():
        nonlocal a_casual, sliced_fruits
        nonlocal score_casual, lives_casual
        nonlocal game_started, game_over, game_end_sound_played
        nonlocal game_start_time
        a_casual, sliced_fruits = [], []
        score_casual, lives_casual = 0, starting_lives
        game_started, game_over, game_end_sound_played = True, False, False
        game_start_time = time.time()
 
    def is_slashing(prev_pos, curr_pos):
        dx = curr_pos[0] - prev_pos[0]
        dy = curr_pos[1] - prev_pos[1]
        return (dx * dx + dy * dy) > (40 * 40)
 
    def create_slashing_effect(x, y):
        slashes.append([(x, y), (x + 20, y + 20), 5])
 
    def spawn_sliced_fruits(fruit_obj):
        if fruit_obj.pic == watermelon[0]:
            left_img = Img(fruit_obj.x - 10, fruit_obj.y, watermelon[1], u=fruit_obj.u, g=fruit_obj.g)
            right_img = Img(fruit_obj.x + 10, fruit_obj.y, watermelon[2], u=fruit_obj.u, g=fruit_obj.g)
        elif fruit_obj.pic == berry[0]:
            left_img = Img(fruit_obj.x - 10, fruit_obj.y, berry[1], u=fruit_obj.u, g=fruit_obj.g)
            right_img = Img(fruit_obj.x + 10, fruit_obj.y, berry[2], u=fruit_obj.u, g=fruit_obj.g)
        elif fruit_obj.pic == orange[0]:
            left_img = Img(fruit_obj.x - 10, fruit_obj.y, orange[1], u=fruit_obj.u, g=fruit_obj.g)
            right_img = Img(fruit_obj.x + 10, fruit_obj.y, orange[2], u=fruit_obj.u, g=fruit_obj.g)
        else:
            return
        sliced_fruits.append((left_img, time.time()))
        sliced_fruits.append((right_img, time.time()))
 
    def check_mode_selection(hand_positions):
        """
        Uses a hover-to-select approach: the user must keep their hand
        over an icon for 1 second to trigger selection. This prevents
        accidental immediate triggering when the menu first appears.
        """
        nonlocal selected_mode, mode_selected
        now = time.time()
        hovering = set()
 
        for hx, hy in hand_positions:
            # Check Casual Mode
            if pygame.Rect(casual_fruit_pos, (icon_width, icon_height)).collidepoint(hx, hy):
                hovering.add("casual")
            # Check Quit Game
            elif pygame.Rect(quit_game_pos, (icon_width, icon_height)).collidepoint(hx, hy):
                hovering.add("quit")
 
        for key in list(hover_start_times.keys()):
            if key not in hovering:
                del hover_start_times[key]
 
        for key in hovering:
            if key not in hover_start_times:
                hover_start_times[key] = now
            elif now - hover_start_times[key] >= 1.0:  # 1 second hover to confirm
                if key == "casual":
                    selected_mode = "classic"
                    mode_selected = True
                elif key == "quit":
                    pygame.quit()
                    os._exit(0)
 
    def draw_hover_progress(win, pos, key, label_gap=10):
        """Draw a progress arc under the icon showing hover progress toward selection."""
        if key in hover_start_times:
            progress = min((time.time() - hover_start_times[key]) / 1.0, 1.0)
            bar_w = icon_width
            bar_h = 6
            bar_x = pos[0]
            bar_y = pos[1] + icon_height + label_gap + 28
            pygame.draw.rect(win, (80, 80, 80), (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(win, (0, 220, 80), (bar_x, bar_y, int(bar_w * progress), bar_h))
 
    # -------------------------
    # Main Loop
    # -------------------------
    while run:
        ret, frame = cam.read()
        if not ret:
            break
 
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
 
        prev_hand_positions = hand_positions.copy()
        hand_positions.clear()
 
        if results.multi_hand_landmarks:
            hand_landmarks_list = [results.multi_hand_landmarks[0]]
            for hand_landmarks in hand_landmarks_list:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                h, w, _ = frame.shape
                fx, fy = int(index_tip.x * win_width), int(index_tip.y * win_height)
                hand_positions.append((fx, fy))
                win.blit(star, (fx - star.get_width() // 2, fy - star.get_height() // 2))
 
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
 
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)
        frame = np.flipud(frame)
        frame = pygame.surfarray.make_surface(frame)
        frame = pygame.transform.scale(frame, (win_width, win_height))
        win.blit(frame, (0, 0))
 
        if not mode_selected:
            # ---- Menu Screen ----
            label_gap = 10
 
            draw_text_outlined(win, "AR FRUITNINJA", title_font, (255, 220, 0), (0, 0, 0), win_width // 2, win_height // 2 - 300, center=True)
            draw_text_outlined(win, "Welcome to AR Fruit Ninja!", intro_font, (255, 255, 255), (0, 0, 0), win_width // 2, win_height // 2 - 250, center=True)
            draw_text_outlined(win, "Use your hand to slice fruits while avoiding bombs.", intro_font, (255, 255, 255), (0, 0, 0), win_width // 2, win_height // 2 - 210, center=True)
            draw_text_outlined(win, "Hover over an option to select!", intro_font, (255, 255, 255), (0, 0, 0), win_width // 2, win_height // 2 - 170, center=True)
 
            # Casual Mode icon + label
            win.blit(casual_fruit, casual_fruit_pos)
            draw_text_outlined(win, "Casual Mode", myfont, (255, 255, 255), (0, 0, 0),
                               casual_fruit_pos[0] + icon_width // 2, casual_fruit_pos[1] + icon_height + label_gap, center=True)
            draw_hover_progress(win, casual_fruit_pos, "casual", label_gap)
 
            # Quit Game icon + label
            win.blit(quit_game_image, quit_game_pos)
            draw_text_outlined(win, "Quit Game", myfont, (255, 255, 255), (0, 0, 0),
                               quit_game_pos[0] + icon_width // 2, quit_game_pos[1] + icon_height + label_gap, center=True)
            draw_hover_progress(win, quit_game_pos, "quit", label_gap)
 
            check_mode_selection(hand_positions)
 
        elif game_over:
            # ---- Game Over Screen ----
            if not game_end_sound_played:
                if game_end_sound:
                    game_end_sound.play()
                game_end_sound_played = True
 
            draw_text_outlined(win, "Game Over!", title_font, (255, 60, 60), (0, 0, 0), win_width // 2, win_height // 2 - 120, center=True)
 
            draw_text_outlined(win, "Score: " + str(score_casual), hud_font, (255, 255, 255), (0, 0, 0), win_width // 2, win_height // 2 - 40, center=True)
 
            win.blit(go_again_fruit, go_again_pos)
            draw_text_outlined(win, "Go Again?", myfont, (255, 255, 255), (0, 0, 0), go_again_pos[0] + icon_width // 2, go_again_pos[1] + 60, center=True)
 
            win.blit(quit_game_fruit, quit_game_over_pos)
            draw_text_outlined(win, "Quit Game", myfont, (255, 255, 255), (0, 0, 0), quit_game_over_pos[0] + icon_width // 2, quit_game_over_pos[1] + 60, center=True)
 
            if any(pygame.Rect(go_again_pos, (icon_width, icon_height)).collidepoint(hx, hy) for hx, hy in hand_positions):
                mode_selected = True
                selected_mode = "classic"
                reset_game()
            if any(pygame.Rect(quit_game_over_pos, (icon_width, icon_height)).collidepoint(hx, hy) for hx, hy in hand_positions):
                run = False
 
        else:
            # ---- Casual Game Mode ----
            draw_text_outlined(win, f"Score: {score_casual}", hud_font, (255, 255, 255), (0, 0, 0), 20, 10)
            draw_text_outlined(win, f"Lives: {lives_casual}", hud_font, (255, 80, 80), (0, 0, 0), 20, 55)

            # Timer: calculate and display; end game if time runs out
            if game_start_time is not None:
                elapsed = time.time() - game_start_time
                time_left = max(0, int(game_duration_sec - elapsed))
                timer_color = (255, 80, 80) if time_left <= 10 else (255, 255, 255)
                draw_text_outlined(win, f"Time: {time_left}s", hud_font, timer_color, (0, 0, 0), win_width - 200, 10)
                if time_left <= 0 and not game_over:
                    game_over = True
                    a_casual.clear()
 
            if not game_started:
                reset_game()
                if game_start_sound:
                    game_start_sound.play()
                game_started = True
                game_start_time = time.time()
 
            spawn_timer_casual += 1
            if spawn_timer_casual > 60:
                spawn_timer_casual = 0
                num = randint(1, 2)
                for _ in range(num):
                    pos = randint(50, win_width - 80)
                    is_bomb = (randint(0, 3) == 0)
                    if is_bomb:
                        a_casual.append(Img(pos, win_height, bomb, u=randint(15, 25), is_bomb=True))
                    else:
                        fruit = [watermelon[0], berry[0], orange[0]][randint(0, 2)]
                        a_casual.append(Img(pos, win_height, fruit, u=randint(15, 25)))
 
            remove_list = []
            for fruit_obj in a_casual:
                fruit_obj.update()
                fruit_obj.show(win, angle)
                fruit_rect = pygame.Rect(fruit_obj.x, fruit_obj.y, fruit_obj.pic.get_width(), fruit_obj.pic.get_height())
                for prev_pos, curr_pos in zip(prev_hand_positions, hand_positions):
                    if is_slashing(prev_pos, curr_pos) and fruit_rect.colliderect(pygame.Rect(curr_pos[0], curr_pos[1], 40, 40)):
                        if slash_sound:
                            slash_sound.play()
                        create_slashing_effect(curr_pos[0], curr_pos[1])
                        if fruit_obj.is_bomb:
                            if bomb_sound:
                                bomb_sound.play()
                            explosions.append(fruit_obj)
                            lives_casual -= 1
                            if lives_casual <= 0:
                                game_over = True
                                a_casual.clear()
                                break
                            remove_list.append(fruit_obj)
                        else:
                            score_casual += 1
                            spawn_sliced_fruits(fruit_obj)
                            remove_list.append(fruit_obj)
                if fruit_obj.y >= win_height:
                    if not fruit_obj.is_bomb:
                        lives_casual -= 1
                        if lives_casual <= 0:
                            game_over = True
                            a_casual.clear()
                            break
                    remove_list.append(fruit_obj)
            for item in remove_list:
                if item in a_casual:
                    a_casual.remove(item)
 
            # Display sliced fruits
            for sliced_obj, spawn_time in sliced_fruits:
                if time.time() - spawn_time > 2:
                    continue
                sliced_obj.update()
                sliced_obj.show(win, angle)
            sliced_fruits = [(obj, t) for (obj, t) in sliced_fruits if time.time() - t <= 2]
 
            # Display explosions
            for explosion in explosions:
                explosion.show_explosion(win)
            explosions = [e for e in explosions if not e.explosion_finished()]
 
            # Display slashing effects
            for s in slashes:
                pygame.draw.line(win, (255, 0, 0), s[0], s[1], s[2])
            slashes.clear()
 
        # Draw hand cursor
        for hx, hy in hand_positions:
            win.blit(star, (hx - star.get_width() // 2, hy - star.get_height() // 2))
 
        angle = (angle + 1) % 360
        pygame.display.update()
        clock.tick(30)
 
    cam.release()
    pygame.quit()

    # Compute derived metrics from the casual game session
    lives_lost = starting_lives - lives_casual
    accuracy = min(100.0, (score_casual / max(score_casual + lives_lost, 1)) * 100)
    # response_time: how quickly the player scored relative to total duration (lower = faster reactions)
    elapsed_total = (time.time() - game_start_time) if game_start_time else game_duration_sec
    response_time = round(min(elapsed_total / max(score_casual, 1), game_duration_sec) / game_duration_sec, 2)
    motor_index = round((score_casual * 0.5 + lives_casual * 2.0) / (starting_lives * 2.0 + 10), 2)

    return score_casual, accuracy, response_time, motor_index