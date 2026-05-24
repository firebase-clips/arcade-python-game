import pygame
import random
import math
import json
import os
import asyncio

# =========================================
# INIT
# =========================================

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

WIDTH, HEIGHT = 400, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("NEON PHASES")
clock = pygame.time.Clock()

font       = pygame.font.SysFont(None, 28)
font_big   = pygame.font.SysFont(None, 54)
font_small = pygame.font.SysFont(None, 22)

# =========================================
# SAVE / LOAD  — localStorage in browser, file on desktop
# =========================================

def load_data():
    try:
        # Pygbag / browser environment
        import platform
        if platform.system() == "Emscripten":
            from js import localStorage
            raw = localStorage.getItem("neon_phases_save")
            if raw:
                return json.loads(raw)
            return {"high": 0}
    except Exception:
        pass
    # Desktop fallback
    if os.path.exists("save.json"):
        try:
            return json.load(open("save.json"))
        except Exception:
            pass
    return {"high": 0}

def save_data(d):
    try:
        import platform
        if platform.system() == "Emscripten":
            from js import localStorage
            localStorage.setItem("neon_phases_save", json.dumps(d))
            return
    except Exception:
        pass
    try:
        json.dump(d, open("save.json", "w"))
    except Exception as e:
        print("Save error:", e)

data = load_data()

# =========================================
# SOUND / MUSIC
# =========================================

MUSIC_VOLUME_NORMAL = 0.18

try:
    pygame.mixer.music.load("assets/bg.ogg")   # .ogg works best in browser
    pygame.mixer.music.set_volume(MUSIC_VOLUME_NORMAL)
    pygame.mixer.music.play(-1)
except Exception as e:
    print("Music error:", e)

# ---- Single-track volume envelope ----
env_state   = ["normal"]
env_target  = [MUSIC_VOLUME_NORMAL]
env_speed   = [0.08]
env_timer   = [0]
current_vol = [MUSIC_VOLUME_NORMAL]

def trigger_envelope(kind):
    if kind == "hit":
        current_vol[0] = 0.03
        pygame.mixer.music.set_volume(0.03)
        env_target[0] = MUSIC_VOLUME_NORMAL
        env_speed[0]  = 0.045
        env_state[0]  = "hit"
        env_timer[0]  = 0
    elif kind == "pickup":
        current_vol[0] = min(current_vol[0], 0.28)
        pygame.mixer.music.set_volume(current_vol[0])
        env_target[0] = MUSIC_VOLUME_NORMAL
        env_speed[0]  = 0.15
        env_state[0]  = "pickup"
        env_timer[0]  = 0
    elif kind == "life":
        current_vol[0] = 0.30
        pygame.mixer.music.set_volume(0.30)
        env_target[0] = MUSIC_VOLUME_NORMAL
        env_speed[0]  = 0.10
        env_state[0]  = "life"
        env_timer[0]  = 0
    elif kind == "phase_start":
        env_target[0] = 0.05
        env_speed[0]  = 0.04
        env_state[0]  = "phase"
        env_timer[0]  = 0
    elif kind == "phase_end":
        env_target[0] = MUSIC_VOLUME_NORMAL
        env_speed[0]  = 0.03
        env_state[0]  = "normal"
        env_timer[0]  = 0

def tick_envelope():
    diff = env_target[0] - current_vol[0]
    if abs(diff) > 0.001:
        current_vol[0] += diff * env_speed[0]
        pygame.mixer.music.set_volume(max(0.0, min(1.0, current_vol[0])))

# =========================================
# FLOATING TEXT
# =========================================

floating_texts = []

def add_floating_text(x, y, text, color):
    floating_texts.append([x, y, text, color, 60])

def update_floating_texts():
    for t in floating_texts[:]:
        t[1] -= 1
        t[4] -= 1
        if t[4] <= 0:
            floating_texts.remove(t)

def draw_floating_texts(offset_x=0, offset_y=0):
    for x, y, text, color, life in floating_texts:
        alpha = int(255 * (life / 60))
        surf = font.render(text, True, color)
        surf.set_alpha(alpha)
        screen.blit(surf, (x + offset_x, y + offset_y))

# =========================================
# PARTICLE SYSTEM
# =========================================

particles = []

