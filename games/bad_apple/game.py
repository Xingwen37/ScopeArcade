from pathlib import Path
from .player import Clip,Player,stamp

class Game:
    def __init__(self,context):
        # Resolve data from this game package, never from the source computer's video path.
        self.player=Player(Clip.load(Path(__file__).with_name('animation.xyframes')))
    def update(self,dt,held,pressed):self.player.update(dt,pressed)
    def lines(self):return self.player.clip.lines_at(self.player.position)
    def status(self):
        p=self.player
        return f'Bad Apple　{stamp(p.position)} / {stamp(p.clip.duration)}　'+('播放中' if p.playing else '已暂停')+f'　{p.clip.fps:g} fps轮廓版　循环'+('开' if p.loop else '关')+'　无音轨'

def create_game(context):return Game(context)
