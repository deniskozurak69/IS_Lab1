import pygame
import sys
import random
import math
from collections import deque

CELL_SIZE = 40
GRID_WIDTH = 15
GRID_HEIGHT = 15
SCREEN_WIDTH = CELL_SIZE * GRID_WIDTH
SCREEN_HEIGHT = CELL_SIZE * GRID_HEIGHT
POINTS_TO_NEXT_LEVEL = 15
ENEMY_MOVE_INTERVAL = 400
LEVEL_COUNT = 7
HUD_HEIGHT = 40

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT + HUD_HEIGHT))
pygame.display.set_caption("Pac-Man")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 24)

BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
GREY = (127, 127, 127)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
PURPLE = (255, 0, 255)
ORANGE = (255, 165, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)

BANDS = [(0, 0), (1, 3), (4, 6), (7, 9), (10, 12), (13, 14)]

player_pos = [GRID_WIDTH // 2, GRID_HEIGHT // 2]
last_player_direction = (0, 0)
score = 0
level = 1
team_mode = 0
enemy_positions = [(0, 0), (GRID_WIDTH - 1, 0), (0, GRID_HEIGHT - 1), (GRID_WIDTH - 1, GRID_HEIGHT - 1)]
enemy_team_mode = False
enemy_roles = ["random", "random", "random", "random"]
mouth_angle = 45
mouth_closing = True
deadlocks = []
last_enemy_move_time = pygame.time.get_ticks()
last_player_move_time = pygame.time.get_ticks()
game_over = False
game_won = False
show_trajectories = False
difficulty_labels = {1: "very easy", 2: "easy", 3: "normal", 4: "hard", 5: "very hard"}
team_target_1=tuple(player_pos)
team_target_2=tuple(player_pos)

def get_difficulty(level):
    return difficulty_labels.get(level, "insane")

def generate_grid():
    grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if (x, y) != tuple(player_pos) and random.random() < 0.2:
                grid[y][x] = 1
    return grid

def generate_barriers(level):
    barriers = set()
    row_count = GRID_HEIGHT // 3
    used_rows = set()
    while len(used_rows) < row_count:
        y = 3 * random.randint(1, GRID_HEIGHT // 3) - 2
        if y not in used_rows:
            used_rows.add(y)
            gap_positions = random.sample(range(1, GRID_WIDTH - 1), 1)
            for x in range(1, GRID_WIDTH - 1):
                if x not in gap_positions:
                    a = (x, y)
                    b = (x, y - 1)
                    barriers.add((a, b))
                    barriers.add((b, a))
    sorted_rows = sorted(used_rows)
    for i in range(len(sorted_rows) - 1):
        y_cur = sorted_rows[i]
        x1 = random.randint(1, GRID_WIDTH - 2)
        x2 = x1
        while x2 == x1:
            x2 = random.randint(1, GRID_WIDTH - 2)
        for j in range(0, 2):
            a = (x1, y_cur + j)
            b = (x1 + 1, y_cur + j)
            barriers.add((a, b))
            barriers.add((b, a))
        for j in range(1, 3):
            a = (x2, y_cur + j)
            b = (x2 + 1, y_cur + j)
            barriers.add((a, b))
            barriers.add((b, a))
    return barriers, sorted_rows

def generate_adjacency(barriers):
    adjacency = {}
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            current = (x, y)
            neighbors = []
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                neighbor = (nx, ny)
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    if ((current, neighbor) not in barriers):
                        neighbors.append(neighbor)
            adjacency[current] = neighbors
    return adjacency

def is_connected(start, adjacency):
    visited = set()
    queue = deque()
    queue.append(start)
    visited.add(start)
    while queue:
        current = queue.popleft()
        for neighbor in adjacency.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return visited

def generate_valid_barriers(level, grid):
    barriers, sorted_rows = generate_barriers(level)
    while True:
        adjacency = generate_adjacency(barriers)
        reachable = is_connected(tuple(player_pos), adjacency)
        food_cells = {(x, y) for y in range(GRID_HEIGHT) for x in range(GRID_WIDTH) if grid[y][x] == 1}
        if food_cells.issubset(reachable):
            return barriers, adjacency, sorted_rows
        barrier_pairs = list({(a, b) for (a, b) in barriers if (b, a) in barriers and a < b})
        if barrier_pairs:
            a, b = random.choice(barrier_pairs)
            barriers.discard((a, b))
            barriers.discard((b, a))
        else:
            return set(), generate_adjacency(set()), []

def bfs(start, goal, adjacency):
    queue = deque()
    queue.append((start, [start]))
    visited = set()
    visited.add(start)
    while queue:
        current, path = queue.popleft()
        if current == goal:
            return path
        for neighbor in adjacency.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return None

def get_zone(y):
    for i, (ymin, ymax) in enumerate(BANDS):
        if ymin <= y <= ymax:
            return i
    return None

def get_target_for_predicter(player_pos):
    neighbors = adjacency.get(enemy_positions[1], [])
    if tuple(player_pos) in neighbors:
        return tuple(player_pos)
    else:
        predicted_pos = (
            player_pos[0] + 2 * last_player_direction[0],
            player_pos[1] + 2 * last_player_direction[1]
        )
        if (0 <= predicted_pos[0] < GRID_WIDTH and 0 <= predicted_pos[1] < GRID_HEIGHT):
            return tuple(predicted_pos)
        else:
            return tuple(player_pos)

def get_target_for_ghost2(player_pos):
    neighbors = adjacency.get(enemy_positions[1], [])
    if tuple(player_pos) in neighbors:
        return tuple(player_pos)
    else:
        x, y = player_pos
        xg, yg = enemy_positions[1]
        player_zone = get_zone(y)
        ghost_zone = get_zone(yg)
        if player_zone is None or player_zone == 0:
            return tuple(player_pos)
        elif player_zone == ghost_zone:
            return tuple(player_pos)
        else:
            ymin, ymax = BANDS[player_zone - 1]
            return (x, ymax)

def get_target_for_ghost3(player_pos):
    neighbors = adjacency.get(enemy_positions[2], [])
    if tuple(player_pos) in neighbors:
        return tuple(player_pos)
    else:
        x, y = player_pos
        xg, yg = enemy_positions[2]
        player_zone = get_zone(y)
        ghost_zone = get_zone(yg)
        if player_zone is None or player_zone == len(BANDS) - 1:
            return tuple(player_pos)
        elif player_zone == ghost_zone:
            return tuple(player_pos)
        else:
            ymin, ymax = BANDS[player_zone + 1]
            return (x, ymin)

def draw_grid(grid):
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE + HUD_HEIGHT, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, BLUE, rect, 1)
            if grid[y][x] == 1:
                pygame.draw.circle(screen, WHITE, rect.center, 5)

def draw_barriers(barriers):
    for (a, b) in barriers:
        if a < b:
            x1, y1 = a
            x2, y2 = b
            if y1 == y2:
                x = min(x1, x2)
                y = y1
                start = (x * CELL_SIZE + CELL_SIZE, y * CELL_SIZE + HUD_HEIGHT)
                end = (x * CELL_SIZE + CELL_SIZE, y * CELL_SIZE + CELL_SIZE + HUD_HEIGHT)
                pygame.draw.line(screen, RED, start, end, 4)
            elif x1 == x2:
                x = x1
                y = min(y1, y2)
                start = (x * CELL_SIZE, y * CELL_SIZE + CELL_SIZE + HUD_HEIGHT)
                end = (x * CELL_SIZE + CELL_SIZE, y * CELL_SIZE + CELL_SIZE + HUD_HEIGHT)
                pygame.draw.line(screen, RED, start, end, 4)

def draw_pacman(pos):
    global mouth_angle, mouth_closing
    if not game_over:
        if mouth_closing:
            mouth_angle -= 1
            if mouth_angle <= 1:
                mouth_closing = False
        else:
            mouth_angle += 1
            if mouth_angle >= 25:
                mouth_closing = True
    else:
        mouth_angle = 1
    x, y = pos
    center = (x * CELL_SIZE + CELL_SIZE // 2, y * CELL_SIZE + CELL_SIZE // 2 + HUD_HEIGHT)
    pygame.draw.circle(screen, YELLOW, center, CELL_SIZE // 2 - 4)
    radius = CELL_SIZE // 2 - 4
    dx, dy = last_player_direction
    angle_offset = 0
    if dx == 1 and dy == 0:
        angle_offset = 0
    elif dx == 0 and dy == -1:
        angle_offset = 90
    elif dx == -1 and dy == 0:
        angle_offset = 180
    elif dx == 0 and dy == 1:
        angle_offset = 270
    points = [center]
    for angle in range(angle_offset - mouth_angle, angle_offset + mouth_angle + 1, 2):
        rad = math.radians(angle)
        x_point = center[0] + radius * math.cos(rad)
        y_point = center[1] - radius * math.sin(rad)
        points.append((x_point, y_point))
    pygame.draw.polygon(screen, BLACK, points)
    eye_offset_x, eye_offset_y = 0, -radius // 2
    if dx == 1:
        eye_offset_x, eye_offset_y = 5, -10
    elif dx == -1:
        eye_offset_x, eye_offset_y = -5, -10
    elif dy == -1:
        eye_offset_x, eye_offset_y = -7, -5
    elif dy == 1:
        eye_offset_x, eye_offset_y = -7, 5
    elif dx == 0 and dy == 0:
        eye_offset_x, eye_offset_y = 5, -10
    eye_pos = (center[0] + eye_offset_x, center[1] + eye_offset_y)
    pygame.draw.circle(screen, BLACK, eye_pos, 4)

def draw_enemies():
    role_colors = {'bfs': PURPLE, 'predict': RED, 'random': ORANGE, 'food_hunter': GREY}
    if not enemy_positions:
        init_enemies_for_level()
    if not enemy_team_mode:
        colors = [role_colors.get(role, GREY) for role in enemy_roles]
    else:
        if team_mode == 2:
            colors = [PURPLE, BLUE, BLUE, ORANGE]
        else:
            colors = [PURPLE, GREEN, GREEN, ORANGE]
        if len(enemy_roles) > 3:
            colors[3] = role_colors.get(enemy_roles[3], GREY)
    for i, (ex, ey) in enumerate(enemy_positions):
        color = colors[i % len(colors)]
        scale = 0.75
        w = int(CELL_SIZE * scale)
        h = int(CELL_SIZE * scale * 1.2)
        x_pix = ex * CELL_SIZE + (CELL_SIZE - w) // 2
        y_pix = ey * CELL_SIZE + (CELL_SIZE - h) // 2 + HUD_HEIGHT
        pygame.draw.circle(screen, color, (x_pix + w // 2, y_pix + h // 2 - 6), w // 2)
        rect = pygame.Rect(x_pix, y_pix + h // 2 - 6, w, h // 2 + 6)
        pygame.draw.rect(screen, color, rect)
        left_leg = [(x_pix, y_pix + h), (x_pix + w // 4, y_pix + h), (x_pix + w // 4, y_pix + h - 8)]
        pygame.draw.polygon(screen, BLACK, left_leg)
        center_leg = [(x_pix + w // 2 - 6, y_pix + h), (x_pix + w // 2 + 6, y_pix + h), (x_pix + w // 2, y_pix + h - 10)]
        pygame.draw.polygon(screen, BLACK, center_leg)
        right_leg = [(x_pix + w * 3 // 4, y_pix + h), (x_pix + w, y_pix + h), (x_pix + w * 3 // 4, y_pix + h - 8)]
        pygame.draw.polygon(screen, BLACK, right_leg)
        eye_radius = 4
        eye_dx = 6
        eye_dy = -2
        pygame.draw.circle(screen, WHITE, (x_pix + w // 2 - eye_dx, y_pix + h // 2 - 8 + eye_dy), eye_radius)
        pygame.draw.circle(screen, WHITE, (x_pix + w // 2 + eye_dx, y_pix + h // 2 - 8 + eye_dy), eye_radius)
        pupil_radius = 1
        pygame.draw.circle(screen, BLACK, (x_pix + w // 2 - eye_dx, y_pix + h // 2 - 8 + eye_dy), pupil_radius)
        pygame.draw.circle(screen, BLACK, (x_pix + w // 2 + eye_dx, y_pix + h // 2 - 8 + eye_dy), pupil_radius)

def draw_trajectories(tp2,tp3):
    if not show_trajectories:
        return
    role_colors = {'bfs': PURPLE, 'predict': RED, 'random': ORANGE, 'food_hunter': GREY}
    if not enemy_team_mode:
        colors = [role_colors.get(role, GREY) for role in enemy_roles]
    else:
        if team_mode == 2:
            colors = [PURPLE, BLUE, BLUE, ORANGE]
        else:
            colors = [PURPLE, GREEN, GREEN, ORANGE]
        if len(enemy_roles) > 3:
            colors[3] = role_colors.get(enemy_roles[3], GREY)
    for i, pos in enumerate(enemy_positions):
        color = colors[i % len(colors)]
        role = enemy_roles[i] if i < len(enemy_roles) else 'bfs'
        target = None
        if enemy_team_mode:
            if i == 0:
                target = tuple(player_pos)
            elif i == 1:
                target = get_target_for_ghost2(player_pos) if team_mode == 1 else tp2
            elif i == 2:
                target = get_target_for_ghost3(player_pos) if team_mode == 1 else tp3
            elif i == 3:
                target = get_target_for_predicter(player_pos) if enemy_roles[3] == 'predict' else get_target_for_food_hunter(player_pos)
        else:
            if role == 'bfs':
                target = tuple(player_pos)
            elif role == 'predict':
                target = get_target_for_predicter(player_pos)
            elif role == 'random':
                neighbors = adjacency.get(pos, [])
                target = tuple(player_pos) if tuple(player_pos) in neighbors else random.choice(neighbors) if neighbors else pos
            elif role == 'food_hunter':
                target = get_target_for_food_hunter(player_pos)
        if target:
            path = bfs(pos, target, adjacency)
            if path and len(path) > 1:
                for j in range(len(path) - 1):
                    x1, y1 = path[j]
                    x2, y2 = path[j + 1]
                    start = (x1 * CELL_SIZE + CELL_SIZE // 2, y1 * CELL_SIZE + CELL_SIZE // 2 + HUD_HEIGHT)
                    end = (x2 * CELL_SIZE + CELL_SIZE // 2, y2 * CELL_SIZE + CELL_SIZE // 2 + HUD_HEIGHT)
                    pygame.draw.line(screen, CYAN, start, end, 2)
                tx, ty = target
                target_center = (tx * CELL_SIZE + CELL_SIZE // 2, ty * CELL_SIZE + CELL_SIZE // 2 + HUD_HEIGHT)
                pygame.draw.circle(screen, color, target_center, 8, 2)

def draw_info():
    points_cnt = score % POINTS_TO_NEXT_LEVEL
    if score==POINTS_TO_NEXT_LEVEL*LEVEL_COUNT: points_cnt = POINTS_TO_NEXT_LEVEL
    text = font.render(f"Level: {level}/{LEVEL_COUNT} | Difficulty: {get_difficulty(level)} | Points: {points_cnt}/{POINTS_TO_NEXT_LEVEL}", True, WHITE)
    screen.blit(text, (10, 10))
    toggle_text = font.render("Show Paths: " + ("ON" if show_trajectories else "OFF"), True, WHITE)
    toggle_rect = toggle_text.get_rect(topright=(SCREEN_WIDTH - 10, 10))
    screen.blit(toggle_text, toggle_rect)
    return toggle_rect

def reset_game():
    global player_pos, last_player_direction, score, level
    global game_over, game_won, grid, barriers, adjacency, sorted_rows
    global enemy_positions, enemy_roles, enemy_team_mode, team_mode

    player_pos = [GRID_WIDTH // 2, GRID_HEIGHT // 2]
    last_player_direction = (0, 0)
    score = 0
    level = 1
    game_over = False
    game_won = False
    team_mode = 0

    grid = generate_grid()
    barriers, adjacency, sorted_rows = generate_valid_barriers(level, grid)
    init_enemies_for_level()

def draw_game_over():
    if game_won:
        text = font.render("Congratulations! You won!", True, (100, 255, 100))
    else:
        text = font.render("Game over!", True, (255, 100, 100))
    rect = text.get_rect(center=(SCREEN_WIDTH // 2, (SCREEN_HEIGHT + HUD_HEIGHT) // 2))
    screen.blit(text, rect)

def find_nearest_food_to_player(grid, player_pos, adjacency):
    visited = set()
    queue = deque()
    queue.append(player_pos)
    visited.add(player_pos)
    while queue:
        current = queue.popleft()
        x, y = current
        if grid[y][x] == 1:
            return current
        for neighbor in adjacency.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return None

def get_target_for_food_hunter(player_pos):
    neighbors = adjacency.get(enemy_positions[3], [])
    if tuple(player_pos) in neighbors:
        return tuple(player_pos)
    else:
        target_food = find_nearest_food_to_player(grid, tuple(player_pos), adjacency)
        if target_food:
            return tuple(target_food)
        else:
            return tuple(player_pos)

def no_barrier_between(a, b):
    return (a, b) not in barriers

def init_enemies_for_level():
    global enemy_positions, enemy_team_mode, enemy_roles
    enemy_positions = [(0, 0), (GRID_WIDTH - 1, 0), (0, GRID_HEIGHT - 1), (GRID_WIDTH - 1, GRID_HEIGHT - 1)]
    enemy_team_mode = False
    if level > 5:
        enemy_team_mode = True
    if enemy_team_mode:
        if random.random() < 0.5:
            enemy_roles = ['bfs', 'team', 'team', 'predict']
        else:
            enemy_roles = ['bfs', 'team', 'team', 'food_hunter']
    else:
        if level == 1:
            enemy_roles = ['random', 'random', 'random', 'random']
        elif level == 2:
            enemy_roles = ['bfs', 'random', 'random', 'random']
        elif level == 3:
            if random.random() < 0.5:
                enemy_roles = ['bfs', 'predict', 'random', 'random']
            else:
                enemy_roles = ['bfs', 'food_hunter', 'random', 'random']
        elif level == 4:
            if random.random() < 0.5:
                enemy_roles = ['bfs', 'predict', 'food_hunter', 'random']
            else:
                enemy_roles = ['bfs', 'food_hunter', 'predict', 'random']
        else:
            if random.random() < 0.5:
                enemy_roles = ['bfs', 'predict', 'food_hunter', 'predict']
            else:
                enemy_roles = ['bfs', 'food_hunter', 'predict', 'food_hunter']

grid = generate_grid()
barriers, adjacency, sorted_rows = generate_valid_barriers(level, grid)
init_enemies_for_level()

running = True
while running:
    screen.fill(BLACK)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and not game_over:
            mouse_pos = event.pos
            toggle_rect = draw_info()
            if toggle_rect.collidepoint(mouse_pos):
                show_trajectories = not show_trajectories
        elif not game_over and event.type == pygame.KEYDOWN:
            x, y = player_pos
            direction = {
                pygame.K_LEFT: (-1, 0),
                pygame.K_RIGHT: (1, 0),
                pygame.K_UP: (0, -1),
                pygame.K_DOWN: (0, 1),
            }.get(event.key)
            if direction:
                dx, dy = direction
                new_pos = (x + dx, y + dy)
                if new_pos in adjacency.get((x, y), []):
                    player_pos = list(new_pos)
                    last_player_direction = (dx, dy)
                    if grid[player_pos[1]][player_pos[0]] == 1:
                        grid[player_pos[1]][player_pos[0]] = 0
                        score += 1
                        if score >= POINTS_TO_NEXT_LEVEL * level:
                            if level == LEVEL_COUNT:
                                game_won = True
                                game_over = True
                            else:
                                level += 1
                                if random.random() < 0.5:
                                    team_mode = 1
                                else:
                                    team_mode = 2
                                player_pos = [GRID_WIDTH // 2, GRID_HEIGHT // 2]
                                last_player_direction = (0, 0)
                                grid = generate_grid()
                                barriers, adjacency, sorted_rows = generate_valid_barriers(level, grid)
                                init_enemies_for_level()

    if not game_over:
        current_time = pygame.time.get_ticks()
        if current_time - last_enemy_move_time > ENEMY_MOVE_INTERVAL:
            new_positions = []
            px, py = player_pos
            if enemy_team_mode:
                if team_mode == 1:
                    main_path = bfs(enemy_positions[0], tuple(player_pos), adjacency)
                    new_positions.append(main_path[1])
                    t2 = get_target_for_ghost2(player_pos)
                    path2 = bfs(enemy_positions[1], t2, adjacency)
                    t3 = get_target_for_ghost3(player_pos)
                    path3 = bfs(enemy_positions[2], t3, adjacency)
                    if path2 and len(path2) >= 2 and path2[1] not in new_positions:
                        new_positions.append(path2[1])
                    else:
                        new_positions.append(enemy_positions[1])
                    if path3 and len(path3) >= 2 and path3[1] not in new_positions:
                        new_positions.append(path3[1])
                    else:
                        new_positions.append(enemy_positions[2])
                elif team_mode == 2:
                    path0 = bfs(enemy_positions[0], tuple(player_pos), adjacency)
                    if path0 and len(path0) >= 2:
                        new_positions.append(path0[1])
                    else:
                        new_positions.append(enemy_positions[0])
                    i = None
                    for idx in range(len(sorted_rows) - 1):
                        if sorted_rows[idx] <= player_pos[1] < sorted_rows[idx + 1]:
                            i = idx
                            break
                    if i is None:
                        if player_pos[1] < sorted_rows[0]:
                            i = -1
                        else:
                            i = len(sorted_rows) - 1
                    if i == -1:
                        target_pos_2 = tuple(player_pos)
                    else:
                        target_row_2 = sorted_rows[i] if sorted_rows else 0
                        target_pos_2 = None
                        for x in range(1, GRID_WIDTH - 1):
                            cell = (x, target_row_2)
                            above = (x, target_row_2 - 1)
                            if 0 <= above[1] < GRID_HEIGHT:
                                if no_barrier_between(cell, above):
                                    target_pos_2 = cell
                                    break
                        if target_pos_2 is None:
                            target_pos_2 = tuple(player_pos)
                    team_target_1=target_pos_2
                    path1 = bfs(enemy_positions[1], target_pos_2, adjacency)
                    neighbors = adjacency.get(enemy_positions[1], [])
                    if tuple(player_pos) in neighbors:
                        new_positions.append(tuple(player_pos))
                    else:
                        if path1 and len(path1) >= 2 and path1[1] not in new_positions:
                            new_positions.append(path1[1])
                        else:
                            new_positions.append(enemy_positions[1])
                    if i == len(sorted_rows) - 1:
                        target_pos_3 = tuple(player_pos)
                    else:
                        if sorted_rows and len(sorted_rows) >= 2 and i + 1 < len(sorted_rows):
                            target_row_3 = sorted_rows[i + 1] - 1
                        else:
                            target_row_3 = min(GRID_HEIGHT - 2, (sorted_rows[0] + 1) if sorted_rows else GRID_HEIGHT // 2)
                        target_pos_3 = None
                        for x in range(1, GRID_WIDTH - 1):
                            cell = (x, target_row_3)
                            below = (x, target_row_3 + 1)
                            if 0 <= below[1] < GRID_HEIGHT:
                                if no_barrier_between(cell, below):
                                    target_pos_3 = cell
                                    break
                        if target_pos_3 is None:
                            target_pos_3 = tuple(player_pos)
                    team_target_2 = target_pos_3
                    path2 = bfs(enemy_positions[2], target_pos_3, adjacency)
                    neighbors = adjacency.get(enemy_positions[2], [])
                    if tuple(player_pos) in neighbors:
                        new_positions.append(tuple(player_pos))
                    else:
                        if path2 and len(path2) >= 2 and path2[1] not in new_positions:
                            new_positions.append(path2[1])
                        else:
                            new_positions.append(enemy_positions[2])
                if enemy_roles[3] == 'predict':
                    t4 = get_target_for_predicter(player_pos)
                elif enemy_roles[3] == 'food_hunter':
                    t4 = get_target_for_food_hunter(player_pos)
                path4 = bfs(enemy_positions[3], t4, adjacency)
                if path4 and len(path4) >= 2 and path4[1] not in new_positions:
                    new_positions.append(path4[1])
                else:
                    new_positions.append(enemy_positions[3])
            else:
                for i, pos in enumerate(enemy_positions):
                    role = enemy_roles[i] if i < len(enemy_roles) else 'bfs'
                    if role == 'bfs':
                        target = tuple(player_pos)
                        path = bfs(pos, target, adjacency)
                        if path and len(path) >= 2:
                            next_step = path[1]
                            if next_step in new_positions:
                                new_positions.append(enemy_positions[i])
                            else:
                                new_positions.append(next_step)
                        else:
                            new_positions.append(pos)
                    elif role == 'predict':
                        predicted_pos = (
                            player_pos[0] + 2 * last_player_direction[0],
                            player_pos[1] + 2 * last_player_direction[1]
                        )
                        neighbors = adjacency.get(pos, [])
                        if tuple(player_pos) in neighbors:
                            new_positions.append(tuple(player_pos))
                        elif (0 <= predicted_pos[0] < GRID_WIDTH and 0 <= predicted_pos[1] < GRID_HEIGHT):
                            target = predicted_pos
                        else:
                            target = tuple(player_pos)
                        path = bfs(pos, target, adjacency)
                        if path and len(path) >= 2:
                            next_step = path[1]
                            if next_step in new_positions:
                                new_positions.append(enemy_positions[i])
                            else:
                                new_positions.append(next_step)
                        else:
                            new_positions.append(pos)
                    elif role == 'random':
                        neighbors = adjacency.get(pos, [])
                        if tuple(player_pos) in neighbors:
                            new_positions.append(tuple(player_pos))
                        elif neighbors:
                            new_positions.append(random.choice(neighbors))
                        else:
                            new_positions.append(pos)
                    elif role == "food_hunter":
                        target_food = find_nearest_food_to_player(grid, tuple(player_pos), adjacency)
                        neighbors = adjacency.get(pos, [])
                        if tuple(player_pos) in neighbors:
                            new_positions.append(tuple(player_pos))
                        elif target_food:
                            path_to_food = bfs(pos, target_food, adjacency)
                            if path_to_food and len(path_to_food) > 1:
                                next_step = path_to_food[1]
                                if next_step not in new_positions:
                                    new_positions.append(next_step)
                                else:
                                    new_positions.append(pos)
                            else:
                                new_positions.append(pos)
                        else:
                            new_positions.append(pos)
                    else:
                        path = bfs(pos, tuple(player_pos), adjacency)
                        if path and len(path) >= 2:
                            next_step = path[1]
                            if next_step in new_positions:
                                new_positions.append(enemy_positions[i])
                            else:
                                new_positions.append(next_step)
                        else:
                            new_positions.append(pos)
            enemy_positions = new_positions
            last_enemy_move_time = current_time
            for enemy in enemy_positions:
                if tuple(player_pos) == enemy:
                    game_over = True

    draw_grid(grid)
    draw_barriers(barriers)
    draw_pacman(player_pos)
    draw_enemies()
    draw_trajectories(team_target_1, team_target_2)
    draw_info()
    if game_over:
        draw_game_over()
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
