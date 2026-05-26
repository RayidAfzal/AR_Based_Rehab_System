def run_finger_tap(level):
    """
    AR Finger Tap Rehabilitation Game
    Returns: (score, accuracy, avg_response_time, motor_score)
    Press ESC at any time to exit back to the main UI.
    """
 
    import cv2
    import mediapipe as mp
    import numpy as np
    import time
    import random
    import csv
    from datetime import datetime
 
    # ── Resolution ────────────────────────────────────────────────────────────
    W, H = 1920, 1080
 
    # ── Difficulty ───────────────────────────────────────────────────────────
    if level == "Easy":
        duration  = 30
        threshold = 60    # pixel distance for tap detection
        target_appear_range = (1.5, 3.5)
    elif level == "Hard":
        duration  = 20
        threshold = 30
        target_appear_range = (0.6, 1.8)
    else:  # Medium
        duration  = 25
        threshold = 45
        target_appear_range = (1.0, 2.5)
 
    # ── MediaPipe & Camera ────────────────────────────────────────────────────
    mp_hands = mp.solutions.hands
    hands    = mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.75,
        min_tracking_confidence=0.75
    )
    mp_draw  = mp.solutions.drawing_utils
 
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)
 
    # ── Display ───────────────────────────────────────────────────────────────
    cv2.namedWindow("AR Finger Tap", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("AR Finger Tap",
                          cv2.WND_PROP_FULLSCREEN,
                          cv2.WINDOW_FULLSCREEN)
 
    # ── State ─────────────────────────────────────────────────────────────────
    selected_finger = 8       # index finger tip
    finger_name     = "Index"
    finger_map = {
        ord('1'): (8,  "Index"),
        ord('2'): (12, "Middle"),
        ord('3'): (16, "Ring"),
        ord('4'): (20, "Little"),
    }
 
    tap_state       = False
    tap_count       = 0
    score           = 0
    correct_taps    = 0
    total_attempts  = 0
    response_times  = []
 
    target_visible  = False
    target_pos      = (W // 2, H // 4)
    target_timer    = 0
    target_appear_t = 0     # when the current target appeared
 
    # FPS smoothing
    prev_time       = 0
    fps             = 0
    alpha           = 0.1
 
    start_time      = time.time()
    aborted         = False
 
    # ── Helper: random target position ───────────────────────────────────────
    def new_target():
        margin = 120
        tx = random.randint(margin, W - margin)
        ty = random.randint(margin, H // 2)     # upper half (easier to reach)
        return tx, ty
 
    # ── Main loop ─────────────────────────────────────────────────────────────
    while True:
        ok, img = cap.read()
        if not ok:
            continue
 
        img = cv2.flip(img, 1)
        img = cv2.resize(img, (W, H))
 
        elapsed = time.time() - start_time
        if elapsed >= duration:
            break
 
        rgb     = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)
 
        # ── Target logic ──────────────────────────────────────────────────────
        now = time.time()
        if not target_visible and now > target_timer:
            target_visible  = True
            target_pos      = new_target()
            target_appear_t = now
            target_timer    = now + random.uniform(*target_appear_range)
 
        if target_visible:
            cv2.circle(img, target_pos, 36, (0, 0, 255), -1)
            cv2.circle(img, target_pos, 38, (255, 255, 255), 2)
            # Shrinking ring for urgency
            shrink = max(8, int(36 * (1 - (now - target_appear_t) / 3.0)))
            cv2.circle(img, target_pos, shrink, (255, 255, 0), 2)
 
        # ── Hand processing ───────────────────────────────────────────────────
        if results.multi_hand_landmarks:
            for handLms in results.multi_hand_landmarks:
                thumb  = handLms.landmark[4]
                finger = handLms.landmark[selected_finger]
 
                tx_px = int(thumb.x  * W)
                ty_px = int(thumb.y  * H)
                fx_px = int(finger.x * W)
                fy_px = int(finger.y * H)
 
                # Visualise
                cv2.circle(img, (tx_px, ty_px), 14, (255, 80,  0),  -1)
                cv2.circle(img, (fx_px, fy_px), 14, (0,  220, 80),  -1)
                cv2.line(  img, (tx_px, ty_px), (fx_px, fy_px), (200, 200, 200), 2)
 
                dist = float(np.hypot(tx_px - fx_px, ty_px - fy_px))
 
                # Tap detection
                if dist < threshold and not tap_state:
                    tap_count    += 1
                    total_attempts += 1
                    tap_state     = True
 
                    if target_visible:
                        rt = time.time() - target_appear_t
                        # Check if finger is near the target
                        ftx = int((finger.x + thumb.x) / 2 * W)
                        fty = int((finger.y + thumb.y) / 2 * H)
                        if abs(ftx - target_pos[0]) < 80 and abs(fty - target_pos[1]) < 80:
                            score        += 10
                            correct_taps += 1
                            response_times.append(rt)
                            target_visible = False
                    else:
                        score -= 3   # penalty for tapping without target
 
                if dist > threshold:
                    tap_state = False
 
                mp_draw.draw_landmarks(img, handLms, mp_hands.HAND_CONNECTIONS)
 
        # ── HUD ───────────────────────────────────────────────────────────────
        time_left = max(0, int(duration - elapsed))
        bar_w     = int((elapsed / duration) * (W - 80))
 
        # Progress bar
        cv2.rectangle(img, (40, H - 60), (W - 40, H - 34), (60, 60, 60), -1)
        cv2.rectangle(img, (40, H - 60), (40 + bar_w, H - 34), (0, 200, 100), -1)
 
        def txt(s, x, y, scale=0.9, col=(255,255,255), thick=2):
            cv2.putText(img, s, (x, y), cv2.FONT_HERSHEY_DUPLEX,
                        scale, col, thick, cv2.LINE_AA)
 
        txt(f"Finger: {finger_name}",  20,  50,  1.0,  (255, 220, 0))
        txt(f"Level:  {level}",        20,  95,  1.0,  (255, 220, 0))
        txt(f"Score:  {score}",        20, 140,  1.0,  (0,  255, 100))
        txt(f"Taps:   {tap_count}",    20, 185,  1.0,  (0,  200, 255))
        txt(f"Time:   {time_left}s",   20, 230,  1.0,  (255, 80,  80))
 
        # FPS (bottom right)
        curr_time   = time.time()
        inst_fps    = 1 / (curr_time - prev_time) if prev_time else 0
        prev_time   = curr_time
        fps         = (1 - alpha) * fps + alpha * inst_fps
        txt(f"FPS {int(fps)}", W - 160, H - 70, 0.7, (0, 255, 0))
 
        txt("1-Index  2-Middle  3-Ring  4-Little  |  ESC=exit",
            20, H - 70, 0.6, (180, 180, 180), 1)
 
        cv2.imshow("AR Finger Tap", img)
 
        key = cv2.waitKey(1) & 0xFF
        if key == 27:           # ESC
            aborted = True
            break
        if key in finger_map:
            selected_finger, finger_name = finger_map[key]
            # Reset session counters on finger switch
            tap_count = score = correct_taps = total_attempts = 0
            response_times.clear()
            start_time     = time.time()
            target_visible = False
 
    # ── Cleanup ───────────────────────────────────────────────────────────────
    cap.release()
    cv2.destroyAllWindows()
 
    # ── Metrics ───────────────────────────────────────────────────────────────
    accuracy    = (correct_taps / total_attempts * 100) if total_attempts > 0 else 0.0
    speed       = tap_count / max(elapsed, 1)
    avg_rt      = sum(response_times) / len(response_times) if response_times else 0.0
    motor_score = (speed * 40) + (accuracy * 0.4)
 
    # Optional CSV log
    try:
        with open("rehab_progress.csv", "a", newline="") as f:
            import csv as _csv
            w = _csv.writer(f)
            w.writerow([
                datetime.now(), finger_name, level,
                tap_count, round(speed, 2),
                round(accuracy, 2), round(motor_score, 2)
            ])
    except Exception:
        pass
 
    return score, accuracy, avg_rt, motor_score