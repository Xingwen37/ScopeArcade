"""Deterministic Pong physics in a 256-unit square court."""
from dataclasses import dataclass
import math


@dataclass
class Game:
    left: float = 128
    right: float = 128
    x: float = 128
    y: float = 128
    vx: float = 90
    vy: float = 30
    left_score: int = 0
    right_score: int = 0
    running: bool = False
    winner: str = ''
    serve_direction: int = 1

    def serve(self):
        if self.winner:
            return
        self.running = not self.running

    def restart(self):
        self.__dict__.update(Game().__dict__)

    def point(self, left_won):
        if left_won:self.left_score += 1
        else:self.right_score += 1
        if self.left_score >= 9:self.winner='你获胜'
        if self.right_score >= 9:self.winner='电脑获胜'
        self.x=self.y=128
        self.serve_direction *= -1
        self.vx=90*self.serve_direction
        self.vy=30 if (self.left_score+self.right_score)%2 else -30
        self.running=False

    def bounce(self, center, direction):
        angle=max(-1,min(1,(self.y-center)/25))*math.radians(55)
        speed=min(175,math.hypot(self.vx,self.vy)*1.045)
        self.vx=direction*max(55,speed*math.cos(angle))
        self.vy=speed*math.sin(angle)

    def step(self, dt, direction=0, auto=False):
        if auto:
            self.left += max(-150*dt,min(150*dt,self.y-self.left))
        else:self.left += direction*160*dt
        self.left=max(48,min(208,self.left))
        # A speed-limited opponent with a dead zone can be beaten.
        target=self.y if self.vx>0 else 128
        if abs(target-self.right)>5:
            self.right += max(-72*dt,min(72*dt,target-self.right))
        self.right=max(48,min(208,self.right))
        if not self.running or self.winner:return
        old_x=self.x
        self.x+=self.vx*dt;self.y+=self.vy*dt
        if self.y<27:self.y=54-self.y;self.vy=abs(self.vy)
        if self.y>229:self.y=458-self.y;self.vy=-abs(self.vy)
        if self.vx<0 and old_x>=29 and self.x<=29 and abs(self.y-self.left)<=25:
            self.x=58-self.x;self.bounce(self.left,1)
        elif self.vx>0 and old_x<=227 and self.x>=227 and abs(self.y-self.right)<=25:
            self.x=454-self.x;self.bounce(self.right,-1)
        if self.x<12:self.point(False)
        elif self.x>244:self.point(True)


def packet(seq, game):
    data=[0xA5,seq&255,round(game.left),round(game.right),
          max(12,min(244,round(game.x))),max(27,min(229,round(game.y))),
          (game.left_score<<4)|game.right_score]
    check=0
    for value in data:check^=value
    return bytes(data+[check])
