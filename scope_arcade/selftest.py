"""Packaged offline smoke test. Never opens serial or VISA devices."""
import json
from pathlib import Path
import tempfile
from .api import GameContext
from .app import Application,assets_root
from .plugins import discover,instantiate,install
from .protocol import validate_lines
from .storage import save_json

def run(data_dir):
    root=Path(data_dir).resolve();root.mkdir(parents=True,exist_ok=True);report={'hardware_accessed':False,'passed':False}
    try:
        with tempfile.TemporaryDirectory(prefix='offline-',dir=root) as folder:
            folder=Path(folder).resolve();assert folder.is_relative_to(root)
            app=Application(folder);app.root.withdraw();app.audio.muted=True
            try:
                report['games']=[]
                for info in app.games:
                    data=folder/'game-data'/info.id;data.mkdir(parents=True,exist_ok=True)
                    game=instantiate(info,GameContext(data,'自检',lambda _:None))
                    for i in range(200):game.update(1/120,set(),{'space'} if i==0 else set())
                    report['games'].append({'id':info.id,'lines':len(validate_lines(game.lines()))})
                    if info.id=='bad-apple':
                        # Exercise real animation frames and controls from the frozen bundle.
                        samples=[]
                        for _ in range(36):
                            game.update(0,set(),{'right'})
                            samples.append(tuple(validate_lines(game.lines())))
                        assert len(set(samples))>10
                        game.update(0,set(),{'home'})
                        game.update(.5,set(),set())
                        before=game.status();game.update(0,set(),{'space'})
                        assert game.status()!=before
                        report['animation_samples']=len(samples)
                imported=install(assets_root()/'game-template',folder/'games',{g.id for g in app.games})
                test=instantiate(imported,GameContext(folder,'自检',lambda _:None));test.update(.1,{'right'},set());validate_lines(test.lines())
                app.play();app.root.update_idletasks();app.tick();assert app.running
                app.stop();assert not app.running
                report['imported_game']=imported.id;report['passed']=True
            finally:app.close()
    except Exception as exc:report['error']=repr(exc)
    save_json(root/'selftest-result.json',report)
    return report['passed']
