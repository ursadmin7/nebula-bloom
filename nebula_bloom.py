import argparse
import math
import random
import pygame

WIDTH, HEIGHT = 1100, 760
TAU = math.tau


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def mix(a, b, t):
    return a + (b - a) * t


def smoothstep(a, b, x):
    if a == b:
        return 0.0
    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def glow(surface, position, radius, color, strength=1.0):
    radius = max(2, int(radius))
    layer = pygame.Surface(
        (radius * 4 + 2, radius * 4 + 2), pygame.SRCALPHA
    )
    center = radius * 2 + 1

    for i in range(7, 0, -1):
        r = max(1, int(radius * i / 7))
        alpha = int(clamp(strength) * (18 + (7 - i) * 7))
        pygame.draw.circle(
            layer, (*color, min(150, alpha)), (center, center), r
        )

    surface.blit(
        layer,
        (int(position[0] - center), int(position[1] - center)),
        special_flags=pygame.BLEND_RGBA_ADD,
    )


def draw_background(surface, t):
    surface.fill((3, 6, 18))
    haze = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    w, h = surface.get_size()

    for i in range(8):
        y = int(h * (0.22 + i * 0.075))
        alpha = int(8 + 7 * (0.5 + 0.5 * math.sin(t * 0.3 + i)))
        pygame.draw.ellipse(
            haze,
            (28, 35, 105, alpha),
            (int(w * 0.12), y - 70, int(w * 0.76), 160),
        )

    surface.blit(haze, (0, 0))


class Particle:
    def __init__(self, rng):
        self.rng = rng
        self.reset(initial=True)

    def reset(self, initial=False):
        self.x = self.rng.uniform(20, WIDTH - 20)
        self.y = self.rng.uniform(0, HEIGHT) if initial else HEIGHT + 10
        self.speed = self.rng.uniform(10, 46)
        self.phase = self.rng.uniform(0, TAU)
        self.size = self.rng.choice((1, 1, 1, 2, 2, 3))
        self.color = self.rng.choice(
            (
                (45, 185, 255),
                (255, 177, 65),
                (255, 70, 197),
                (115, 100, 255),
            )
        )

    def update(self, dt, t):
        self.y -= self.speed * dt
        self.x += math.sin(t * 0.7 + self.phase) * 9 * dt
        if self.y < -10:
            self.reset()

    def draw(self, surface, t):
        pulse = 0.55 + 0.45 * math.sin(t * 2.4 + self.phase)
        color = tuple(int(c * pulse) for c in self.color)
        pygame.draw.circle(
            surface, color, (int(self.x), int(self.y)), self.size
        )
        if self.size >= 2 and pulse > 0.82:
            glow(surface, (self.x, self.y), 5, self.color, 0.45)


def petal_point(center, angle, length, width, u, side=0):
    breadth = math.sin(math.pi * (u ** 0.78)) ** 0.78
    lateral = side * width * breadth
    bend = math.sin(u * math.pi) * 9
    lx, ly = length * u, lateral + bend
    ca, sa = math.cos(angle), math.sin(angle)

    return (
        center[0] + lx * ca - ly * sa,
        center[1] + lx * sa + ly * ca,
    )


def draw_petal(surface, center, angle, length, width, color_a, color_b, t, index, bloom):
    steps = 30

    top = [
        petal_point(center, angle, length * bloom, width * bloom, i / steps, 1)
        for i in range(steps + 1)
    ]
    bottom = [
        petal_point(center, angle, length * bloom, width * bloom, i / steps, -1)
        for i in range(steps, -1, -1)
    ]

    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.polygon(layer, (*color_a, 36), top + bottom)
    pygame.draw.lines(layer, (*color_b, 220), False, top, 2)
    pygame.draw.lines(layer, (*color_a, 150), False, bottom, 1)
    surface.blit(layer, (0, 0))

    tip = petal_point(center, angle, length * bloom, width * bloom, 0.98)
    pygame.draw.line(
        surface, color_b, tuple(map(int, center)), tuple(map(int, tip)), 2
    )

    for k in range(1, 8):
        u = k / 9
        p1 = petal_point(center, angle, length * bloom, width * bloom, u)
        p2 = petal_point(
            center, angle, length * bloom, width * bloom,
            min(0.98, u + 0.13), 0.5 if k % 2 else -0.5
        )
        pulse = 0.5 + 0.5 * math.sin(t * 2 + index + k)
        color = tuple(
            int(mix(color_a[j], color_b[j], pulse)) for j in range(3)
        )
        pygame.draw.line(
            surface, color, tuple(map(int, p1)), tuple(map(int, p2)), 1
        )


def draw_orbits(surface, center, t):
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    orbits = (
        (330, 95, (27, 156, 255)),
        (360, 115, (255, 166, 53)),
        (285, 75, (99, 76, 255)),
    )

    for i, (rx, ry, color) in enumerate(orbits):
        rect = pygame.Rect(0, 0, rx * 2, ry * 2)
        rect.center = (
            int(center[0]),
            int(center[1] + 65 + i * 3),
        )
        pygame.draw.ellipse(layer, (*color, 100), rect, 1)

        angle = t * (0.35 + i * 0.12) + i * 1.7
        point = (
            center[0] + math.cos(angle) * rx,
            center[1] + 65 + i * 3 + math.sin(angle) * ry,
        )

        pygame.draw.circle(layer, (*color, 230), tuple(map(int, point)), 3)
        glow(layer, point, 12, color, 0.7)

    surface.blit(layer, (0, 0))


