"""Small stdlib-only player for the bundled vector animation."""
from dataclasses import dataclass
import json
import math
from pathlib import Path
import struct
import zipfile

MAX_FRAMES=18000
MAX_BYTES=MAX_FRAMES*(1+72*4)

@dataclass(frozen=True)
class Clip:
    fps: float
    frames: tuple
    source_name: str

    @property
    def duration(self):return len(self.frames)/self.fps

    @classmethod
    def load(cls,path):
        with zipfile.ZipFile(Path(path)) as archive:
            if set(archive.namelist())!={'metadata.json','frames.bin'}:raise ValueError('动画数据结构不正确')
            if archive.getinfo('metadata.json').file_size>8192 or archive.getinfo('frames.bin').file_size>MAX_BYTES:
                raise ValueError('动画数据超过大小限制')
            metadata=json.loads(archive.read('metadata.json'))
            fps=float(metadata['fps']);count=metadata['frame_count']
            if metadata.get('version')!=1 or not math.isfinite(fps) or not 0<fps<=60:
                raise ValueError('动画版本或帧率不正确')
            if type(count) is not int or not 1<=count<=MAX_FRAMES:raise ValueError('动画帧数不正确')
            raw=archive.read('frames.bin')
        frames=[];offset=0
        for _ in range(count):
            if offset>=len(raw):raise ValueError('动画数据不完整')
            size=raw[offset];offset+=1
            if not 1<=size<=72 or offset+size*4>len(raw):raise ValueError('动画线段数据不完整')
            frames.append(raw[offset:offset+size*4]);offset+=size*4
        if offset!=len(raw):raise ValueError('动画末尾包含多余数据')
        return cls(fps,tuple(frames),str(metadata.get('source_name','Bad Apple')))

    def lines_at(self,seconds):
        index=min(len(self.frames)-1,max(0,int(seconds*self.fps)))
        return list(struct.iter_unpack('4B',self.frames[index]))

class Player:
    def __init__(self,clip):
        self.clip=clip;self.position=0.;self.playing=True;self.loop=True
    def seek(self,seconds):
        self.position=max(0.,min(self.clip.duration,float(seconds)))
    def update(self,dt,pressed):
        if pressed&{'r','home'}:self.position=0.;self.playing=True
        if 'left' in pressed:self.seek(self.position-5)
        if 'right' in pressed:self.seek(self.position+5)
        if 'l' in pressed:self.loop=not self.loop
        if 'space' in pressed:
            if self.position>=self.clip.duration:self.position=0.
            self.playing=not self.playing
        if self.playing:
            self.position+=max(0.,dt)
            if self.position>=self.clip.duration:
                if self.loop:self.position%=self.clip.duration
                else:self.position=self.clip.duration;self.playing=False

def stamp(seconds):
    value=max(0,int(seconds));return f'{value//60:02d}:{value%60:02d}'
