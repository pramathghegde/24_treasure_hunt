import pygame
import random


TILE = 40
COLS, ROWS = 20, 15
WALL, FLOOR, CHEST, KEY, TRAP = 0, 1, 2, 3, 4
SPEED = 3


def generate_world():
    grid = [[WALL] * COLS for _ in range(ROWS)]
    rooms = []
    for _ in range(8):
        w = random.randint(3, 6)
        h = random.randint(3, 5)
        x = random.randint(1, COLS-w-1)
        y = random.randint(1, ROWS-h-1)
        room = pygame.Rect(x, y, w, h)
        overlap = any(room.inflate(2, 2).colliderect(r) for r in rooms)
        if not overlap:
            rooms.append(room)
            for ry in range(y, y+h):
                for rx in range(x, x+w):
                    grid[ry][rx] = FLOOR

    for i in range(len(rooms)-1):
        ax, ay = rooms[i].centerx, rooms[i].centery
        bx, by = rooms[i+1].centerx, rooms[i+1].centery
        cx = ax
        while cx != bx:
            grid[ay][cx] = FLOOR
            cx += 1 if bx > cx else -1
        cy = ay
        while cy != by:
            grid[cy][bx] = FLOOR
            cy += 1 if by > cy else -1

    if len(rooms) >= 2:
        cr, ck = rooms[-1], rooms[-2]
        grid[cr.centery][cr.centerx] = CHEST
        grid[ck.centery][ck.centerx] = KEY

    if rooms:
        start = rooms[0]
        trap_cells = []

        for r in range(ROWS):
            for c in range(COLS):
                if grid[r][c] == FLOOR and not start.collidepoint(c, r):
                    trap_cells.append((r, c))

        for r, c in random.sample(trap_cells, min(8, len(trap_cells))):
            grid[r][c] = TRAP
    else:
        start = None

    return grid, start


COLORS = {
    WALL: (60, 50, 70),
    FLOOR: (200, 190, 170),
    CHEST: (200, 160, 30),
    KEY: (220, 220, 60),
    TRAP: (180, 50, 50),
}


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 28, 28)
        self.color = (60, 120, 220)
        self.has_key = False

    def move(self, keys, grid, rows, cols):
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = SPEED
        self._try_move(dx, 0, grid, rows, cols)
        self._try_move(0, dy, grid, rows, cols)

    def _try_move(self, dx, dy, grid, rows, cols):
        new = self.rect.move(dx, dy)
        for px, py in [
            (new.left, new.top),
            (new.right-1, new.top),
            (new.left, new.bottom-1),
            (new.right-1, new.bottom-1)
        ]:
            c, r = px // TILE, py // TILE
            if not (0 <= r < rows and 0 <= c < cols) or grid[r][c] == WALL:
                return
        self.rect = new

    def draw(self, screen):
        pygame.draw.ellipse(screen, self.color, self.rect)
        if self.has_key:
            pygame.draw.circle(
                screen,
                (220, 220, 60),
                (self.rect.right-6, self.rect.top+6),
                5
            )


class Guard:
    def __init__(self, point_a, point_b):
        self.rect = pygame.Rect(point_a[0], point_a[1], 28, 28)
        self.point_a = pygame.Vector2(point_a)
        self.point_b = pygame.Vector2(point_b)
        self.position = pygame.Vector2(point_a)
        self.target = self.point_b
        self.speed = 2
        self.color = (180, 40, 40)

    def update(self):
        direction = self.target - self.position
        distance = direction.length()

        if distance <= self.speed:
            self.position = self.target.copy()

            if self.target == self.point_b:
                self.target = self.point_a.copy()
            else:
                self.target = self.point_b.copy()
        else:
            direction.normalize_ip()
            self.position += direction * self.speed

        self.rect.topleft = (
            round(self.position.x),
            round(self.position.y)
        )

    def draw(self, screen):
        pygame.draw.rect(
            screen,
            self.color,
            self.rect,
            border_radius=6
        )

        pygame.draw.circle(
            screen,
            (240, 220, 200),
            (self.rect.centerx - 7, self.rect.centery - 3),
            4
        )
        pygame.draw.circle(
            screen,
            (240, 220, 200),
            (self.rect.centerx + 7, self.rect.centery - 3),
            4
        )

        pygame.draw.line(
            screen,
            (60, 20, 20),
            (self.rect.centerx - 8, self.rect.centery + 7),
            (self.rect.centerx + 8, self.rect.centery + 7),
            3
        )


