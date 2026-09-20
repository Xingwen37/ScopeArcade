from dataclasses import dataclass
from pathlib import Path
from typing import Callable

@dataclass(frozen=True)
class GameContext:
    data_dir: Path
    player_name: str
    sound: Callable[[str], None]
