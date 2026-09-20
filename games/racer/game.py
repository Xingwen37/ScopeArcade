import json
import math
import time
from .model import Game as Model
from .drawing import scene

class Game:
    def __init__(self,context):
        self.context=context;self.model=Model(time.time_ns());self.path=context.data_dir/'leaderboard.json'
        self.board=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else []
    def update(self,dt,held,pressed):
        if ('space' in pressed and self.model.mode in ('attract','result')) or 'r' in pressed:self.model.start()
        if 'p' in pressed:self.model.pause()
        direction=int(bool(held&{'d','right'}))-int(bool(held&{'a','left'}))
        self.model.step(dt,direction)
        if self.model.events:self.context.sound(self.model.events[-1]);self.model.events.clear()
        if self.model.round_finished:
            self.board.append({'name':self.context.player_name,'score':self.model.score,'distance':round(self.model.distance,1)})
            self.board.sort(key=lambda row:(-row['score'],-row['distance']));self.board=self.board[:10]
            temporary=self.path.with_suffix('.tmp');temporary.write_text(json.dumps(self.board,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(self.path)
            self.model.round_finished=False
    def lines(self):return scene(self.model)
    def status(self):
        g=self.model;mode={'attract':'自动演示，空格开始','countdown':f'准备：{max(1,math.ceil(g.countdown))}',
                         'playing':'超越前车','paused':'已暂停，P继续','result':'挑战结束，空格再来一局'}[g.mode]
        best=' / '.join(f'{row["name"]}: {row["score"]}' for row in self.board[:3]) or '等待第一位挑战者'
        return f'{mode}　分数 {g.score:02d}　剩余 {math.ceil(g.remaining):02d}s　{g.speed*3.6:.0f}km/h\n排行榜：{best}'

def create_game(context):return Game(context)
