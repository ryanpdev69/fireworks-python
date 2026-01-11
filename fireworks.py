import curses
import time
import random
import math
import os
import sys

# Check for pygame availability for sound
try:
    import pygame
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False
    print("pygame not installed. Running without sound.")
    print("Install with: pip install pygame")
    time.sleep(2)

FPS = 0.03
BPM = 120
BEAT_INTERVAL = 60 / BPM
SHOW_TIME = 20
MESSAGE = "HAPPY NEW YEAR EBRIWAN"

COLORS = [
    curses.COLOR_RED,
    curses.COLOR_YELLOW,
    curses.COLOR_GREEN,
    curses.COLOR_CYAN,
    curses.COLOR_BLUE,
    curses.COLOR_MAGENTA,
    curses.COLOR_WHITE,
]

# Firework pattern types
PATTERNS = ['burst', 'ring', 'willow', 'palm', 'chrysanthemum', 'peony']

class SoundManager:
    def __init__(self):
        self.enabled = SOUND_AVAILABLE
        if self.enabled:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.sounds = {}
            self.generate_sounds()
    
    def generate_sounds(self):
        """Generate procedural explosion sounds"""
        try:
            # Launch whoosh
            self.sounds['launch'] = self.create_whoosh()
            # Explosion sounds with varying pitches
            self.sounds['boom1'] = self.create_explosion(150)
            self.sounds['boom2'] = self.create_explosion(100)
            self.sounds['boom3'] = self.create_explosion(200)
            self.sounds['crackle'] = self.create_crackle()
        except:
            self.enabled = False
    
    def create_whoosh(self):
        duration = 0.3
        sample_rate = 22050
        samples = int(duration * sample_rate)
        wave = []
        for i in range(samples):
            freq = 200 + (i / samples) * 400
            value = int(8000 * math.sin(2 * math.pi * freq * i / sample_rate) * (1 - i/samples))
            wave.append([value, value])
        return pygame.sndarray.make_sound(wave)
    
    def create_explosion(self, base_freq):
        duration = 0.5
        sample_rate = 22050
        samples = int(duration * sample_rate)
        wave = []
        for i in range(samples):
            decay = 1 - (i / samples)
            noise = random.randint(-1, 1) * 10000 * decay
            sine = int(3000 * math.sin(2 * math.pi * base_freq * i / sample_rate) * decay)
            value = int((noise + sine) * 0.7)
            wave.append([value, value])
        return pygame.sndarray.make_sound(wave)
    
    def create_crackle(self):
        duration = 0.2
        sample_rate = 22050
        samples = int(duration * sample_rate)
        wave = []
        for i in range(samples):
            value = random.randint(-5000, 5000) * (1 - i/samples)
            wave.append([int(value), int(value)])
        return pygame.sndarray.make_sound(wave)
    
    def play(self, sound_name):
        if self.enabled and sound_name in self.sounds:
            self.sounds[sound_name].play()

class Particle:
    def __init__(self, x, y, color, pattern='burst'):
        self.pattern = pattern
        
        if pattern == 'ring':
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.5, 2.0)
        elif pattern == 'willow':
            angle = random.uniform(-math.pi/3, -2*math.pi/3)
            speed = random.uniform(0.8, 1.5)
        elif pattern == 'palm':
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2.0, 3.0)
        elif pattern == 'chrysanthemum':
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.0, 2.5)
        else:  # burst/peony
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.8, 2.5)
        
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.x = x
        self.y = y
        self.life = random.randint(15, 35)
        self.max_life = self.life
        self.color = color
        self.trail = []
        self.char = self.get_char()
        
    def get_char(self):
        chars = ['*', '+', 'o', '●', '◆', '✦', '✧']
        return random.choice(chars)
    
    def update(self):
        self.trail.append((int(self.y), int(self.x)))
        trail_length = 8 if self.pattern == 'willow' else 5
        if len(self.trail) > trail_length:
            self.trail.pop(0)
        
        self.x += self.vx
        self.y += self.vy
        
        # Gravity and air resistance vary by pattern
        if self.pattern == 'willow':
            self.vy += 0.15
            self.vx *= 0.98
        elif self.pattern == 'palm':
            self.vy += 0.05
            self.vx *= 0.99
        else:
            self.vy += 0.1
            self.vx *= 0.98
        
        self.life -= 1
    
    def draw(self, stdscr):
        brightness = self.life / self.max_life
        
        # Draw trail with fading effect
        for i, (ty, tx) in enumerate(self.trail):
            try:
                trail_brightness = (i / len(self.trail)) * brightness
                if trail_brightness > 0.5:
                    stdscr.addstr(ty, tx, "·", curses.color_pair(self.color))
                else:
                    stdscr.addstr(ty, tx, ".", curses.A_DIM)
            except:
                pass
        
        # Draw particle
        if self.life > 0:
            try:
                attr = curses.color_pair(self.color)
                if brightness > 0.7:
                    attr |= curses.A_BOLD
                stdscr.addstr(int(self.y), int(self.x), self.char, attr)
            except:
                pass

