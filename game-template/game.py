class Game:
    def __init__(self,context):self.x=self.y=128
    def update(self,dt,held,pressed):
        if 'r' in pressed:self.x=self.y=128
        self.x=max(25,min(230,self.x+80*dt*(int('right' in held)-int('left' in held))))
        self.y=max(25,min(230,self.y+80*dt*(int('up' in held)-int('down' in held))))
    def lines(self):
        x,y=round(self.x),round(self.y)
        return [(x-10,y-10,x+10,y-10),(x+10,y-10,x+10,y+10),
                (x+10,y+10,x-10,y+10),(x-10,y+10,x-10,y-10)]
    def status(self):return '方向键移动你的方块'

def create_game(context):return Game(context)
