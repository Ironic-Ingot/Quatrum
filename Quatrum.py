import pygame
import random
import json
from gamelib.ui import UI
from gamelib.particles import ParticleManager
from pathlib import Path

WIDTH = 800
HEIGHT = 990
FPS = 60
BASE_DIR = Path(__file__).parent

PIECES = (
    (
        (
            (1, 1),
            (1, 1),
        ),
        (220, 210, 55)
    ),
    (
        (
            (0, 1, 0),
            (0, 1, 0),
            (0, 1, 1)
        ),
        (35, 65, 215)
    ),
    (
        (
            (0, 1, 0),
            (0, 1, 0),
            (1, 1, 0)
        ),
        (215, 140, 35)
    ),
    (
        (
            (0, 1, 1),
            (1, 1, 0),
            (0, 0, 0)
        ),
        (35, 205, 65)
    ),
    (
        (
            (1, 1, 0),
            (0, 1, 1),
            (0, 0, 0)
        ),
        (215, 45, 45)
    ),
    (
        (
            (0, 1, 0),
            (1, 1, 1),
            (0, 0, 0)
        ),
        (150, 55, 215)
    ),
    (
        (
            (0, 1, 0),
            (0, 1, 0),
            (0, 1, 0),
            (0, 1, 0)
        ),
        (35, 210, 210)
    ),
)

def draw_block(screen, color, rect, alpha=255):
    x, y, size, _ = rect
    block = pygame.Surface((size, size), pygame.SRCALPHA)
    smaller = 0.8*size
    pygame.draw.rect(
        block,
        [i/1.5 for i in color],
        (0, 0, size, size)
    )
    pygame.draw.rect(
        block,
        color,
        (
            size - smaller,
            size - smaller,
            size - (size - smaller) * 2,
            size - (size - smaller) * 2
        )
    )
    block.set_alpha(alpha)
    screen.blit(block, (x, y))

class Piece:
    def __init__(self, shape: list, color, x, y, landed=False, hard_drop=False):
        self.shape = shape
        self.color = color
        self.x = x
        self.y = y
        self.landed = landed
        self.hard_drop = hard_drop
    
    def rotate(self, grid, amount):
        if amount > 0:
            for _ in range(amount):
                rotated_shape = [list(row) for row in zip(*self.shape[::-1])]
        elif amount < 0:
            for _ in range(amount*-1):
                rotated_shape = [list(row) for row in list(zip(*self.shape))[::-1]]
        if self.can_place(grid, rotated_shape, self.x, self.y, 0, 0):
            self.shape = rotated_shape
            
    def fall(self, grid, land=False, get=False):
        check_y = self.y
        if self.can_place(grid, self.shape, self.x, check_y, 0, 1):
            check_y += 1
            if not get:
                self.y = check_y
        else:
            if not get:
                self.y = check_y
                self.landed = True
        return check_y
    
    def land(self, grid, get=False):
        check_y = self.y
        while self.can_place(grid, self.shape, self.x, check_y, 0, 1):
            check_y += 1
        else:
            if not get:
                self.hard_drop = True
                self.y = check_y
                self.landed = True
        return check_y
            
    def move(self, grid, amount):
        if self.can_place(grid, self.shape, self.x, self.y, amount, 0):
            self.x += amount

    def can_place(self, grid, shape, x_pos, y_pos, x_offset, y_offset):
        for y, rows in enumerate(shape):
            for x, cell in enumerate(rows):
                if cell and len(grid) <= (y_pos + y + y_offset):
                    return False
                if cell and not 0 <= (x_pos + x + x_offset) < len(grid[0]):
                    return False
                elif cell and grid[y_pos + y + y_offset][x_pos + x + x_offset]:
                    return False
        return True

    def draw(self, size, screen, land_y=None, alpha=255):
        for y, rows in enumerate(self.shape):
            for x, cell in enumerate(rows):
                if cell:
                    draw_block(screen, self.color, ((x+self.x)*size + size, (y+(self.y if land_y is None else land_y))*size + size, size, size), alpha)

    def to_dict(self):
        return {
            "shape": self.shape,
            "color": self.color,
            "x": self.x,
            "y": self.y,
            "landed": self.landed,
            "hard_drop": self.hard_drop,
        }

