import json
import os
from pathlib import Path

def default_data_dir():
    return Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))/'ScopeArcade'

def save_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)

def load_json(path,default):
    path=Path(path)
    if not path.exists():return default
    return json.loads(path.read_text(encoding='utf-8'))
