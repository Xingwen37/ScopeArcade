"""Build the Windows x64 folder distribution; no vendor runtimes included."""
from importlib.metadata import version,distribution
import json
from pathlib import Path
import shutil
import subprocess
import sys
from scope_arcade import __version__

ROOT=Path(__file__).resolve().parent

def main():
    if sys.platform!='win32':raise SystemExit('Windows packaging must run on Windows')
    cmd=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--name','ScopeArcade',
         '--hidden-import','random','--hidden-import','dataclasses','--hidden-import','winsound',
         '--hidden-import','zipfile','--hidden-import','struct',
         '--exclude-module','cv2','--exclude-module','numpy',
         '--collect-submodules','pyvisa']
    # Include portable source/assets, not bytecode caches from the build computer.
    for folder in ['games','game-template']:
        for source in sorted((ROOT/folder).rglob('*')):
            if source.is_file() and '__pycache__' not in source.parts and source.suffix!='.pyc':
                cmd.extend(['--add-data',f'{source};{source.parent.relative_to(ROOT)}'])
    cmd.append(str(ROOT/'main.py'))
    subprocess.run(cmd,cwd=ROOT,check=True)
    target=ROOT/'dist/ScopeArcade'
    for name in ['README.md','LICENSE','THIRD_PARTY_NOTICES.md']:shutil.copy2(ROOT/name,target/name)
    for name in ['docs','game-template']:
        shutil.copytree(ROOT/name,target/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    licenses=target/'licenses';licenses.mkdir(exist_ok=True)
    for source in (ROOT/'third_party_licenses').glob('*'):
        if source.is_file():shutil.copy2(source,licenses/source.name)
    python_license=Path(sys.base_prefix)/'LICENSE.txt'
    if python_license.exists():shutil.copy2(python_license,licenses/'Python-LICENSE.txt')
    for package in ['pyserial','pyvisa','pyinstaller']:
        dist=distribution(package)
        for file in dist.files or []:
            if 'license' in str(file).lower() and dist.locate_file(file).is_file():
                shutil.copy2(dist.locate_file(file),licenses/(package+'-'+Path(str(file)).name))
    # Preserve Tcl/Tk license texts from the Python distribution when available.
    for source in (Path(sys.base_prefix)/'tcl').glob('*/license.terms'):
        shutil.copy2(source,licenses/(source.parent.name+'-license.terms'))
    info={'app_version':__version__,'python':sys.version,'packages':{name:version(name) for name in ['pyserial','pyvisa','pyinstaller']}}
    (target/'build-info.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    release=ROOT/'release';release.mkdir(exist_ok=True)
    archive=shutil.make_archive(str(release/f'ScopeArcade-v{__version__}-Windows-x64'),'zip',ROOT/'dist','ScopeArcade')
    print(archive)

if __name__=='__main__':main()
