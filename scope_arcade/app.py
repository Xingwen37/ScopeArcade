import argparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import ctypes
import json
import math
from pathlib import Path
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
import traceback
from . import __version__
from .api import GameContext
from .audio import Audio
from .instruments import Instruments
from .plugins import discover,instantiate,install
from .protocol import validate_lines
from .storage import default_data_dir,save_json,load_json
from .transport import SerialTransport,ports

def assets_root():return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))

class Application:
    def __init__(self,data_dir=None):
        self.data_dir=Path(data_dir or default_data_dir());self.data_dir.mkdir(parents=True,exist_ok=True)
        self.settings=load_json(self.data_dir/'settings.json',{})
        self.root=tk.Tk();self.root.title(f'ScopeArcade {__version__} · 示波器游戏中心');self.root.geometry('1160x840');self.root.minsize(960,680)
        self.root.configure(bg='#0b1914');self.style=ttk.Style(self.root);self.style.theme_use('clam')
        self.style.configure('TFrame',background='#0b1914');self.style.configure('TLabel',background='#0b1914',foreground='#d9e8df',font=('Microsoft YaHei UI',10))
        self.style.configure('TButton',padding=(10,7),font=('Microsoft YaHei UI',10))
        self.style.configure('Compact.TButton',padding=(7,3),font=('Microsoft YaHei UI',10))
        self.style.configure('TLabelframe',background='#0b1914');self.style.configure('TLabelframe.Label',background='#0b1914',foreground='#9bffd0')
        self.style.configure('TCheckbutton',background='#0b1914',foreground='#d9e8df')
        self.executor=ThreadPoolExecutor(max_workers=1);self.job=None;self.cancel=threading.Event();self.closing=False
        self.instruments=Instruments();self.transport=None;self.managed_generator='';self.game=None;self.info=None;self.running=False
        self.keys=set();self.pressed=set();self.lines=[];self.game_errors=[];self.frames=0;self.rate=deque(maxlen=121)
        self.audio=Audio(self.data_dir/'sounds');self.audio.muted=self.settings.get('muted',False)
        self.winmm=ctypes.WinDLL('winmm') if sys.platform=='win32' else None
        self.timer_enabled=bool(self.winmm and self.winmm.timeBeginPeriod(1)==0)
        self.serial_var=tk.StringVar(value=self.settings.get('port',''))
        self.scope_var=tk.StringVar(value=self.settings.get('scope',''));self.gen_var=tk.StringVar(value=self.settings.get('generator',''))
        self.name_var=tk.StringVar(value=self.settings.get('player_name','玩家'))
        self.mute_var=tk.BooleanVar(value=self.audio.muted)
        self.status_var=tk.StringVar(value='先选择游戏。没有硬件也可以使用电脑预览。')
        self._layout();self.reload_games();self.refresh_ports()
        self.root.bind('<KeyPress>',self.key_down);self.root.bind('<KeyRelease>',lambda e:self.keys.discard(e.keysym.lower()))
        self.root.bind('<FocusOut>',lambda e:(self.keys.clear(),self.pressed.clear()));self.root.protocol('WM_DELETE_WINDOW',self.close)
        self.last=time.monotonic();self.deadline=self.last;self.accumulator=0;self.last_report=0
        self.root.after(1,self.tick)

    def _layout(self):
        header=ttk.Frame(self.root);header.pack(fill='x',padx=18,pady=(14,8))
        ttk.Label(header,text='SCOPE / ARCADE',font=('Segoe UI',23,'bold'),foreground='#9bffd0').pack(side='left')
        ttk.Button(header,text='使用说明',command=self.help,style='Compact.TButton').pack(side='right',padx=(12,0))
        ttk.Label(header,text='一套绘图器 · 多个游戏 · 即时切换').pack(side='right')
        devices=ttk.LabelFrame(self.root,text='设备连接');devices.pack(fill='x',padx=18,pady=5)
        for row,label,var in [(0,'FPGA 串口',self.serial_var),(1,'示波器 DHO4404',self.scope_var),(2,'发生器 SDG1032X',self.gen_var)]:
            ttk.Label(devices,text=label).grid(row=row,column=0,sticky='w',padx=10,pady=4)
            box=ttk.Combobox(devices,textvariable=var,width=64);box.grid(row=row,column=1,sticky='ew',padx=6,pady=4)
            if row==0:self.port_box=box
            elif row==1:self.scope_box=box
            else:self.gen_box=box
        devices.columnconfigure(1,weight=1)
        self.scan_button=ttk.Button(devices,text='扫描设备',command=self.scan);self.scan_button.grid(row=0,column=2,padx=8)
        self.connect_button=ttk.Button(devices,text='配置仪器并连接',command=self.connect);self.connect_button.grid(row=1,column=2,padx=8)
        self.off_button=ttk.Button(devices,text='断开并关闭输出',command=self.disconnect);self.off_button.grid(row=2,column=2,padx=8)
        body=ttk.Frame(self.root);body.pack(fill='both',expand=True,padx=18,pady=10)
        side_shell=ttk.Frame(body,width=285);side_shell.pack(side='left',fill='y',padx=(0,12));side_shell.pack_propagate(False)
        scroll=tk.Canvas(side_shell,bg='#0b1914',highlightthickness=0,width=267)
        bar=ttk.Scrollbar(side_shell,orient='vertical',command=scroll.yview);bar.pack(side='right',fill='y');scroll.pack(side='left',fill='both',expand=True)
        scroll.configure(yscrollcommand=bar.set)
        sidebar=ttk.Frame(scroll,width=263);scroll.create_window((0,0),window=sidebar,anchor='nw',width=263)
        sidebar.bind('<Configure>',lambda event:scroll.configure(scrollregion=scroll.bbox('all')))
        library_header=ttk.Frame(sidebar);library_header.pack(fill='x',pady=5)
        ttk.Label(library_header,text='游戏库',font=('Microsoft YaHei UI',14,'bold')).pack(side='left')
        ttk.Button(library_header,text='添加游戏…',command=self.add_game,style='Compact.TButton').pack(side='right')
        self.library=tk.Listbox(sidebar,height=4,bg='#12291e',fg='#ddf7e8',selectbackground='#286e4b',font=('Microsoft YaHei UI',11),exportselection=False)
        self.library.pack(fill='x');self.library.bind('<<ListboxSelect>>',self.select_game)
        self.description=ttk.Label(sidebar,text='',wraplength=250);self.description.pack(fill='x',pady=6)
        self.controls=ttk.Label(sidebar,text='',wraplength=258,foreground='#9bffd0');self.controls.pack(fill='x',pady=5)
        ttk.Label(sidebar,text='玩家昵称').pack(anchor='w',pady=(10,2));ttk.Entry(sidebar,textvariable=self.name_var).pack(fill='x')
        ttk.Button(sidebar,text='启动 / 重开',command=self.play,style='Compact.TButton').pack(fill='x',pady=(8,3))
        ttk.Button(sidebar,text='停止游戏',command=self.stop,style='Compact.TButton').pack(fill='x',pady=3)
        ttk.Button(sidebar,text='仅电脑预览',command=self.preview,style='Compact.TButton').pack(fill='x',pady=3)
        ttk.Checkbutton(sidebar,text='静音',variable=self.mute_var,command=self.mute).pack(anchor='w',pady=6)
        ttk.Label(sidebar,text='游戏包包含可执行 Python 代码，\n仅导入你信任的来源。',wraplength=260).pack(anchor='w',pady=4)
        right=ttk.Frame(body);right.pack(side='left',fill='both',expand=True)
        self.canvas=tk.Canvas(right,bg='#030d08',highlightthickness=0,takefocus=True);self.canvas.pack(fill='both',expand=True)
        self.items=[self.canvas.create_line(0,0,0,0,fill='#a9ffd0',width=2,state='hidden') for _ in range(72)]
        self.game_status=ttk.Label(right,text='选择一个游戏并点击“启动 / 重开”',wraplength=720);self.game_status.pack(fill='x',pady=8)
        self.telemetry=ttk.Label(self.root,text='电脑预览 · 未连接硬件');self.telemetry.pack(fill='x',padx=18)
        ttk.Label(self.root,textvariable=self.status_var,wraplength=1100).pack(fill='x',padx=18,pady=(4,12))

    def refresh_ports(self):
        available=ports();self.port_box['values']=[p[0] for p in available]
        # Do not pick the debugger's wrong interface automatically.

    def reload_games(self):
        self.games,self.game_errors=discover(assets_root()/'games',self.data_dir/'games')
        self.library.delete(0,'end')
        for game in self.games:self.library.insert('end',game.name)
        index=next((i for i,g in enumerate(self.games) if g.id==self.settings.get('game','racer')),0)
        if self.games:self.library.selection_set(index);self.select_game()
        if self.game_errors:self.status_var.set('；'.join(self.game_errors))

    def select_game(self,event=None):
        selected=self.library.curselection()
        if not selected:return
        if self.info and self.info.id==self.games[selected[0]].id:return
        was_running=self.running;self.stop();self.info=self.games[selected[0]]
        self.description.config(text=self.info.description);self.controls.config(text=self.info.controls)
        self.settings['game']=self.info.id
        if was_running:self.play()

    def play(self):
        if not self.info:return
        try:
            folder=self.data_dir/'game-data'/self.info.id;folder.mkdir(parents=True,exist_ok=True)
            context=GameContext(folder,self.name_var.get().strip()[:16] or '玩家',self.audio.play)
            self.game=instantiate(self.info,context);self.lines=validate_lines(self.game.lines());self.running=True
            self.accumulator=0;self.keys.clear();self.pressed.clear();self.canvas.focus_set()
            self.status_var.set('已启动：'+self.info.name+(' · 示波器输出' if self.transport else ' · 电脑预览'))
        except Exception as exc:self.fail_game(exc)

    def stop(self):
        self.running=False;self.keys.clear();self.pressed.clear();self.lines=[]
        if self.transport:self.transport.frame(None)
        if not self.closing:self.status_var.set('游戏已停止；硬件画面将在约1秒内消隐。')

    def preview(self):
        if self.transport:self.status_var.set('请先断开硬件，再进入仅电脑预览。');return
        self.play()

    def mute(self):self.audio.muted=self.mute_var.get()

    def key_down(self,event):
        if event.widget.winfo_class() in ('TEntry','TCombobox','Entry'):return
        key=event.keysym.lower()
        if key not in self.keys:self.pressed.add(key)
        self.keys.add(key)
        if key=='escape':self.stop()

    def job_run(self,work,complete):
        if self.job:self.status_var.set('请等待当前设备操作完成。');return
        self.scan_button.state(['disabled']);self.connect_button.state(['disabled'])
        self.job=self.executor.submit(work)
        def poll():
            if not self.job.done():self.root.after(30,poll);return
            future=self.job;self.job=None
            self.scan_button.state(['!disabled']);self.connect_button.state(['!disabled'])
            try:complete(future.result())
            except Exception as exc:
                self.status_var.set(str(exc));self.log_error(exc)
            if self.closing:self.root.after(1,self._finish_close)
        self.root.after(30,poll)

    def scan(self):
        self.refresh_ports();self.status_var.set('正在只读扫描 USB / 网络仪器…')
        def done(resources):
            self.scope_box['values']=[r['resource'] for r in resources if ',DHO4404,' in r['identity']]
            self.gen_box['values']=[r['resource'] for r in resources if ',SDG1032X,' in r['identity']]
            for var,model in [(self.scope_var,'DHO4404'),(self.gen_var,'SDG1032X')]:
                matches=[r['resource'] for r in resources if f',{model},' in r['identity']]
                if len(matches)==1:var.set(matches[0])
            self.status_var.set('扫描完成。选择 FPGA 的 UART 串口；仪器地址也可以手动填写。')
            self.save_settings()
        self.job_run(self.instruments.discover,done)

    def connect(self):
        if self.transport:self.status_var.set('已经连接；可直接切换游戏。要更换设备，请先断开。');return
        port=self.serial_var.get().strip();scope=self.scope_var.get().strip();generator=self.gen_var.get().strip()
        if not all((port,scope,generator)):self.status_var.set('请先选择串口、示波器和发生器。');return
        self.status_var.set('配置仪器（输出先关闭）→ 检查 FPGA → 开启同步消隐…')
        def work():
            transport=None
            try:
                report=self.instruments.configure(scope,generator,self.cancel)
                transport=SerialTransport.open(port)
                self.instruments.enable(scope,generator,self.cancel)
                return transport,report
            except BaseException:
                if transport:transport.close()
                try:self.instruments.off(generator)
                except Exception:pass
                raise
        def done(result):
            self.transport,report=result;self.managed_generator=generator
            save_json(self.data_dir/'last-connection.json',report);self.save_settings()
            if self.closing:return
            self.status_var.set('仪器配置及 FPGA 通信通过。已开启同步消隐，可直接切换游戏。')
            if not self.running:self.play()
        self.job_run(work,done)

    def disconnect(self):
        if self.job:self.status_var.set('当前设备操作尚未结束，请稍候再断开。');return
        self.stop()
        if self.transport:self.transport.close();self.transport=None
        generator=self.managed_generator;self.managed_generator=''
        if generator:self.job_run(lambda:self.instruments.off(generator),lambda _:self.status_var.set('已断开串口并关闭发生器输出。'))
        else:self.status_var.set('已停止，当前没有受控硬件连接。')

    def add_game(self):
        file=filedialog.askopenfilename(title='选择信任的游戏包 game.json',filetypes=[('游戏描述','game.json')])
        if not file:return
        try:
            info=install(Path(file).parent,self.data_dir/'games',{g.id for g in self.games})
            self.reload_games();index=next(i for i,g in enumerate(self.games) if g.id==info.id)
            self.library.selection_clear(0,'end');self.library.selection_set(index);self.select_game()
            self.status_var.set('已添加 '+info.name+'；点击启动即可运行。')
        except Exception as exc:messagebox.showerror('无法添加游戏',str(exc))

    def help(self):
        messagebox.showinfo('连接说明',
            '1. FPGA 使用已固化的通用矢量绘图器（C48F，1 Mbaud），切换游戏不刷固件。\n'
            '2. AD9767 CH1/CH2 → 示波器 CH1/CH2。\n'
            '3. FPGA E14 → SDG AUX 输入；发生器 CH1 → 示波器 CH3。保持公共地。\n'
            '4. 扫描设备，选择 UART 串口，点击“配置仪器并连接”。\n\n'
            'Windows USB 使用需要 FTDI 串口驱动及 NI-VISA / 兼容 VISA 运行库。\n'
            '本应用不含 FPGA/Flash 烧录功能。游戏包 API 和固件源码见随附 docs。\n\n'
            f'设置、排行榜和自定义游戏保存在：\n{self.data_dir}')

    def save_settings(self):
        self.settings.update(port=self.serial_var.get(),scope=self.scope_var.get(),generator=self.gen_var.get(),
                             player_name=self.name_var.get(),muted=self.mute_var.get())
        save_json(self.data_dir/'settings.json',self.settings)

    def log_error(self,exc):
        with (self.data_dir/'errors.log').open('a',encoding='utf-8') as out:
            out.write(time.strftime('%Y-%m-%d %H:%M:%S')+' '+repr(exc)+'\n'+traceback.format_exc()+'\n')

    def fail_game(self,exc):
        self.stop();self.status_var.set('游戏已停止：'+str(exc));self.log_error(exc)

    def tick(self):
        if self.closing:return
        now=time.monotonic();self.rate.append(now);self.accumulator+=min(.1,now-self.last);self.last=now
        if self.running and self.game:
            try:
                while self.accumulator>=1/120:
                    self.game.update(1/120,set(self.keys),set(self.pressed));self.pressed.clear();self.accumulator-=1/120
                self.lines=validate_lines(self.game.lines());self.game_status.config(text=self.game.status());self.frames+=1
                if self.transport:self.transport.frame(self.lines)
            except Exception as exc:self.fail_game(exc)
        else:self.accumulator=0;self.pressed.clear()
        width=max(1,self.canvas.winfo_width());height=max(1,self.canvas.winfo_height());scale=min(width,height)/256
        ox=(width-256*scale)/2;oy=(height-256*scale)/2
        for i,item in enumerate(self.items):
            if i<len(self.lines):
                x0,y0,x1,y1=self.lines[i];self.canvas.coords(item,x0*scale+ox,(256-y0)*scale+oy,x1*scale+ox,(256-y1)*scale+oy);self.canvas.itemconfigure(item,state='normal')
            else:self.canvas.itemconfigure(item,state='hidden')
        hz=(len(self.rate)-1)/(now-self.rate[0]) if len(self.rate)>1 else 0
        stats=self.transport.snapshot() if self.transport else None
        if stats and (stats['error'] or (self.running and stats['stream_age']>1.5 and stats['ack_age']>1.5)):
            self.stop();self.status_var.set('FPGA 通信中断，已停止发送。请断开后重新连接。 '+stats['error'])
        self.telemetry.config(text=f'{"硬件连接" if stats else "电脑预览"} · {hz:.0f} 次/秒 · {len(self.lines)}/72 线段'+(f' · 确认 {stats["acks"]}/{stats["sent"]}' if stats else ''))
        if now-self.last_report>.5:
            save_json(self.data_dir/'runtime.json',{'time':time.time(),'game':self.info.id if self.info else None,
                'running':self.running,'update_hz':hz,'lines':len(self.lines),'transport':stats})
            self.last_report=now
        finished=time.monotonic();self.deadline+=1/60
        if self.deadline<=finished:self.deadline=finished+1/60
        self.root.after(max(1,math.ceil((self.deadline-finished)*1000)),self.tick)

    def close(self):
        if self.closing:return
        self.closing=True;self.cancel.set();self.stop();self.save_settings()
        self.status_var.set('正在关闭连接和发生器输出…')
        if not self.job:self._finish_close()

    def _finish_close(self):
        if self.transport:self.transport.close();self.transport=None
        generator=self.managed_generator;self.managed_generator=''
        if generator:
            self.job_run(lambda:self.instruments.off(generator),lambda _:None)
            return
        self.audio.close()
        if self.timer_enabled:self.winmm.timeEndPeriod(1);self.timer_enabled=False
        self.executor.shutdown(wait=False,cancel_futures=True);self.root.destroy()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data-dir',type=Path);parser.add_argument('--self-test',action='store_true');args=parser.parse_args()
    if args.self_test:
        from .selftest import run
        raise SystemExit(0 if run(args.data_dir or default_data_dir()/'self-test') else 1)
    Application(args.data_dir).root.mainloop()