class Game:
    def __init__(self):
        pygame.init()

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.fixed_screen = pygame.Surface((WIDTH, HEIGHT))
        pygame.display.set_caption("Quatrum")
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        self.default_fall_timer = 0.6
        self.fall_timer = self.default_fall_timer
        self.fall_speed_multiplier = 1
        
        self.grid = [[0 for column in range(10)] for row in range(20)]
        self.cell_size = 45
        
        self.cleared_lines = 0
        self.score = 0
        self.high_score = 0
        
        self.bag = list(PIECES)
        random.shuffle(self.bag)
        self.pieces = [self.create_piece(4, 0), self.create_piece(12, 2)]
        
        self.scene = 'main_menu'
        
        self.particles = ParticleManager()

        self.clearing_lines = False
        self.clear_timer = 0
        self.lines_to_clear = []
        
        self.ghost_piece = True
        
        self.load()
        self.setup_ui()
        self.update_labels()

    #region UI Setup
    def setup_ui(self):
        self.main_menu_ui = UI()
        self.pause_ui = UI()
        self.game_over_ui = UI()
        self.settings_ui = UI()
        self.game_ui = UI()
        default_label_kwargs = {
            'text_size': 75,
            'text_color': (220, 220, 220),
            'background': True,
            'padding': 15,
            'background_size': (0, 0),
            'background_color': (30, 30, 30),
            'border_radius': 15
        }
        self.setup_game_over_ui(default_label_kwargs)
        self.setup_game_ui(default_label_kwargs)
        self.setup_pause_ui(default_label_kwargs)
        self.setup_settings_ui(default_label_kwargs)
        self.setup_main_menu_ui(default_label_kwargs)
        
    def setup_game_over_ui(self, default_label_kwargs):
        self.game_over_ui.create_label("title", (12*self.cell_size, 350), 'Game Over', **(default_label_kwargs | {'text_size': 120, 'background_color': (180, 50, 50)}))
        self.game_over_ui.create_button('restart', lambda: (self.change_scene('playing'), self.restart_game()), (0, 0), 'Restart', **(default_label_kwargs | {'text_size': 90}))
        self.game_over_ui.create_overlay("bgoverlay", pygame.Vector2(WIDTH, HEIGHT), color=(10, 10, 10), alpha=100)
        self.game_over_ui.buttons["restart"].set_center((WIDTH / 2, + (HEIGHT / 2) - 20))
        self.game_over_ui.labels["title"].set_center((WIDTH / 2, + (HEIGHT / 2) - 150))
    
    def setup_main_menu_ui(self, default_label_kwargs):
        self.main_menu_ui.create_label("title", (12*self.cell_size, 350), 'Quatrum', **(default_label_kwargs | {'text_size': 160, 'text_color': (170, 60, 170), 'background_color': (90, 20, 90)}))
        self.main_menu_ui.create_button('play', lambda: self.change_scene('playing'), (0, 0), 'Continue' if self.score > 0 else 'Start', **(default_label_kwargs | {'text_size': 100}))
        self.main_menu_ui.create_button("quit", self.quit, (0, 0), 'Quit', **default_label_kwargs)
        self.main_menu_ui.create_overlay("bgoverlay", pygame.Vector2(WIDTH, HEIGHT), color=(10, 10, 10), alpha=255)
        self.main_menu_ui.labels["title"].set_center((WIDTH / 2, + (HEIGHT / 2) - 200))
        self.main_menu_ui.buttons["quit"].set_center((WIDTH / 2, + (HEIGHT / 2) + 120))
        self.main_menu_ui.buttons["play"].set_center((WIDTH / 2, + (HEIGHT / 2)))
        
    def setup_game_ui(self, default_label_kwargs):
        self.game_ui.create_label("score", (12*self.cell_size, 350), f'Score\n[   ]', **default_label_kwargs)
        self.game_ui.create_label("lines", (12*self.cell_size, 550), f'Lines\n[   ]', **default_label_kwargs)
        self.game_ui.create_label("high_score", (12*self.cell_size, 750), f'HiScore\n[   ]', **default_label_kwargs)

    def setup_pause_ui(self, default_label_kwargs):
        self.pause_ui.create_button("continue", lambda: self.change_scene('playing'), (0, 0), 'Continue', **default_label_kwargs)
        self.pause_ui.create_button("settings", lambda: self.change_scene('settings'), (0, 0), 'Settings', **default_label_kwargs)
        self.pause_ui.create_button("restart", self.restart_game, (0, 0), 'Restart', **default_label_kwargs)
        self.pause_ui.create_button("quit", self.quit, (0, 0), 'Quit', **default_label_kwargs)
        self.pause_ui.buttons["continue"].set_center((WIDTH / 2, + (HEIGHT / 2) - 180))
        self.pause_ui.buttons["settings"].set_center((WIDTH / 2, + (HEIGHT / 2) - 80))
        self.pause_ui.buttons["restart"].set_center((WIDTH / 2, -50 + (HEIGHT / 2) + 70))
        self.pause_ui.buttons["quit"].set_center((WIDTH / 2, + (HEIGHT / 2) + 120))
        self.pause_ui.create_overlay("bgoverlay", pygame.Vector2(WIDTH, HEIGHT), alpha=100)

    def setup_settings_ui(self, default_label_kwargs):
        self.settings_ui.create_overlay("bgoverlay", pygame.Vector2(WIDTH, HEIGHT), alpha=175)
        self.settings_ui.create_button("ghost", self.set_ghost_piece, (0, 0), 'Toggle Ghost', toggle_colors=((180, 30, 30), (30, 180, 30)), **default_label_kwargs, state=self.ghost_piece)
        self.settings_ui.create_button("save", self.save, (0, 0), 'Save', **default_label_kwargs)
        self.settings_ui.buttons["save"].set_center((WIDTH / 2, + (HEIGHT / 2) - 50))
        self.settings_ui.buttons["ghost"].set_center((WIDTH / 2, + (HEIGHT / 2) - 180))
    #endregion

    #region Helpers
    def change_scene(self, scene: str):
        self.scene = scene

    def quit(self):
        self.running = False
        
    def set_ghost_piece(self, boolean):
        self.ghost_piece = boolean

    def update_labels(self):
        self.game_ui.labels["lines"].update_text(f'Lines\n[ {self.cleared_lines} ]')
        self.game_ui.labels["score"].update_text(f'Score\n[ {self.score} ]')
        self.game_ui.labels["high_score"].update_text(f'HiScore\n[ {self.high_score} ]')
        
    def restart_game(self):
        self.pieces.clear()
        self.pieces.append(self.create_piece(4, 0))
        self.pieces.append(self.create_piece(12, 2))
        self.grid = [[0 for column in range(10)] for row in range(20)]
        self.cleared_lines = 0
        self.score = 0
        self.update_labels()
        self.save()
    #endregion

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000

            self.handle_events()
            self.update(dt)
            self.draw()
            
        pygame.quit()

    def handle_events(self): 
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            # if event.type == pygame.WINDOWRESIZED:
                # self.adjust_to_screen()

            if event.type == pygame.KEYDOWN:
                match(event.key):
                    case pygame.K_q:
                        self.running = False
                if self.scene == "playing" and not self.clearing_lines:
                    match(event.key):
                        case pygame.K_SPACE:
                            self.pieces[0].land(self.grid)
                        case pygame.K_a:
                            self.pieces[0].move(self.grid, -1)
                        case pygame.K_d:
                            self.pieces[0].move(self.grid, 1)
                        case pygame.K_RIGHT:
                            self.pieces[0].rotate(self.grid, 1)
                        case pygame.K_LEFT:
                            self.pieces[0].rotate(self.grid, -1)
                if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                    match(self.scene):
                        case 'playing':
                            self.change_scene('paused')
                        case 'paused':
                            self.change_scene('playing')
                        case 'settings':
                            self.change_scene('paused')
                
        keys = pygame.key.get_pressed()
        if self.scene == "playing":
            if keys[pygame.K_s]:
                self.fall_timer = min(self.fall_timer, 0.03)
                self.cleared_lines = 15      

    def update(self, dt):
        if self.scene != 'playing':
            mouse_buttons = pygame.mouse.get_pressed()
            mouse_pos = pygame.Vector2(*pygame.mouse.get_pos())
            screen_x_scale, screen_y_scale =self.screen.get_size()
            screen_x_scale /= WIDTH
            screen_y_scale /= HEIGHT
            mouse_x = mouse_pos.x / screen_x_scale
            mouse_y = mouse_pos.y / screen_y_scale
            match(self.scene):
                case 'paused':
                    self.pause_ui.update(mouse_buttons, pygame.Vector2(mouse_x, mouse_y))
                case 'settings':
                    self.settings_ui.update(mouse_buttons, pygame.Vector2(mouse_x, mouse_y))
                case 'main_menu':
                    self.main_menu_ui.update(mouse_buttons, pygame.Vector2(mouse_x, mouse_y))
                case 'game_over':
                    self.game_over_ui.update(mouse_buttons, pygame.Vector2(mouse_x, mouse_y))
                case _:
                    pass
            
            
        if self.scene == 'playing':
            self.particles.update(dt)
            if self.clearing_lines:
                self.clear_timer -= dt

                if self.clear_timer <= 0:
                    for line in self.lines_to_clear:
                        self.grid.pop(line)
                        self.grid.insert(0, [0 for cell in range(len(self.grid[0]))])
                    self.lines_to_clear = []
                    self.clearing_lines = False
                    self.clear_timer = 1
            
            if self.fall_timer <= 0 and not self.clearing_lines:
                self.pieces[0].fall(self.grid)
                self.fall_timer = self.default_fall_timer
            self.fall_timer -= dt * self.fall_speed_multiplier
            
            cleared_lines_now = 0
            for y in range(len(self.grid)):
                if all(self.grid[y]):
                    cleared_lines_now += 1
                    self.cleared_lines += 1
                    self.lines_to_clear.append(y)
                    self.clearing_lines = True
                    self.clear_timer = 1.0
                    for i, cell in enumerate(self.grid[y]):
                        if not cell:
                            color = (0, 0, 0, 255)
                        else:
                            color = [*cell, 255]
                        self.particles.spawn(
                            pygame.Vector2((i+1)*self.cell_size, (y+1)*self.cell_size),
                            spawn_range=pygame.Vector2(self.cell_size, self.cell_size),
                            amount=4,
                            size=self.cell_size/3,
                            lifetime=120,
                            start_speed=1,
                            color=color
                        )
                        self.grid[y] = [0 for _ in range(len(self.grid[y]))]
                        
            self.fall_speed_multiplier = 1 + (self.cleared_lines // 5) / 3
                        
            if cleared_lines_now != 0:
                self.score += [0, 100, 300, 500, 800][cleared_lines_now]
                self.update_labels()
            
            if self.pieces[0].landed:
                for y, rows in enumerate(self.pieces[0].shape):
                    for x, cell in enumerate(rows):
                        if not cell:
                            continue
                        
                        self.grid[self.pieces[0].y + y][self.pieces[0].x + x] = self.pieces[0].color
                        self.score += 1 + self.pieces[0].hard_drop
                        
                        if self.pieces[0].hard_drop:
                            color = [*self.pieces[0].color, 255]
                            self.particles.spawn(
                                pos=pygame.Vector2((self.pieces[0].x + x + 1)*self.cell_size, (self.pieces[0].y + y + 1)*self.cell_size),
                                spawn_range=pygame.Vector2(self.cell_size, self.cell_size),
                                amount=3,
                                size=15,
                                lifetime=60,
                                start_speed=30,
                                color=color,
                                direction=pygame.Vector2(0, -1),
                                spread= 17,
                                slowdown=0.87
                            )

                self.pieces.pop(0)
                self.pieces[0].x = 4
                self.pieces[0].y = 0
                self.pieces.append(self.create_piece(12, 2))
                if not self.pieces[0].can_place(self.grid, self.pieces[0].shape, 4, 0, 0, 0):
                    self.scene = 'game_over'

                if self.score > self.high_score:
                    self.high_score = self.score
                self.save()
                self.update_labels()

    def draw(self):
        self.fixed_screen.fill("black")
        if self.ghost_piece:
            self.pieces[0].draw(self.cell_size, self.fixed_screen, land_y=self.pieces[0].land(self.grid, get=True), alpha=100)
        
        for piece in self.pieces:
            piece.draw(self.cell_size, self.fixed_screen)

        self.draw_grid(self.grid, self.cell_size, self.fixed_screen)
        self.draw_container(self.fixed_screen, self.cell_size)
        
        self.game_ui.draw(self.fixed_screen)
        self.particles.draw(self.fixed_screen)
        if self.scene == 'paused':
            self.pause_ui.draw(self.fixed_screen)
        if self.scene == 'main_menu':
            self.main_menu_ui.draw(self.fixed_screen)
        if self.scene == 'settings':
            self.settings_ui.draw(self.fixed_screen)
        if self.scene == 'game_over':
            self.game_over_ui.draw(self.fixed_screen)
            
        
        
        scaled = pygame.transform.scale(self.fixed_screen, self.screen.get_size())
        self.screen.blit(scaled, (0, 0))
        
        pygame.display.flip()
            
    def draw_grid(self, grid, size, screen):
        ROWS = len(grid)
        COLUMNS = len(grid[0])
        grid_line_width = size*0.045
        offset = size - (grid_line_width/4)
        for y, rows in enumerate(grid):
            for x, cell in enumerate(rows):
                if cell:
                    draw_block(
                        screen,
                        cell,
                        (
                            x*size + size,
                            y*size + size,
                            size, size
                        )
                    )

        grid_color = [185 for _ in range(3)]
        for column in range(COLUMNS+1):
            pygame.draw.rect(screen, grid_color, (column*size + offset, offset, grid_line_width, ROWS*size))
        for row in range(ROWS+1):
            pygame.draw.rect(screen, grid_color, (offset, row*size + offset, COLUMNS*size, grid_line_width))
            
    def draw_container(self, screen, size):
        for y in [0, 21*size]:
            for x in range(0, 18*size, size):
                draw_block(
                    screen,
                    (150, 150, 150),
                    (x, y, size, size)
                )
        for x in [0, 11*size]:
            for y in range(size, size*21, size):
                draw_block(
                    screen,
                    (150, 150, 150),
                    (x, y, size, size)
                )
        # for x in range(12*size, 20*size, size):
        #     for y in range(size, 17*size, size):
        #         draw_block(
        #             screen,
        #             (150, 150, 150),
        #             (x, y, size, size)
        #         )
            
    def create_piece(self, x, y, piece: int=None):
        if not self.bag:
            self.bag = list(PIECES)
            random.shuffle(self.bag)
            
        if piece is None:
            shape, color = self.bag[-1]
            self.bag.pop()
        else:
            shape, color = self.pieces[piece]
        return Piece([row[:] for row in shape], color, x, y)
    
    def save(self):
        with open(BASE_DIR / 'GameData/saved.json', "w") as file:
            self.save_data = {
                "high_score": self.high_score,
                "score": self.score,
                "cleared_lines": self.cleared_lines,
                "grid": self.grid,
                "pieces": [piece.to_dict() for piece in self.pieces],
                "ghost": self.ghost_piece
            }
            json.dump(self.save_data, file, indent=4)
        
    def load(self):
        try:
            with open(BASE_DIR / 'GameData/saved.json', "r") as file:
                self.save_data: dict = json.load(file)
                self.high_score = self.save_data.get('high_score', 0)
                self.score = self.save_data.get('score', 0)
                self.cleared_lines = self.save_data.get('cleared_lines', 0)
                self.ghost_piece = self.save_data.get('ghost', True)
                self.grid = self.save_data.get('grid', self.grid)
                self.pieces = [Piece(**piece) for piece in self.save_data.get('pieces', [])] or self.pieces
        except (FileNotFoundError, json.JSONDecodeError):
            self.save()
            
game = Game()
game.run()