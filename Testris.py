import pygame
import random
import json
from gamelib.ui import UI
from pathlib import Path

WIDTH = 800
HEIGHT = 1000
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

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Tetris")
        
        
        
        self.grid = [[0 for column in range(10)] for row in range(20)]
        self.clock = pygame.time.Clock()
        self.running = True
        self.default_fall_timer = 0.6
        self.fall_timer = self.default_fall_timer
        self.cell_size = 45
        self.cleared_lines = 0
        self.score = 0
        self.high_score = 0
        self.bag = list(PIECES)
        random.shuffle(self.bag)
        self.pieces = [self.create_piece(4, 0), self.create_piece(12, 2)]
        self.scene = 'playing'
        self.pause_ui = UI()
        self.ui = UI()
        default_label_args = (75, (220, 220, 220), True, 15, (0, 0), (30, 30, 30))
        self.lines_label = self.ui.create_label((530, 550), f'Lines\n[   ]', *default_label_args)
        self.score_label = self.ui.create_label((530, 350), f'Score\n[   ]', *default_label_args)
        self.high_score_label = self.ui.create_label((530, 750), f'HiScore\n[   ]', *default_label_args)
        self.continue_button = self.pause_ui.create_button(lambda: self.change_scene('playing'), (WIDTH/2, HEIGHT/2), 'Continue', *default_label_args) # i know doesnt perfectly center
        
        self.load()

        self.update_labels()

    def change_scene(self, scene: str):
        self.scene = scene

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000

            self.handle_events(dt)
            self.update(dt)
            self.draw()
            
        pygame.quit()

    def handle_events(self, dt): 
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    self.running = False
                if event.key == pygame.K_SPACE:
                    self.pieces[0].land(self.grid)
                if event.key == pygame.K_a:
                    self.pieces[0].move(self.grid, -1)
                if event.key == pygame.K_d:
                    self.pieces[0].move(self.grid, 1)
                if event.key == pygame.K_RIGHT:
                    self.pieces[0].rotate(self.grid, 1)
                if event.key == pygame.K_LEFT:
                    self.pieces[0].rotate(self.grid, -1)
                if event.key == pygame.K_p:
                    self.change_scene('paused')
                
        keys = pygame.key.get_pressed()
        if keys[pygame.K_s]:
            self.fall_timer = min(self.fall_timer, 0.03)
                                

    def update(self, dt):
        if self.scene == 'paused':
            mouse_buttons = pygame.mouse.get_pressed()
            mouse_pos = pygame.mouse.get_pos()
            self.pause_ui.update(mouse_buttons, mouse_pos)
        if self.scene == 'playing':
            if self.fall_timer <= 0:
                self.pieces[0].fall(self.grid)
                self.fall_timer = self.default_fall_timer
            self.fall_timer -= dt
            
            cleared_lines_now = 0
            for y in range(len(self.grid)):
                if all(self.grid[y]):
                    cleared_lines_now += 1
                    self.cleared_lines += 1
                    self.grid.pop(y)
                    self.grid.insert(0, [0 for cell in range(len(self.grid[0]))])
            if cleared_lines_now != 0:
                self.score += [0, 100, 300, 500, 800][cleared_lines_now]
                self.update_labels()
            
            if self.pieces[0].landed:
                for y, rows in enumerate(self.pieces[0].shape):
                    for x, cell in enumerate(rows):
                        if cell:
                            self.grid[self.pieces[0].y + y][self.pieces[0].x + x] = self.pieces[0].color
                            self.score += 1 + self.pieces[0].hard_drop
                self.pieces.pop(0)
                
                if not self.pieces[0].can_place(self.grid, self.pieces[0].shape, 4, 0, 0, 0):
                    self.grid = [[0 for column in range(10)] for row in range(20)]
                    self.cleared_lines = 0
                    self.score = 0
                self.pieces[0].x = 4
                self.pieces[0].y = 0
            
                self.pieces.append(self.create_piece(12, 2))
                
                if self.score > self.high_score:
                    self.high_score = self.score
                self.save()
                self.update_labels()
            
            
    def update_labels(self):
        self.lines_label.update_text(f'Lines\n[ {self.cleared_lines} ]')
        self.score_label.update_text(f'Score\n[ {self.score} ]')
        self.high_score_label.update_text(f'HiScore\n[ {self.high_score} ]')

    def draw(self):
        self.screen.fill("black")
        self.pieces[0].draw(self.cell_size, self.screen, land_y=self.pieces[0].land(self.grid, get=True), alpha=100)
        for piece in self.pieces:
            piece.draw(self.cell_size, self.screen)
        self.draw_grid(self.grid, self.cell_size, self.screen)
        self.ui.draw(self.screen)
        if self.scene == 'paused':
            self.pause_ui.draw(self.screen)
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
                        self.screen,
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
            
    def create_piece(self, x, y, piece=None):
        if not self.bag:
            self.bag = list(PIECES)
            random.shuffle(self.bag)
            
        if piece is None:
            shape, color = self.bag[0]
            self.bag.pop(0)
        return Piece([row[:] for row in shape], color, x, y)
    
    def save(self):
        with open(BASE_DIR / 'GameData/saved.json', "w") as file:
            self.save_data = {
                "high_score": self.high_score,
                "score": self.score,
                "cleared_lines": self.cleared_lines,
                "grid": self.grid,
                "pieces": [piece.to_dict() for piece in self.pieces]
            }
            json.dump(self.save_data, file, indent=4)
        
    def load(self):
        try:
            with open(BASE_DIR / 'GameData/saved.json', "r") as file:
                self.save_data: dict = json.load(file)
                self.high_score = self.save_data.get('high_score', 0)
                self.score = self.save_data.get('score', 0)
                self.cleared_lines = self.save_data.get('cleared_lines', 0)
                self.grid = self.save_data.get('grid', self.grid)
                self.pieces = [Piece(**piece) for piece in self.save_data.get('pieces', [])] or self.pieces
        except (FileNotFoundError, json.JSONDecodeError):
            self.save()
            

    


game = Game()
game.run()

# TODO r to restart