class Firework:
    def __init__(self, w, h, sound_manager, pattern=None):
        self.x = random.randint(15, w - 15)
        self.y = h - 2
        self.peak = random.randint(5, h // 3)
        self.exploded = False
        self.particles = []
        self.sound_manager = sound_manager
        self.pattern = pattern or random.choice(PATTERNS)
        self.color = random.randint(1, len(COLORS))
        self.multi_stage = random.random() < 0.15  # 15% chance of multi-stage
        self.stage = 0
        self.launch_trail = []  # Trail while rocket is ascending
        
    def explode(self):
        if self.stage == 0:
            self.sound_manager.play(f'boom{random.randint(1,3)}')
        
        # Reduced particle counts for smaller fireworks
        particle_counts = {
            'ring': 30,
            'willow': 40,
            'palm': 50,
            'chrysanthemum': 60,
            'peony': 45,
            'burst': 35
        }
        count = particle_counts.get(self.pattern, 35)
        
        for _ in range(count):
            self.particles.append(Particle(self.x, self.y, self.color, self.pattern))
        
        # Add fewer sparkles for some patterns
        if self.pattern in ['chrysanthemum', 'peony']:
            for _ in range(15):
                p = Particle(self.x, self.y, 7, 'burst')  # white sparkles
                p.life = random.randint(8, 15)
                self.particles.append(p)
        
        self.exploded = True
        self.stage += 1
    
    def update(self):
        if not self.exploded:
            # Add to launch trail
            self.launch_trail.append((int(self.y), self.x))
            if len(self.launch_trail) > 8:
                self.launch_trail.pop(0)
            
            self.y -= 1.5
            if self.y <= self.peak:
                self.explode()
        else:
            for p in self.particles:
                p.update()
            self.particles = [p for p in self.particles if p.life > 0]
            
            # Multi-stage fireworks
            if self.multi_stage and self.stage == 1 and len(self.particles) < 20:
                self.sound_manager.play('crackle')
                for _ in range(15):  # Reduced from 30
                    new_color = random.randint(1, len(COLORS))
                    self.particles.append(Particle(self.x, self.peak, new_color, 'burst'))
                self.stage += 1
    
    def draw(self, stdscr):
        if not self.exploded:
            try:
                # Draw launch trail (white smoke trail)
                for i, (ty, tx) in enumerate(self.launch_trail):
                    trail_char = "·" if i < len(self.launch_trail) - 2 else "|"
                    stdscr.addstr(ty, tx, trail_char, curses.color_pair(7) | curses.A_DIM)
                
                # Rising rocket
                stdscr.addstr(int(self.y), self.x, "^", curses.color_pair(7) | curses.A_BOLD)
            except:
                pass
        else:
            for p in self.particles:
                p.draw(stdscr)

def finale(stdscr, h, w, sound_manager):
    """Grand finale with many simultaneous fireworks"""
    fireworks = []
    for _ in range(15):
        fw = Firework(w, h, sound_manager, random.choice(['chrysanthemum', 'peony', 'palm']))
        fw.y = random.randint(5, h // 2)
        fw.explode()
        fireworks.append(fw)
    
    for _ in range(60):
        stdscr.clear()
        for fw in fireworks:
            fw.update()
            fw.draw(stdscr)
        stdscr.refresh()
        time.sleep(FPS)

def text_explosion(stdscr, h, w, sound_manager):
    """Animated text reveal with fireworks"""
    start_x = max(0, (w - len(MESSAGE)) // 2)
    y = h // 2
    
    fireworks = []
    for i, ch in enumerate(MESSAGE):
        if start_x + i < w:
            fw = Firework(w, h, sound_manager, 'burst')
            fw.x = start_x + i
            fw.y = y
            fw.color = (i % len(COLORS)) + 1
            fw.explode()
            fireworks.append(fw)
    
    # Animate the explosion
    for frame in range(50):
        stdscr.clear()
        for fw in fireworks:
            fw.update()
            fw.draw(stdscr)
        
        # Reveal text gradually
        if frame > 20:
            try:
                msg_color = curses.color_pair(random.randint(1, len(COLORS))) | curses.A_BOLD
                stdscr.addstr(y, start_x, MESSAGE, msg_color)
            except:
                pass
        
        stdscr.refresh()
        time.sleep(FPS)

def main(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    stdscr.nodelay(True)
    
    for i, c in enumerate(COLORS, 1):
        curses.init_pair(i, c, -1)
    
    sound_manager = SoundManager()
    h, w = stdscr.getmaxyx()
    
    fireworks = []
    last_launch = time.time()
    start = time.time()
    consecutive_launch_interval = 0.15  # Launch every 0.15 seconds for rapid fire
    fast_launch_interval = 1.0  # Launch every 1 second after consecutive phase
    
    while time.time() - start < SHOW_TIME:
        stdscr.clear()
        elapsed = time.time() - start
        
        # First 3 seconds: Consecutive rapid launches
        if elapsed < 3:
            if time.time() - last_launch >= consecutive_launch_interval:
                fw = Firework(w, h, sound_manager)
                sound_manager.play('launch')
                fireworks.append(fw)
                last_launch = time.time()
        
        # After 3 seconds: Fast but spaced launches (every 1 second)
        else:
            if time.time() - last_launch >= fast_launch_interval:
                fw = Firework(w, h, sound_manager)
                sound_manager.play('launch')
                fireworks.append(fw)
                last_launch = time.time()
        
        for fw in fireworks:
            fw.update()
            fw.draw(stdscr)
        
        fireworks = [f for f in fireworks if not (f.exploded and not f.particles)]
        
        # Check for quit
        try:
            key = stdscr.getch()
            if key == ord('q'):
                break
        except:
            pass
        
        stdscr.refresh()
        time.sleep(FPS)
    
    # Grand finale
    finale(stdscr, h, w, sound_manager)
    time.sleep(1)
    
    # Text explosion
    text_explosion(stdscr, h, w, sound_manager)
    time.sleep(3)

if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\nFireworks show ended!")
    finally:
        if SOUND_AVAILABLE:
            pygame.mixer.quit()