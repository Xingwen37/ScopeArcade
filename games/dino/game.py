import json
from pathlib import Path
from .model import Game as Model

class Game:
    def __init__(self,context):
        self.model=Model();self.context=context;self.auto=False
        self.art=json.loads((Path(__file__).parent/'artwork.json').read_text())
    def update(self,dt,held,pressed):
        g=self.model
        if pressed&{'space','up'}:g.jump()
        if 'r' in pressed:g.restart()
        if 'a' in pressed:self.auto=not self.auto;g.running=self.auto or g.running
        if self.auto:
            if g.dead:g.restart();g.running=True
            if 76<g.obstacle<94 and g.height==0:g.jump()
        dead=g.dead;score=g.score;g.step(dt)
        if g.dead and not dead:self.context.sound('crash')
        elif g.score!=score:self.context.sound('pass')
    def lines(self):
        g=self.model;lines=[(x,40,min(x+30,247),40) for x in range(8,247,30)]
        for name,dx,dy in [('dino',48,42+round(g.height)),('cactus',round(g.obstacle),40)]:
            points=self.art[name]
            for a,b in zip(points,points[1:]):lines.append((a[0]+dx,a[1]+dy,b[0]+dx,b[1]+dy))
        return lines
    def status(self):
        g=self.model
        return f'分数 {g.score}　'+('碰撞！空格重新开始' if g.dead else ('跳过仙人掌' if g.running else '空格开始'))+('　自动演示' if self.auto else '')

def create_game(context):return Game(context)
