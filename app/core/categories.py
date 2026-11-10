# app/core/categories.py
from pathlib import Path

# Пути относительно папки 730
CATEGORIES = {
    "graphics": [
        "local/cfg/cs2_video.txt",
        "local/cfg/cs2_machine_convars.vcfg",
    ],
    "gameplay": [
        "local/cfg/cs2_user_convars_0_slot0.vcfg",
        "local/cfg/cs2_user_keys_0_slot0.vcfg",
        "remote/cfg/cs2_user_convars_0_slot0.vcfg",
        "remote/cfg/cs2_user_keys_0_slot0.vcfg",
    ],
    # autoexec обрабатываем отдельно, потому что путь другой
}

def get_files_for(category_names: list[str], cfg_root: Path) -> list[Path]:
    result = []
    for name in category_names:
        if name == "autoexec":
            # autoexec ищем через steam.get_autoexec_path()
            continue  # обрабатывается в UI-слое
        for rel_path in CATEGORIES.get(name, []):
            full_path = cfg_root / rel_path
            if full_path.exists():
                result.append(full_path)
    return result


def get_rel_paths(category_names: list[str]) -> list[str]:
    result = []
    for name in category_names:
        if name == "autoexec":
            result.append("__autoexec__")  # маркер
            continue
        for rel in CATEGORIES.get(name, []):
            if rel not in result:
                result.append(rel)
    return result