WIDTH = COLS * TILE
HEIGHT = ROWS * TILE + 50
FPS = 60


class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Treasure Hunt")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 24)
        self.big_font = pygame.font.SysFont("monospace", 40, bold=True)
        self.reset()

    def _find_guard_patrol_points(self):
        chest_cell = None

        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] == CHEST:
                    chest_cell = (r, c)
                    break
            if chest_cell:
                break

        if chest_cell is None:
            return None

        candidates = []

        # Find horizontal floor segments.
        for r in range(ROWS):
            c = 0
            while c < COLS:
                if self.grid[r][c] != FLOOR:
                    c += 1
                    continue

                start_c = c
                while c < COLS and self.grid[r][c] == FLOOR:
                    c += 1

                end_c = c - 1

                if end_c - start_c + 1 >= 2:
                    point_a = (start_c * TILE + 6, r * TILE + 6)
                    point_b = (end_c * TILE + 6, r * TILE + 6)

                    mid_c = (start_c + end_c) / 2
                    distance = abs(mid_c - chest_cell[1]) + abs(r - chest_cell[0])

                    candidates.append(
                        (distance, point_a, point_b)
                    )

        # Find vertical floor segments.
        for c in range(COLS):
            r = 0
            while r < ROWS:
                if self.grid[r][c] != FLOOR:
                    r += 1
                    continue

                start_r = r
                while r < ROWS and self.grid[r][c] == FLOOR:
                    r += 1

                end_r = r - 1

                if end_r - start_r + 1 >= 2:
                    point_a = (c * TILE + 6, start_r * TILE + 6)
                    point_b = (c * TILE + 6, end_r * TILE + 6)

                    mid_r = (start_r + end_r) / 2
                    distance = abs(c - chest_cell[1]) + abs(mid_r - chest_cell[0])

                    candidates.append(
                        (distance, point_a, point_b)
                    )

        if candidates:
            candidates.sort(key=lambda item: item[0])
            _, point_a, point_b = candidates[0]
            return point_a, point_b

        return None

    def reset(self):
        self.grid, start = generate_world()
        if start:
            sx = start.x * TILE + 6
            sy = start.y * TILE + 6
        else:
            sx, sy = TILE+6, TILE+6

        self.player = Player(sx, sy)
        self.start_pos = (sx, sy)

        patrol_points = self._find_guard_patrol_points()

        if patrol_points:
            point_a, point_b = patrol_points
            self.guard = Guard(point_a, point_b)
        else:
            self.guard = None

        self.won = False
        self.status = "Find the KEY, then the CHEST!"

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.reset()
        return True

    def update(self):
        if self.won:
            return

        if self.guard:
            self.guard.update()

        keys = pygame.key.get_pressed()
        self.player.move(keys, self.grid, ROWS, COLS)

        if self.guard and self.player.rect.colliderect(self.guard.rect):
            self.player.rect.topleft = self.start_pos
            self.status = "Guard caught you! Back to start!"
            return

        pr = self.player.rect.centery // TILE
        pc = self.player.rect.centerx // TILE

        if 0 <= pr < ROWS and 0 <= pc < COLS:
            cell = self.grid[pr][pc]

            if cell == KEY:
                self.player.has_key = True
                self.grid[pr][pc] = FLOOR
                self.status = "Got the key! Find the CHEST!"

            elif cell == CHEST and self.player.has_key:
                self.won = True
                self.status = "Treasure found!"

            elif cell == TRAP:
                self.player.rect.topleft = self.start_pos
                self.status = "Trap! Back to start!"

    def _draw_minimap(self):
        # Keep the mini-map compact enough to remain a small overlay.
        map_tile = 6
        map_width = COLS * map_tile
        map_height = ROWS * map_tile

        margin = 10
        border = 4

        map_x = WIDTH - map_width - margin - border * 2
        map_y = margin + border

        background = pygame.Rect(
            map_x - border,
            map_y - border,
            map_width + border * 2,
            map_height + border * 2
        )

        pygame.draw.rect(
            self.screen,
            (15, 15, 25),
            background,
            border_radius=4
        )

        for r in range(ROWS):
            for c in range(COLS):
                cell = self.grid[r][c]

                if cell == WALL:
                    color = (35, 30, 45)
                else:
                    color = (190, 180, 160)

                mini_rect = pygame.Rect(
                    map_x + c * map_tile,
                    map_y + r * map_tile,
                    map_tile,
                    map_tile
                )

                pygame.draw.rect(
                    self.screen,
                    color,
                    mini_rect
                )

                if cell == CHEST:
                    pygame.draw.rect(
                        self.screen,
                        (220, 160, 30),
                        mini_rect.inflate(-2, -2)
                    )
                elif cell == KEY:
                    pygame.draw.rect(
                        self.screen,
                        (240, 220, 50),
                        mini_rect.inflate(-2, -2)
                    )
                elif cell == TRAP:
                    pygame.draw.rect(
                        self.screen,
                        (150, 40, 40),
                        mini_rect.inflate(-2, -2)
                    )

        player_col = self.player.rect.centerx // TILE
        player_row = self.player.rect.centery // TILE

        if 0 <= player_row < ROWS and 0 <= player_col < COLS:
            player_x = (
                map_x
                + player_col * map_tile
                + map_tile // 2
            )
            player_y = (
                map_y
                + player_row * map_tile
                + map_tile // 2
            )

            pygame.draw.circle(
                self.screen,
                (50, 130, 255),
                (player_x, player_y),
                3
            )

        pygame.draw.rect(
            self.screen,
            (220, 220, 220),
            background,
            1,
            border_radius=4
        )

    def draw(self):
        self.screen.fill((30, 25, 40))

        for r in range(ROWS):
            for c in range(COLS):
                cell = self.grid[r][c]
                rect = pygame.Rect(c*TILE, r*TILE, TILE, TILE)
                pygame.draw.rect(self.screen, COLORS[cell], rect)

                if cell == KEY:
                    pygame.draw.circle(
                        self.screen,
                        (255, 240, 60),
                        (c*TILE + TILE//2, r*TILE + TILE//2),
                        10
                    )
                elif cell == CHEST:
                    pygame.draw.rect(
                        self.screen,
                        (180, 120, 20),
                        rect.inflate(-12, -12),
                        border_radius=4
                    )
                elif cell == TRAP:
                    pygame.draw.line(
                        self.screen,
                        (80, 20, 20),
                        (c*TILE+8, r*TILE+8),
                        (c*TILE+TILE-8, r*TILE+TILE-8),
                        4
                    )
                    pygame.draw.line(
                        self.screen,
                        (80, 20, 20),
                        (c*TILE+TILE-8, r*TILE+8),
                        (c*TILE+8, r*TILE+TILE-8),
                        4
                    )

        if self.guard:
            self.guard.draw(self.screen)

        self.player.draw(self.screen)

        # Task 3: draw the mini-map from the current dungeon grid.
        self._draw_minimap()

        hud = pygame.Rect(0, ROWS*TILE, WIDTH, 50)
        pygame.draw.rect(self.screen, (20, 20, 35), hud)

        st = self.font.render(
            self.status + "  |  R=Restart",
            True,
            (200, 200, 200)
        )
        self.screen.blit(st, (8, ROWS*TILE+13))

        if self.won:
            ov = pygame.Surface(
                (WIDTH, ROWS*TILE),
                pygame.SRCALPHA
            )
            ov.fill((0, 0, 0, 140))
            self.screen.blit(ov, (0, 0))

            msg = self.big_font.render(
                "TREASURE FOUND!",
                True,
                (220, 180, 30)
            )
            sub = self.font.render(
                "Press R to Play Again",
                True,
                (180, 180, 180)
            )

            self.screen.blit(
                msg,
                (
                    WIDTH//2-msg.get_width()//2,
                    ROWS*TILE//2-30
                )
            )
            self.screen.blit(
                sub,
                (
                    WIDTH//2-sub.get_width()//2,
                    ROWS*TILE//2+20
                )
            )

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    engine = GameEngine()
    engine.run()