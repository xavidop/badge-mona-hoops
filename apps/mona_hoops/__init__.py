"""
Mona Hoops: a sixty-second shootout. Charge the shot, pick the arc, sink it.

Hold Select to charge the power meter and let go to shoot; Up and Down change
the arc. Every shot moves Mona to a new spot, the far ones are worth three,
swishes earn a bonus and three in a row sets the ball on fire.

Controls:
* Select = Hold to charge, release to shoot (and start, or play again)
* Up / Down = Raise or lower the arc
* Back = Back to the title
"""

import math
import os
import random
import sys

from badgeware import State

APP_DIR = "/system/apps/mona_hoops"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

badge.mode(HIRES | VSYNC)
screen.antialias = image.OFF

WIDTH, HEIGHT = screen.width, screen.height

SHOOTER = image.load("assets/shooter.png").spritesheet(2, 1)
BALL = image.load("assets/ball.png")

GAME_MS = 60000
FLOOR = 212
BOARD_X, BOARD_TOP, BOARD_H = 292, 92, 50
RIM_Y = 136
RIM_LEFT, RIM_RIGHT = 262, 290
BALL_R = 5
GRAVITY = 430.0
MIN_SPEED, MAX_SPEED = 170.0, 300.0
POWER_PERIOD_MS = 1300
ANGLES = (35, 40, 45, 50, 55, 60, 65, 70)
SPOTS = (176, 150, 124, 96, 68, 42)      # Mona's x for each shot, farther each time
THREE_FROM = 3                           # spot index from which shots are worth three
SHOOT_POSE_MS = 400
FIRE_STREAK = 3

SKY = color.rgb(32, 36, 64)
CROWD_DARK = color.rgb(22, 24, 44)
COURT = color.rgb(196, 140, 84)
COURT_LINE = color.rgb(240, 230, 200)
WALL = color.rgb(60, 50, 90)
BOARD = color.rgb(240, 240, 240)
BOARD_EDGE = color.rgb(60, 60, 70)
RIM = color.rgb(240, 90, 40)
NET = color.rgb(230, 230, 230)
POLE = color.rgb(120, 120, 130)
CROWD = (color.rgb(230, 80, 80), color.rgb(80, 120, 230), color.rgb(240, 220, 90), color.rgb(240, 240, 240), color.rgb(90, 200, 120))
INK = color.rgb(20, 20, 32)
CREAM = color.rgb(240, 232, 208)
AMBER = color.rgb(255, 200, 48)
RED = color.rgb(230, 70, 70)
GREEN = color.rgb(96, 208, 96)
FLAME = (color.rgb(255, 120, 40), color.rgb(255, 210, 60))
PANEL = color.rgb(20, 20, 32, 190)
SHADOW = color.rgb(0, 0, 0, 90)

TITLE = font.futile
BIG = font.ignore
BODY = font.nope
SMALL = font.sins

TITLE_SCREEN, PLAY, RESULT = 0, 1, 2

state = {"best": 0, "games": 0, "makes": 0}
State.load("mona_hoops", state)
for key in state:
    if not isinstance(state[key], int) or state[key] < 0:
        state[key] = 0


def save_state():
    try:
        State.save("mona_hoops", state)
    except OSError as error:
        print("Mona Hoops: could not save:", error)


# ----------------------------------------------------------------------------
# game state

mode = TITLE_SCREEN
score = 0
makes = 0
attempts = 0
streak = 0
best_streak = 0
spot = 0
angle_index = 4
charging_since = None
power = 0.0
shot_at = 0
ball = None             # [x, y, vx, vy, bounces, touched, scored, resolved_at]
started_at = None
message = ""
message_until = 0
crowd = []


def seed_crowd():
    random.seed(badge.ticks)
    del crowd[:]
    for n in range(70):
        crowd.append((random.randint(4, WIDTH - 6), 10 + random.randint(0, 26), random.randint(0, len(CROWD) - 1)))


seed_crowd()


def start_game():
    global mode, score, makes, attempts, streak, best_streak, spot, charging_since, power, ball, started_at, message
    mode = PLAY
    score = makes = attempts = streak = best_streak = 0
    spot = 0
    charging_since = None
    power = 0.0
    ball = None
    started_at = None
    message = ""


