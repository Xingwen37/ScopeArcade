from pathlib import Path
from .model import Game as Model

MASKS=[0x3f,0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,0x7f,0x6f]
class Game:
    def __init__(self,context):
        self.model=Model();self.context=context;self.auto=False;self.waiting=0
        self.segments=[int(x,16) for x in (Path(__file__).parent/'segments.hex').read_text().split()]
    def update(self,dt,held,pressed):
        g=self.model
        if 'space' in pressed:g.serve()
        if 'r' in pressed:g.restart()
        if 'a' in pressed:self.auto=not self.auto
        if self.auto and not g.running:
            self.waiting+=dt
            if self.waiting>.8:
                if g.winner:g.restart()
                g.serve();self.waiting=0
        else:self.waiting=0
        score=g.left_score+g.right_score
        direction=int(bool(held&{'w','up'}))-int(bool(held&{'s','down'}))
        g.step(dt,direction,self.auto)
        if g.left_score+g.right_score!=score:self.context.sound('pass')
    def lines(self):
        g=self.model;lines=[]
        for value in self.segments:
            kind=value>>35;bit=(value>>32)&7
            x0,y0,x1,y1=[(value>>shift)&255 for shift in (24,16,8,0)]
            dx=dy=0
            if kind==1:dx=22;dy=round(g.left)-22
            elif kind==2:dx=230;dy=round(g.right)-22
            elif kind==3:dx=round(g.x)-3;dy=round(g.y)-3
            elif kind in (4,5):
                score=g.left_score if kind==4 else g.right_score
                if not MASKS[score]&(1<<bit):continue
                dx=95 if kind==4 else 149;dy=206
            lines.append((x0+dx,y0+dy,x1+dx,y1+dy))
        return lines
    def status(self):
        g=self.model
        return f'你 {g.left_score} : {g.right_score} 电脑　'+(g.winner or ('对打中' if g.running else '空格发球 / 继续'))+('　自动演示' if self.auto else '')

def create_game(context):return Game(context)
