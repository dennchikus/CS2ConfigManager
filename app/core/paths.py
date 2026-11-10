import sys
from pathlib import Path


def data_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(sys.argv[0]).resolve().parent
    storage = base / "storage"
    storage.mkdir(exist_ok=True)
    return storage


def resource_path(relative: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parents[2]  # app/core/paths.py -> корень
    return base / relative