def time_left():
    if started_at is None:
        return GAME_MS
    return max(0, GAME_MS - (badge.ticks - started_at))


def hands():
    """Where the ball sits in Mona's hands for the current spot."""
    return SPOTS[spot] + 12, FLOOR - 50


def shoot():
    global ball, shot_at, attempts, started_at, charging_since
    if started_at is None:
        started_at = badge.ticks
    speed = MIN_SPEED + (MAX_SPEED - MIN_SPEED) * power
    radians = math.radians(ANGLES[angle_index])
    x, y = hands()
    ball = [float(x), float(y - 6), speed * math.cos(radians), -speed * math.sin(radians), 0, False, False, None]
    shot_at = badge.ticks
    attempts += 1
    charging_since = None


def resolve(made):
    global score, makes, streak, best_streak, spot, message, message_until
    swish = made and not ball[5]
    if made:
        points = 3 if spot >= THREE_FROM else 2
        bonus = (1 if swish else 0) + (1 if streak >= FIRE_STREAK else 0)
        score += points + bonus
        makes += 1
        streak += 1
        best_streak = max(best_streak, streak)
        state["makes"] += 1
        message = "SWISH! +%d" % (points + bonus) if swish else "+%d" % (points + bonus)
        if streak == FIRE_STREAK:
            message = "ON FIRE! +%d" % (points + bonus)
    else:
        streak = 0
        message = "MISS"
    message_until = badge.ticks + 900
    spot = (spot + 1) % len(SPOTS)


def update_ball(dt):
    global ball
    if ball is None:
        return
    if ball[7] is not None:
        if badge.ticks - ball[7] > 350:
            ball = None
        return
    x, y, vx, vy = ball[0], ball[1], ball[2], ball[3]
    prev_y = y
    vy += GRAVITY * dt
    x += vx * dt
    y += vy * dt
    # the backboard
    if x + BALL_R >= BOARD_X and BOARD_TOP <= y <= BOARD_TOP + BOARD_H and vx > 0:
        x = BOARD_X - BALL_R
        vx = -vx * 0.55
        ball[5] = True
    # the rim's two ends
    for rx in (RIM_LEFT, RIM_RIGHT - 2):
        dx, dy = x - rx, y - RIM_Y
        dist = math.sqrt(dx * dx + dy * dy)
        if 0 < dist < BALL_R + 2:
            nx, ny = dx / dist, dy / dist
            dot = vx * nx + vy * ny
            if dot < 0:
                vx -= 1.6 * dot * nx
                vy -= 1.6 * dot * ny
                vx *= 0.7
                vy *= 0.7
            x = rx + nx * (BALL_R + 2)
            y = RIM_Y + ny * (BALL_R + 2)
            ball[5] = True
    # through the hoop, going down, between the rim ends
    if not ball[6] and prev_y < RIM_Y <= y and vy > 0 and RIM_LEFT + 4 < x < RIM_RIGHT - 6:
        ball[6] = True
        resolve(True)
        ball[7] = badge.ticks
    # the floor
    if y + BALL_R >= FLOOR:
        y = FLOOR - BALL_R
        vy = -vy * 0.5
        vx *= 0.8
        ball[4] += 1
        if ball[4] >= 2 and not ball[6]:
            resolve(False)
            ball[7] = badge.ticks
    if x < -20 or x > WIDTH + 20:
        if not ball[6]:
            resolve(False)
        ball[7] = badge.ticks
    ball[0], ball[1], ball[2], ball[3] = x, y, vx, vy


def update_play(dt):
    global charging_since, power, angle_index, mode
    if badge.pressed(BUTTON_BACK):
        mode = TITLE_SCREEN
        return
    if badge.pressed(BUTTON_UP):
        angle_index = min(len(ANGLES) - 1, angle_index + 1)
    if badge.pressed(BUTTON_DOWN):
        angle_index = max(0, angle_index - 1)
    if time_left() == 0 and ball is None:
        finish_game()
        return
    if ball is None and time_left() > 0:
        if badge.held(BUTTON_SELECT):
            if charging_since is None:
                charging_since = badge.ticks
            phase = ((badge.ticks - charging_since) % POWER_PERIOD_MS) / POWER_PERIOD_MS
            power = phase * 2 if phase < 0.5 else 2 - phase * 2
        elif charging_since is not None:
            shoot()
    update_ball(dt)


