"""Trusted local Python game packages; metadata discovery never imports code."""
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys

@dataclass(frozen=True)
class GameInfo:
    id: str
    name: str
    description: str
    controls: str
    directory: Path
    entry: str
    builtin: bool=False

def read_game(directory,builtin=False):
    directory=Path(directory).resolve()
    d=json.loads((directory/'game.json').read_text(encoding='utf-8'))
    if d.get('api_version')!=1:raise ValueError('仅支持 game API 1')
    identifier=d.get('id','')
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,47}',identifier):raise ValueError('游戏 id 格式无效')
    entry=d.get('entry','game.py');target=(directory/entry).resolve()
    if target.parent!=directory or target.suffix!='.py' or not target.is_file():
        raise ValueError('入口必须是游戏目录内的 Python 文件')
    name=d.get('name','')
    if not isinstance(name,str) or not name.strip():raise ValueError('缺少游戏名称')
    return GameInfo(identifier,name,str(d.get('description','')),str(d.get('controls','')),directory,entry,builtin)

def discover(builtin_root,user_root):
    games=[];errors=[];seen=set()
    for root,builtin in [(Path(builtin_root),True),(Path(user_root),False)]:
        if not root.exists():continue
        for folder in sorted(root.iterdir()):
            if not (folder/'game.json').is_file():continue
            try:
                game=read_game(folder,builtin)
                if game.id in seen:raise ValueError('重复游戏 id')
                seen.add(game.id);games.append(game)
            except (ValueError,OSError,TypeError) as exc:errors.append(f'{folder.name}: {exc}')
    return games,errors

def instantiate(info,context):
    name='scope_game_'+info.id+'_'+hashlib.sha256(str(info.directory).encode()).hexdigest()[:10]
    # A unique package namespace permits relative helper imports without game.py collisions.
    for key in list(sys.modules):
        if key==name or key.startswith(name+'.'):del sys.modules[key]
    spec=importlib.util.spec_from_file_location(name,info.directory/info.entry,submodule_search_locations=[str(info.directory)])
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    game=module.create_game(context)
    for method in ['update','lines','status']:
        if not callable(getattr(game,method,None)):raise ValueError(f'游戏缺少 {method}()')
    return game

def install(source,user_root,existing_ids):
    source=Path(source).resolve();info=read_game(source)
    if info.id in existing_ids:raise ValueError('同名游戏已存在，请先修改游戏包的 id')
    destination=Path(user_root)/info.id
    if destination.exists():raise ValueError('目标目录已存在，不会覆盖')
    files=list(source.rglob('*'))
    if any(p.is_symlink() or not p.resolve().is_relative_to(source) for p in files):
        raise ValueError('游戏包不能包含符号链接或目录外文件')
    if sum(p.stat().st_size for p in files if p.is_file())>20*1024*1024:raise ValueError('游戏包超过 20 MB')
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(source,destination,ignore=shutil.ignore_patterns('__pycache__','.git','*.pyc'))
    return read_game(destination)
