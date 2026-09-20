"""Original60-second arcade road racer. Units: metres and seconds."""
from dataclasses import dataclass
import math
import random

@dataclass
class Car:
    x: float
    z: float
    speed: float
    hit: bool=False
    passed: bool=False

class Game:
    def __init__(self,seed=1):
        self.rng=random.Random(seed);self.mode='attract';self.player=0.;self.speed=20.
        self.distance=0.;self.elapsed=0.;self.score=0;self.combo=0;self.collisions=0
        self.countdown=3.;self.result_time=0.;self.invulnerable=0.;self.flash=0.
        self.spawn_clock=0.;self.cars=[];self.events=[];self.round_finished=False
        self.populate()

    def populate(self):
        self.cars=[Car(-2.3,30,11),Car(2.3,55,13),Car(0,80,12)]

    def start(self):
        self.mode='countdown';self.player=0.;self.speed=0.;self.distance=0.;self.elapsed=0.
        self.score=self.combo=self.collisions=0;self.countdown=3.;self.result_time=0.
        self.invulnerable=self.flash=0.;self.spawn_clock=0.;self.round_finished=False
        self.populate();self.events=['count']

    @property
    def remaining(self):return max(0,60-self.elapsed)

    def pause(self):
        if self.mode=='playing':self.mode='paused'
        elif self.mode=='paused':self.mode='playing'

    def autopilot(self):
        threat=[c for c in self.cars if 0<c.z<24 and not c.hit]
        candidates=(-2.3,0,2.3)
        target=max(candidates,key=lambda lane:min([abs(lane-c.x) for c in threat]+[5])-.05*abs(lane-self.player))
        return max(-1,min(1,(target-self.player)*1.7))

    def step(self,dt,steer=0):
        if self.mode=='paused':return
        if self.mode=='result':
            self.result_time+=dt
            if self.result_time>12:
                self.mode='attract';self.score=self.combo=0;self.elapsed=0.;self.speed=22.;self.populate()
            return
        if self.mode=='countdown':
            previous=math.ceil(self.countdown);self.countdown-=dt
            if math.ceil(self.countdown)<previous and self.countdown>0:self.events.append('count')
            if self.countdown<=0:self.mode='playing';self.events.append('go')
            return
        demo=self.mode=='attract'
        if demo:steer=self.autopilot()
        self.player=max(-4.8,min(4.8,self.player+steer*3.6*dt))
        target=22 if demo else 18+14*min(1,self.elapsed/60)
        if abs(self.player)>3.65:target=8
        self.speed+=max(-14*dt,min(5*dt,target-self.speed))
        self.distance+=self.speed*dt
        self.invulnerable=max(0,self.invulnerable-dt);self.flash=max(0,self.flash-dt)
        for car in self.cars:
            previous=car.z;car.z+=(car.speed-self.speed)*dt
            if previous>1 and car.z<=3 and car.z>=-2 and abs(self.player-car.x)<1.15 and not car.hit:
                if not demo and self.invulnerable==0:
                    car.hit=True;self.speed*=.45;self.combo=0;self.collisions+=1
                    self.invulnerable=1.2;self.flash=.18;self.events.append('crash')
            if car.z<-3 and not car.passed:
                car.passed=True
                if not car.hit and not demo:
                    self.combo+=1;self.score=min(99,self.score+1+int(self.combo%3==0));self.events.append('pass')
        self.cars=[c for c in self.cars if -8<c.z<130]
        self.spawn_clock+=dt
        if self.spawn_clock>=2.8 and len(self.cars)<6:
            self.spawn_clock=0
            lane=self.rng.choice((-2.3,0,2.3))
            self.cars.append(Car(lane,85+self.rng.uniform(0,12),self.rng.uniform(9,13)))
        if not demo:
            self.elapsed=min(60,self.elapsed+dt)
            if self.elapsed>=60:
                self.mode='result';self.result_time=0;self.round_finished=True;self.events.append('finish')

    def snapshot(self):
        return {'mode':self.mode,'player':self.player,'speed':self.speed,'elapsed':self.elapsed,
                'score':self.score,'collisions':self.collisions,'distance':self.distance}