def add_particles(x, y, color, count=10):
    for _ in range(count):
        angle = random.uniform(0, math.tau)
        spd   = random.uniform(1, 4)
        particles.append({
            "x": x, "y": y,
            "vx": math.cos(angle) * spd,
            "vy": math.sin(angle) * spd,
            "color": color,
            "life": random.randint(20, 40)
        })

def update_draw_particles(offset_x=0, offset_y=0):
    for p in particles[:]:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vy"] += 0.15
        p["life"] -= 1
        if p["life"] <= 0:
            particles.remove(p)
            continue
        alpha  = int(255 * p["life"] / 40)
        radius = max(1, p["life"] // 8)
        surf   = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*p["color"], alpha), (radius, radius), radius)
        screen.blit(surf, (int(p["x"] - radius + offset_x),
                           int(p["y"] - radius + offset_y)))

# =========================================
# HIGH SCORE
# =========================================

def check_highscore(score):
    global highscore_announced
    if score > data["high"]:
        data["high"] = int(score)
        save_data(data)
        if not highscore_announced:
            add_floating_text(WIDTH // 2 - 90, 120, "NEW HIGH SCORE!", (255, 215, 0))
            highscore_announced = True

# =========================================
# HUD
# =========================================

def draw_ui(score, lives, phase_name, combo, combo_timer):
    pygame.draw.rect(screen, (15, 15, 25), (0, 0, WIDTH, 80))
    pygame.draw.line(screen, (0, 220, 200), (0, 80), (WIDTH, 80), 1)
    screen.blit(font.render(f"Score: {int(score)}", True, (255, 255, 255)), (10, 10))
    screen.blit(font.render(f"Best:  {int(data['high'])}", True, (255, 215, 0)), (10, 36))
    screen.blit(font.render(f"Phase: {phase_name}", True, (255, 200, 120)), (10, 60))
    for i in range(lives):
        pygame.draw.circle(screen, (0, 255, 100), (WIDTH - 20 - i * 22, 25), 8)
    for i in range(lives, 5):
        pygame.draw.circle(screen, (60, 60, 60), (WIDTH - 20 - i * 22, 25), 8)
    if combo > 1.0:
        c_surf = font_small.render(f"x{combo:.1f} COMBO", True, (255, 230, 80))
        screen.blit(c_surf, (WIDTH - c_surf.get_width() - 8, 48))

# =========================================
# GLOBAL STATE
# =========================================

flash_timer  = 0
shake_timer  = 0
phase        = 1
phase_name   = "WARMUP"
last_phase   = 1
phase_transition       = False
phase_transition_timer = 0
highscore_announced    = False
boss_mode              = False
boss_timer             = 0
boss_triggered_phase   = 0
safe_lane_x            = 150
minimum_safe_gap       = 120
pattern_timer          = 0
difficulty_balance     = 1.0
shield_timer           = 0
magnet_timer           = 0
player_idle_timer      = 0
last_player_x          = 180

# =========================================
# RESET
# =========================================

def reset():
    global highscore_announced, boss_triggered_phase
    global player_idle_timer, last_player_x
    global particles, floating_texts

    highscore_announced  = False
    boss_triggered_phase = 0
    player_idle_timer    = 0
    last_player_x        = 180
    particles.clear()
    floating_texts.clear()
    env_state[0]   = "normal"
    env_target[0]  = MUSIC_VOLUME_NORMAL
    env_speed[0]   = 0.08
    current_vol[0] = MUSIC_VOLUME_NORMAL
    pygame.mixer.music.set_volume(MUSIC_VOLUME_NORMAL)

    return (
        pygame.Rect(180, 500, 40, 40),
        [], [], [], [], [], [],
        0, 1.0, 0, 2.0, 0.0, 3, 0
    )

(player, blocks, collectibles, life_orbs,
 calm_orbs, shield_orbs, magnet_orbs,
 score, combo, combo_timer,
 speed_bonus, velocity_x, lives, calm_timer) = reset()

# =========================================
# SPAWN HELPERS
# =========================================

def spawn_block(pattern="random"):
    global safe_lane_x, player_idle_timer

    camping = player_idle_timer > 180
    if camping:
        target_x = max(0, min(player.x, WIDTH - 40))
        if not any(abs(b.x - target_x) < 30 and b.y < -10 for b in blocks):
            blocks.append(pygame.Rect(target_x, -40, 40, 40))
        add_floating_text(player.x, player.y - 40, "MOVE!", (255, 80, 80))
        player_idle_timer = 0
        return

    safe_lane_x += random.randint(-30, 30)
    safe_lane_x  = max(60, min(safe_lane_x, WIDTH - 140))

    if pattern == "random":
        for _ in range(30):
            x = random.randint(0, 360)
            if abs(x - safe_lane_x) < minimum_safe_gap:
                continue
            if any(abs(b.x - x) < minimum_safe_gap and abs(b.y) < 120 for b in blocks):
                continue
            blocks.append(pygame.Rect(x, -40, 40, 40))
            break
    elif pattern == "wall_gap":
        gap_x = safe_lane_x
        for x in range(0, WIDTH, 50):
            if gap_x <= x <= gap_x + 140:
                continue
            blocks.append(pygame.Rect(x, -40, 40, 40))
    elif pattern == "zigzag":
        for i, x in enumerate([40, 120, 200, 280]):
            if abs(x - safe_lane_x) < 100:
                continue
            blocks.append(pygame.Rect(x, -i * 90, 40, 40))

def spawn_collectible():
    if random.random() < 0.015:
        collectibles.append(pygame.Rect(random.randint(0, 360), -40, 25, 25))

def spawn_life_orb():
    if random.random() < 0.0018:
        life_orbs.append(pygame.Rect(random.randint(0, 360), -40, 25, 25))

# =========================================
# MAIN  — async required by Pygbag
# =========================================

async def main():
    global flash_timer, shake_timer, phase, phase_name, last_phase
    global phase_transition, phase_transition_timer, highscore_announced
    global boss_mode, boss_timer, boss_triggered_phase
    global safe_lane_x, pattern_timer, difficulty_balance
    global player_idle_timer, last_player_x
    global player, blocks, collectibles, life_orbs
    global calm_orbs, shield_orbs, magnet_orbs
    global score, combo, combo_timer, speed_bonus, velocity_x, lives, calm_timer

    state   = "menu"
    running = True

    while running:
        # ---- EVENTS ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if state == "menu":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    (player, blocks, collectibles, life_orbs,
                     calm_orbs, shield_orbs, magnet_orbs,
                     score, combo, combo_timer,
                     speed_bonus, velocity_x, lives, calm_timer) = reset()
                    phase, last_phase              = 1, 1
                    phase_transition               = False
                    phase_transition_timer         = 0
                    boss_mode                      = False
                    boss_timer                     = 0
                    boss_triggered_phase           = 0
                    difficulty_balance             = 1.0
                    pattern_timer                  = 0
                    flash_timer = shake_timer      = 0
                    state = "game"

            if state == "gameover":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    state = "menu"

        # ==========================================
        # MENU
        # ==========================================
        if state == "menu":
            screen.fill((10, 10, 20))
            random.seed(42)
            for _ in range(80):
                sx, sy = random.randint(0, WIDTH), random.randint(0, HEIGHT)
                br = random.randint(40, 120)
                screen.set_at((sx, sy), (br, br, br))
            random.seed()
            pulse = int(150 + 80 * math.sin(pygame.time.get_ticks() * 0.005))
            title = font_big.render("NEON PHASES", True, (0, 255, 220))
            start = font.render("PRESS ENTER TO START", True, (pulse, pulse, pulse))
            hi    = font_small.render(f"Best: {int(data['high'])}", True, (255, 215, 0))
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 210))
            screen.blit(start, (WIDTH // 2 - start.get_width() // 2, 310))
            screen.blit(hi,    (WIDTH // 2 - hi.get_width() // 2,    360))

        # ==========================================
        # GAME OVER
        # ==========================================
        elif state == "gameover":
            screen.fill((20, 0, 0))
            over        = font_big.render("GAME OVER",                True, (255, 50, 50))
            final_score = font.render(f"Score: {int(score)}",         True, (255, 255, 0))
            best_final  = font.render(f"Best:  {int(data['high'])}",  True, (255, 215, 0))
            restart     = font.render("PRESS R TO MENU",              True, (255, 255, 255))
            screen.blit(over,        (WIDTH // 2 - over.get_width() // 2,        210))
            screen.blit(final_score, (WIDTH // 2 - final_score.get_width() // 2, 285))
            screen.blit(best_final,  (WIDTH // 2 - best_final.get_width() // 2,  320))
            screen.blit(restart,     (WIDTH // 2 - restart.get_width() // 2,     380))

        # ==========================================
        # GAME
        # ==========================================
        elif state == "game":

            # Screen shake
            offset_x = offset_y = 0
            if shake_timer > 0:
                offset_x = random.randint(-5, 5)
                offset_y = random.randint(-5, 5)
                shake_timer -= 1

            # Phase thresholds
            if score < 120:
                phase, phase_name, base_speed, spawn_multiplier = 1, "WARMUP",   4.5, 0.70
            elif score < 300:
                phase, phase_name, base_speed, spawn_multiplier = 2, "PRESSURE", 5.5, 0.85
            elif score < 600:
                phase, phase_name, base_speed, spawn_multiplier = 3, "FLOW",     6.5, 1.00
            elif score < 1200:
                phase, phase_name, base_speed, spawn_multiplier = 4, "SURVIVAL", 7.5, 1.10
            else:
                phase, phase_name, base_speed, spawn_multiplier = 5, "ELITE",    8.5, 1.20

            if phase != last_phase:
                phase_transition       = True
                phase_transition_timer = 180
                blocks.clear()
                trigger_envelope("phase_start")
                add_floating_text(WIDTH // 2 - 70,  HEIGHT // 2 - 20, phase_name,    (255, 255, 255))
                add_floating_text(WIDTH // 2 - 90,  HEIGHT // 2 + 20, "PHASE SHIFT", (100, 200, 255))
                last_phase = phase

            speed = (base_speed + speed_bonus) * difficulty_balance
            if phase_transition:
                speed *= 0.2
            speed = max(4.0, min(speed, 14.0))

            difficulty_balance *= 0.985 if len(blocks) > 8 else 1.002
            difficulty_balance  = max(0.8, min(difficulty_balance, 1.15))

            intensity = min(180, int(50 + speed_bonus * 10))
            screen.fill((intensity, 10, 20) if not phase_transition else (15, 15, 30))

            # Player movement
            keys         = pygame.key.get_pressed()
            acceleration = 0.8
            friction     = 0.90
            max_spd      = 8
            if keys[pygame.K_LEFT]:
                velocity_x -= acceleration
            if keys[pygame.K_RIGHT]:
                velocity_x += acceleration
            velocity_x = max(-max_spd, min(velocity_x * friction, max_spd))
            player.x  += int(velocity_x)

            if abs(player.x - last_player_x) < 5:
                player_idle_timer += 1
            else:
                player_idle_timer = 0
            last_player_x = player.x
            player.x = max(0, min(player.x, WIDTH - player.width))

            # Combo decay
            if combo_timer > 0:
                combo_timer -= 1
            else:
                combo = max(1.0, combo - 0.02)

            # Spawning
            spawn_rate = 0.010 * spawn_multiplier
            if len(blocks) > 7:
                spawn_rate *= 0.6
            if phase_transition:
                spawn_rate = 0

            pattern_timer    += 1
            phase_pattern_time = max(180, 420 - phase * 35)

            if pattern_timer > phase_pattern_time:
                pattern_timer = 0
                if not phase_transition and len(blocks) < 6 and random.random() < 0.25:
                    spawn_block(random.choice(["wall_gap", "zigzag"]))
            else:
                if not phase_transition and len(blocks) < 7 and random.random() < spawn_rate:
                    spawn_block()

            # Boss mode
            if (phase >= 4 and phase != boss_triggered_phase
                    and not phase_transition and boss_timer <= 0):
                boss_mode            = True
                boss_timer           = 300
                boss_triggered_phase = phase
                blocks.clear()
                add_floating_text(WIDTH // 2 - 80, HEIGHT // 2, "WARNING", (255, 80, 80))

            if boss_mode and not phase_transition:
                if len(blocks) < 8 and random.random() < 0.06:
                    spawn_block(random.choice(["wall_gap", "zigzag"]))
                boss_timer -= 1
                if boss_timer <= 0:
                    boss_mode = False
                    blocks.clear()
                    add_floating_text(WIDTH // 2 - 70, HEIGHT // 2, "BOSS CLEARED", (100, 255, 180))

            if not phase_transition:
                spawn_collectible()
                spawn_life_orb()

            # Blocks
            for b in blocks[:]:
                b.y += speed
                if b.y > HEIGHT:
                    blocks.remove(b)
                    score += 0.25
                    check_highscore(score)
                    continue
                if player.colliderect(b):
                    trigger_envelope("hit")
                    lives      -= 1
                    shake_timer = 12
                    flash_timer = 15
                    add_floating_text(player.x, player.y - 20, "-1 LIFE", (255, 80, 80))
                    add_particles(player.centerx, player.centery, (255, 60, 60), 15)
                    combo   = 1.0
                    blocks  = blocks[len(blocks) // 2:]
                    if lives <= 0:
                        state = "gameover"
                pygame.draw.rect(screen, (255, 50, 50),
                                 b.move(offset_x, offset_y), border_radius=6)

            # Collectibles
            for c in collectibles[:]:
                c.y += speed * 0.9
                if c.y > HEIGHT:
                    collectibles.remove(c)
                    continue
                if player.colliderect(c):
                    gain        = max(1, int(2 * combo))
                    score      += gain
                    check_highscore(score)
                    combo       = min(combo + 0.5, 8.0)
                    combo_timer = 120
                    speed_bonus += 0.2
                    add_floating_text(c.x, c.y, f"+{gain}", (255, 255, 0))
                    add_particles(c.centerx, c.centery, (255, 240, 0), 10)
                    trigger_envelope("pickup")
                    collectibles.remove(c)
                    continue
                pygame.draw.circle(screen, (255, 255, 0),
                                   (c.centerx + offset_x, c.centery + offset_y), 12)

            # Life orbs
            for orb in life_orbs[:]:
                orb.y += speed * 0.8
                if orb.y > HEIGHT:
                    life_orbs.remove(orb)
                    continue
                if player.colliderect(orb):
                    lives = min(5, lives + 1)
                    add_floating_text(orb.x, orb.y, "+1 LIFE", (0, 255, 100))
                    add_particles(orb.centerx, orb.centery, (0, 255, 100), 10)
                    trigger_envelope("life")
                    life_orbs.remove(orb)
                    continue
                pygame.draw.circle(screen, (0, 255, 100),
                                   (orb.centerx + offset_x, orb.centery + offset_y), 12)

            tick_envelope()

            # Phase transition countdown
            if phase_transition:
                phase_transition_timer -= 1
                if phase_transition_timer <= 0:
                    phase_transition = False
                    trigger_envelope("phase_end")

            speed_bonus *= 0.985

            # Player
            glow         = int(100 + 100 * math.sin(pygame.time.get_ticks() * 0.01))
            player_color = (0, glow, 200)
            pygame.draw.rect(screen, player_color,
                             player.move(offset_x, offset_y), border_radius=10)

            update_draw_particles(offset_x, offset_y)
            update_floating_texts()
            draw_floating_texts(offset_x, offset_y)
            draw_ui(score, lives, phase_name, combo, combo_timer)

            # Boss overlay
            if boss_mode:
                pulse_b   = int(200 + 55 * math.sin(pygame.time.get_ticks() * 0.015))
                boss_text = font_big.render("BOSS", True, (255, pulse_b, pulse_b))
                screen.blit(boss_text, (WIDTH // 2 - boss_text.get_width() // 2, 100))

            # Phase transition overlay
            if phase_transition:
                overlay = pygame.Surface((WIDTH, HEIGHT))
                overlay.set_alpha(120)
                overlay.fill((0, 0, 0))
                screen.blit(overlay, (0, 0))
                phase_big  = font_big.render(phase_name,        True, (255, 255, 255))
                relax_text = font.render("PREPARE YOUR FLOW",   True, (100, 200, 255))
                screen.blit(phase_big,
                            (WIDTH // 2 - phase_big.get_width() // 2,  HEIGHT // 2 - 40))
                screen.blit(relax_text,
                            (WIDTH // 2 - relax_text.get_width() // 2, HEIGHT // 2 + 20))

            # Hit flash
            if flash_timer > 0:
                flash = pygame.Surface((WIDTH, HEIGHT))
                flash.set_alpha(80)
                flash.fill((255, 0, 0))
                screen.blit(flash, (0, 0))
                flash_timer -= 1

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)   # yields control back to browser each frame

    pygame.quit()

asyncio.run(main())
