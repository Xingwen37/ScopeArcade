"""Small deterministic runner model shared by the controller and tests."""
from dataclasses import dataclass


@dataclass
class Game:
    height: float = 0
    velocity: float = 0
    obstacle: float = 230
    score: int = 0
    running: bool = False
    dead: bool = False
    passed: bool = False

    def jump(self):
        if self.dead:
            self.restart()
        self.running = True
        if self.height == 0:
            self.velocity = 230

    def restart(self):
        self.__dict__.update(Game().__dict__)

    def step(self, dt):
        if not self.running or self.dead:
            return
        self.height += self.velocity * dt
        self.velocity -= 430 * dt
        if self.height <= 0:
            self.height = self.velocity = 0
        self.obstacle -= (62 + min(self.score, 20) * 1.6) * dt
        # Dinosaur at x=48..72, cactus at obstacle..obstacle+13.
        if self.obstacle < 70 and self.obstacle + 13 > 51 and self.height < 27:
            self.dead = True
            self.running = False
        if self.obstacle + 13 < 48 and not self.passed:
            self.score += 1
            self.passed = True
        if self.obstacle < 3:
            self.obstacle = 230
            self.passed = False


def packet(sequence, height, obstacle, flags=0):
    values = [0xA5, sequence & 255, min(100, max(0, int(height))),
              min(235, max(0, int(obstacle))), flags & 3]
    checksum = 0
    for value in values:
        checksum ^= value
    return bytes(values + [checksum])