def finish_game():
    global mode
    state["games"] += 1
    if score > state["best"]:
        state["best"] = score
    save_state()
    mode = RESULT


# ----------------------------------------------------------------------------
# drawing

def fill(x, y, w, h, pen):
    screen.pen = pen
    screen.rectangle(x, y, w, h)


def write(text, x, y, pen, face=BODY):
    screen.font = face
    screen.pen = pen
    screen.text(text, x, y)


def text_width(text, face=BODY):
    screen.font = face
    return screen.measure_text(text)[0]


def write_centred(text, cx, y, pen, face=BODY):
    write(text, cx - text_width(text, face) // 2, y, pen, face)


def write_shadowed(text, cx, y, pen, face=BODY):
    write_centred(text, cx + 2, y + 2, INK, face)
    write_centred(text, cx, y, pen, face)


def draw_court():
    fill(0, 0, WIDTH, HEIGHT, SKY)
    fill(0, 6, WIDTH, 36, CROWD_DARK)
    cheering = badge.ticks < message_until and message != "MISS"
    for n, (x, y, c) in enumerate(crowd):
        lift = ((badge.ticks // 120 + n) % 2) if cheering else 0
        fill(x, y - lift, 3, 3, CROWD[c])
    fill(0, 42, WIDTH, FLOOR - 42, WALL)
    for x in range(0, WIDTH, 40):
        fill(x, 42, 2, FLOOR - 42, SKY)
    fill(0, FLOOR, WIDTH, HEIGHT - FLOOR, COURT)
    fill(0, FLOOR, WIDTH, 2, COURT_LINE)
    # the three-point arc on the floor
    screen.pen = COURT_LINE
    screen.shape(shape.line(vec2(SPOTS[THREE_FROM] - 6, FLOOR + 2), vec2(SPOTS[THREE_FROM] - 6, HEIGHT), 2))
    # the hoop: pole, backboard, rim and net
    fill(BOARD_X + 8, 100, 6, FLOOR - 100, POLE)
    fill(BOARD_X, BOARD_TOP, 6, BOARD_H, BOARD)
    fill(BOARD_X, BOARD_TOP, 6, 2, BOARD_EDGE)
    fill(BOARD_X, BOARD_TOP + BOARD_H - 2, 6, 2, BOARD_EDGE)
    fill(BOARD_X + 1, RIM_Y - 14, 2, 12, BOARD_EDGE)
    screen.pen = NET
    for n in range(5):
        x = RIM_LEFT + 2 + n * 6
        screen.shape(shape.line(vec2(x, RIM_Y + 2), vec2(x + 3, RIM_Y + 16), 1))
        screen.shape(shape.line(vec2(x + 6, RIM_Y + 2), vec2(x + 3, RIM_Y + 16), 1))
    fill(RIM_LEFT, RIM_Y - 1, RIM_RIGHT - RIM_LEFT, 3, RIM)
    fill(RIM_LEFT - 2, RIM_Y - 2, 4, 5, RIM)


def draw_mona():
    frame = 1 if (ball is not None and badge.ticks - shot_at < SHOOT_POSE_MS) or charging_since is not None else 0
    x = SPOTS[spot] - 16
    fill(x + 4, FLOOR - 6, 26, 6, SHADOW)
    screen.blit(SHOOTER.sprite(frame, 0), rect(0, 0, 16, 24), rect(x, FLOOR - 48, 32, 48), image.NEAREST)


def draw_ball():
    if ball is None:
        if charging_since is None and mode == PLAY:
            x, y = hands()
            screen.blit(BALL, rect(0, 0, 8, 8), rect(x - 8, y - 8 + 14, 16, 16), image.NEAREST)
        elif charging_since is not None:
            x, y = hands()
            screen.blit(BALL, rect(0, 0, 8, 8), rect(x - 2, y - 14, 16, 16), image.NEAREST)
        return
    x, y = int(ball[0]), int(ball[1])
    if streak >= FIRE_STREAK and not ball[6]:
        for n in range(3):
            fill(x - 8 + random.randint(0, 10), y - 12 + random.randint(0, 8), 3, 3, FLAME[n % 2])
    fill(x - 6, FLOOR - 3, 12, 3, SHADOW)
    screen.blit(BALL, rect(0, 0, 8, 8), rect(x - 8, y - 8, 16, 16), image.NEAREST)


def draw_aim():
    if ball is not None or mode != PLAY:
        return
    x, y = hands()
    radians = math.radians(ANGLES[angle_index])
    length = 18 + 22 * power
    screen.pen = AMBER if charging_since is not None else CREAM
    screen.shape(shape.line(vec2(x + 2, y - 8), vec2(x + 2 + math.cos(radians) * length, y - 8 - math.sin(radians) * length), 2))
    # the power meter beside Mona
    mx = SPOTS[spot] - 28
    fill(mx, FLOOR - 60, 6, 52, INK)
    level = int(50 * power)
    fill(mx + 1, FLOOR - 9 - level, 4, level, GREEN if power < 0.55 else (AMBER if power < 0.8 else RED))
    write("%d" % ANGLES[angle_index], mx - 2, FLOOR - 74, CREAM, SMALL)


def draw_hud():
    fill(0, 0, WIDTH, 16, PANEL)
    write("SCORE %d" % score, 6, 2, AMBER, BODY)
    left = time_left()
    write_centred("0:%02d" % (left // 1000) if left else "TIME!", WIDTH // 2, 2, RED if left < 10000 else CREAM, BODY)
    label = "%dPT SHOT" % (3 if spot >= THREE_FROM else 2)
    write(label, WIDTH - 6 - text_width(label, BODY), 2, CREAM, BODY)
    if streak >= FIRE_STREAK:
        write_shadowed("ON FIRE", SPOTS[spot], FLOOR - 92, FLAME[1], SMALL)
    if message and badge.ticks < message_until:
        write_shadowed(message, WIDTH // 2, 56, AMBER if message != "MISS" else RED, TITLE)


def draw_title():
    draw_court()
    draw_mona()
    x, y = hands()
    screen.blit(BALL, rect(0, 0, 8, 8), rect(x - 8, y + 6, 16, 16), image.NEAREST)
    fill(20, 50, WIDTH - 40, 92, PANEL)
    write_shadowed("MONA HOOPS", WIDTH // 2, 58, AMBER, BIG)
    write_shadowed("60 SECONDS - HOLD SELECT TO SHOOT", WIDTH // 2, 90, CREAM, SMALL)
    if (badge.ticks // 400) % 2:
        write_shadowed("SELECT TO TIP OFF", WIDTH // 2, 112, CREAM, BODY)
    if state["games"]:
        write_shadowed("BEST %d   MADE %d SHOTS EVER" % (state["best"], state["makes"]), WIDTH // 2, 222, AMBER, SMALL)


def draw_result():
    draw_court()
    draw_mona()
    fill(30, 40, WIDTH - 60, 140, PANEL)
    write_shadowed("FINAL SCORE %d" % score, WIDTH // 2, 50, AMBER, TITLE)
    write_centred("%d OF %d MADE   BEST STREAK %d" % (makes, attempts, best_streak), WIDTH // 2, 84, CREAM, BODY)
    if score >= state["best"] and score > 0:
        write_centred("NEW BEST!", WIDTH // 2, 106, AMBER, BODY)
    write_centred("BEST EVER %d" % state["best"], WIDTH // 2, 126, CREAM, SMALL)
    if (badge.ticks // 400) % 2:
        write_centred("SELECT: AGAIN   BACK: TITLE", WIDTH // 2, 152, CREAM, SMALL)


def update():
    global mode
    dt = min(badge.ticks_delta, 60) / 1000
    if mode == TITLE_SCREEN:
        if badge.pressed(BUTTON_SELECT):
            start_game()
        draw_title()
    elif mode == PLAY:
        update_play(dt)
        if mode != PLAY:
            return
        draw_court()
        draw_aim()
        draw_mona()
        draw_ball()
        draw_hud()
    else:
        if badge.pressed(BUTTON_SELECT):
            start_game()
        elif badge.pressed(BUTTON_BACK):
            mode = TITLE_SCREEN
        draw_result()


def on_exit():
    save_state()


run(update)
