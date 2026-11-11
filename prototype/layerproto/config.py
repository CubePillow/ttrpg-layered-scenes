"""Settings for the layer prototype (everything runs on the Kaggle GPU servers; nothing here loads a model).

Defaults live here. Override any of them in prototype/config.json, e.g.
    {"width": 512, "first_steps": 4}
The GPU servers (URL + token of the Kaggle notebooks) are NOT settings: see layerproto/connection.py.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field

PROTO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROTO_DIR, "config.json")


@dataclass
class Settings:
    width: int = 512            # canvas of every scene; the Qwen-Image-2.1 profile works at 512 px
    height: int = 512
    first_steps: int = 4        # SDXL-Turbo steps for the first picture
    first_seed: int = 13
    idle_minutes: float = 20    # a Kaggle server stops itself after this many minutes without a request
    scenes_dir: str = field(default_factory=lambda: os.path.join(PROTO_DIR, "scenes"))

    def save(self) -> str:
        """Persist everything except the scenes folder to prototype/config.json."""
        d = {k: v for k, v in asdict(self).items() if k != "scenes_dir"}
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
        return CONFIG_PATH


def load_settings() -> Settings:
    s = Settings()
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            for k, v in json.load(f).items():
                if hasattr(s, k):
                    setattr(s, k, v)
    return s