def draw_bloom(surface, t):
    cx, cy = WIDTH * 0.5, HEIGHT * 0.49
    center = (cx, cy)
    breath = 1 + 0.025 * math.sin(t * 1.1)
    bloom = smoothstep(0, 2.2, t) * breath

    draw_orbits(surface, center, t)

    palette = [
        ((255, 44, 165), (255, 190, 86)),
        ((80, 54, 255), (43, 220, 255)),
        ((255, 53, 188), (100, 123, 255)),
        ((27, 154, 255), (255, 94, 202)),
    ]

    for i in range(8):
        angle = -math.pi / 2 + i * TAU / 8
        angle += 0.06 * math.sin(t * 0.45 + i)

        length = (205 if i % 2 == 0 else 170) * breath
        width = 79 if i % 2 == 0 else 68
        color_a, color_b = palette[i % len(palette)]

        origin = (
            cx - math.cos(angle) * 10,
            cy - math.sin(angle) * 10,
        )

        draw_petal(
            surface, origin, angle, length, width,
            color_a, color_b, t, i, bloom
        )

    glow(surface, center, 75, (255, 111, 49), 0.8)
    glow(surface, center, 42, (255, 205, 84), 1.0)
    pygame.draw.circle(surface, (255, 225, 142), (int(cx), int(cy)), 8)
    pygame.draw.circle(surface, (255, 255, 238), (int(cx), int(cy)), 3)

    for i in range(27):
        angle = i / 27 * TAU + 0.15 * math.sin(t * 0.8)
        length = 34 + 52 * ((i * 7) % 13) / 13
        sway = math.sin(t * 1.8 + i * 1.9) * 5

        end = (
            cx + math.cos(angle) * length + sway,
            cy + math.sin(angle) * length * 0.82,
        )

        pygame.draw.line(
            surface, (255, 172, 57),
            (int(cx), int(cy)), tuple(map(int, end)), 2
        )
        pygame.draw.circle(
            surface, (255, 220, 110), tuple(map(int, end)), 3
        )

        if i % 3 == 0:
            glow(surface, end, 10, (255, 174, 49), 0.65)


def main():
    parser = argparse.ArgumentParser(
        description="NEBULA BLOOM — cinematic cosmic flower animation"
    )
    parser.add_argument("--width", type=int, default=WIDTH)
    parser.add_argument("--height", type=int, default=HEIGHT)
    parser.add_argument("--fps", type=int, default=60)
    args = parser.parse_args()

    if args.width < 640 or args.height < 480 or args.fps < 1:
        parser.error("width >= 640, height >= 480, and fps >= 1 are required")

    pygame.init()
    screen = pygame.display.set_mode(
        (args.width, args.height), pygame.RESIZABLE
    )
    pygame.display.set_caption("NEBULA BLOOM | Procedural Cosmic Flower")

    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 24, bold=True)
    small = pygame.font.SysFont("consolas", 12)
    rng = random.Random(27)
    particles = [Particle(rng) for _ in range(145)]
    design = pygame.Surface((WIDTH, HEIGHT))

    t = 0.0
    paused = False
    running = True

    try:
        while running:
            dt = min(clock.tick(args.fps) / 1000, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif event.key == pygame.K_SPACE:
                        paused = not paused
                    elif event.key == pygame.K_s:
                        pygame.image.save(screen, "nebula-bloom.png")
                        print("Screenshot saved: nebula-bloom.png")

            if not paused:
                t += dt
                for particle in particles:
                    particle.update(dt, t)

            draw_background(design, t)

            for particle in particles:
                particle.draw(design, t)

            draw_bloom(design, t)

            design.blit(
                font.render("NEBULA BLOOM", True, (205, 224, 255)),
                (28, 24),
            )
            design.blit(
                small.render(
                    "A PROCEDURAL COSMIC FLOWER / PYTHON + PYGAME",
                    True, (104, 135, 186)
                ),
                (30, 59),
            )

            status = "PAUSED" if paused else "LIVE"
            status_color = (
                (255, 190, 80) if paused else (75, 225, 205)
            )
            label = small.render(
                f"{status} | SPACE pause | S screenshot | ESC quit",
                True, status_color,
            )
            design.blit(label, (28, HEIGHT - 32))

            pygame.draw.line(
                design, (32, 54, 88), (28, 88), (WIDTH - 28, 88), 1
            )
            pygame.draw.line(
                design, (45, 187, 255), (28, 88),
                (28 + int((WIDTH - 56) * ((t % 60) / 60)), 88), 2
            )

            scaled = pygame.transform.smoothscale(
                design, screen.get_size()
            )
            screen.blit(scaled, (0, 0))
            pygame.display.flip()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()