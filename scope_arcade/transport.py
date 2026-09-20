"""Single serial owner, latest-frame scheduling, finite-time handshake."""
import threading
import time
import serial
from serial.tools import list_ports
from .protocol import BAUD,packet,validate_lines

def ports():
    return [(p.device,f'{p.device} — {p.description}') for p in list_ports.comports()]

class SerialTransport:
    def __init__(self,link):
        self.link=link;self._frame=None;self._stream_started=None;self._lock=threading.Lock();self._stop=threading.Event()
        self.sent=0;self.acks=0;self.error='';self.last_ack=time.monotonic();self.skips=0
        self.thread=threading.Thread(target=self._run,daemon=True,name='ScopeArcade-serial')

    @classmethod
    def open(cls,port):
        link=serial.Serial(port,BAUD,timeout=.05,write_timeout=.05)
        try:
            link.reset_input_buffer()
            for sequence in (173,46):
                link.write(packet(sequence,[(128,128,128,128)]));deadline=time.monotonic()+1.2
                while time.monotonic()<deadline:
                    response=link.read(1)
                    if not response:continue
                    if response!=bytes([sequence]):raise RuntimeError('串口响应不是通用绘图器的帧确认，请检查所选接口和固件。')
                    break
                else:raise RuntimeError('FPGA 未确认通用绘图帧。请检查启动模式、串口和固件（C48F / 1 Mbaud），不要选旧版游戏专用固件。')
            link.timeout=0
            result=cls(link);result.thread.start();return result
        except BaseException:link.close();raise

    def frame(self,lines):
        frame=validate_lines(lines) if lines is not None else None
        with self._lock:
            if frame is not None and self._frame is None:self._stream_started=time.monotonic()
            if frame is None:self._stream_started=None
            self._frame=frame

    def snapshot(self):
        with self._lock:started=self._stream_started
        return {'sent':self.sent,'acks':self.acks,'skips':self.skips,'error':self.error,
                'ack_age':time.monotonic()-self.last_ack,'stream_age':time.monotonic()-started if started else 0,'port':self.link.port}

    def _run(self):
        pending={};sequence=0;deadline=time.monotonic()
        while not self._stop.is_set():
            try:
                now=time.monotonic()
                for ack in self.link.read(self.link.in_waiting):
                    if ack in pending:del pending[ack];self.acks+=1;self.last_ack=now
                pending={s:t for s,t in pending.items() if now-t<2}
                with self._lock:frame=self._frame
                if frame is not None:
                    if self.link.out_waiting<400:
                        self.link.write(packet(sequence,frame));pending[sequence]=now
                        sequence=(sequence+1)&255;self.sent+=1
                    else:self.skips+=1
            except (serial.SerialException,OSError) as exc:
                self.error=str(exc);break
            deadline+=1/60
            if deadline<time.monotonic():deadline=time.monotonic()+1/60
            self._stop.wait(max(0,deadline-time.monotonic()))

    def close(self):
        self._stop.set();self.thread.join(timeout=1);self.link.close()
