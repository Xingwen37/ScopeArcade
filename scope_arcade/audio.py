import math
from pathlib import Path
import struct
import sys
import wave

class Audio:
    def __init__(self,folder):
        self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True);self.muted=False
        self.player=__import__('winsound') if sys.platform=='win32' else None
        for name,notes in {'count':[(520,.07)],'go':[(1040,.15)],'pass':[(1320,.045)],
                           'crash':[(150,.12)],'finish':[(660,.10),(880,.10),(1100,.14)]}.items():
            path=self.folder/(name+'.wav')
            if path.exists():continue
            samples=[]
            for frequency,duration in notes:
                length=int(22050*duration)
                for i in range(length):
                    envelope=min(1,i/180,(length-i)/180)
                    samples.append(int(4500*envelope*math.sin(2*math.pi*frequency*i/22050)))
            with wave.open(str(path),'wb') as out:
                out.setnchannels(1);out.setsampwidth(2);out.setframerate(22050)
                out.writeframes(struct.pack('<'+'h'*len(samples),*samples))
    def play(self,name):
        if self.player and not self.muted and name in {'count','go','pass','crash','finish'}:
            self.player.PlaySound(str(self.folder/(name+'.wav')),self.player.SND_FILENAME|self.player.SND_ASYNC|self.player.SND_NODEFAULT)
    def close(self):
        if self.player:self.player.PlaySound(None,0)
