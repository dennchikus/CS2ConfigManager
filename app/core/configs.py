import shutil
from datetime import datetime
from pathlib import Path

from app.core.paths import data_path
from app.core.steam import get_autoexec_path
from app.core.logger import log


def _profile_dir(profile_name: str) -> Path:
    return data_path() / profile_name


def list_profiles() -> list[str]:
    storage = data_path()
    return sorted(
        p.name for p in storage.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    )


def delete_profile(profile_name: str):
    profile = _profile_dir(profile_name)
    if profile.exists():
        shutil.rmtree(profile)
        log.info(f"Профиль удален: {profile_name}")


def save_to_storage(files: list[Path], cfg_root: Path, profile_name: str) -> int:
    profile = _profile_dir(profile_name)
    copied = 0
    for src in files:
        if not src.exists():
            continue
        if src.name == "autoexec.cfg":
            dst = profile / "autoexec.cfg"
        else:
            rel = src.relative_to(cfg_root)
            dst = profile / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
    log.info(f"Сохранено {copied} файлов в профиль '{profile_name}'")
    return copied


def apply_to_account(rel_paths: list[str], cfg_root: Path, profile_name: str) -> int:
    profile = _profile_dir(profile_name)
    if not profile.exists():
        raise FileNotFoundError(f"Профиль '{profile_name}' не найден")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup = data_path() / "_backup" / timestamp

    copied = 0
    for rel in rel_paths:
        if rel == "__autoexec__":
            src_profile = profile / "autoexec.cfg"
            target = get_autoexec_path()
            if target is None or not src_profile.exists():
                continue
            rel_backup = Path("autoexec.cfg")
        else:
            src_profile = profile / rel
            if not src_profile.exists():
                continue
            target = cfg_root / rel
            rel_backup = rel

        # Бэкап текущего файла (сохраняем структуру папок!)
        if target.exists():
            dst_backup = backup / rel_backup
            dst_backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, dst_backup)

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_profile, target)
        copied += 1

    log.info(f"Применено {copied} файлов из '{profile_name}'. Бэкап: {timestamp}")
    return copied


# --- НОВЫЕ ФУНКЦИИ ---

def list_backups() -> list[str]:
    backup_dir = data_path() / "_backup"
    if not backup_dir.exists():
        return []
    return sorted((p.name for p in backup_dir.iterdir() if p.is_dir()), reverse=True)


def rollback_backup(backup_name: str, cfg_root: Path) -> int:
    backup_dir = data_path() / "_backup" / backup_name
    if not backup_dir.exists():
        raise FileNotFoundError(f"Бэкап '{backup_name}' не найден")

    copied = 0
    for src in backup_dir.rglob("*"):
        if src.is_file():
            rel = src.relative_to(backup_dir)
            if rel.name == "autoexec.cfg":
                target = get_autoexec_path()
                if target is None: continue
            else:
                target = cfg_root / rel

            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            copied += 1

    log.info(f"Откат бэкапа '{backup_name}': восстановлено {copied} файлов")
    return copied


def get_profile_contents(profile_name: str) -> dict:
    """Проверяет, какие категории есть в профиле."""
    profile = _profile_dir(profile_name)
    contents = {"graphics": False, "gameplay": False, "autoexec": False}

    if (profile / "local/cfg/cs2_video.txt").exists() or (profile / "local/cfg/cs2_machine_convars.vcfg").exists():
        contents["graphics"] = True

    if (profile / "local/cfg/cs2_user_convars_0_slot0.vcfg").exists() or (
            profile / "remote/cfg/cs2_user_convars_0_slot0.vcfg").exists():
        contents["gameplay"] = True

    if (profile / "autoexec.cfg").exists():
        contents["autoexec"] = True

    return contents