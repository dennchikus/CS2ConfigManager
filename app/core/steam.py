from pathlib import Path
import winreg
import vdf

# Файлы, наличие которых означает, что аккаунт реально использовался в CS2
_REQUIRED_FILES = [
    "local/cfg/cs2_video.txt",
    "local/cfg/cs2_user_convars_0_slot0.vcfg",
    "remote/cfg/cs2_user_convars_0_slot0.vcfg",
]


def find_accounts():
    accounts = []
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
    steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
    userdata_path = Path(steam_path) / "userdata"

    for user_dir in userdata_path.iterdir():
        cfg_root = user_dir / "730"
        if not cfg_root.exists():
            continue
        # Проверяем, есть ли хоть один реальный файл конфига
        has_files = any((cfg_root / rel).exists() for rel in _REQUIRED_FILES)
        if not has_files:
            continue
        accounts.append({
            "steam_id": user_dir.name,
            "cfg_path": cfg_root,
            "user_dir": user_dir,
        })
    return accounts


def get_username(user_dir: Path) -> str | None:
    cfg_file = user_dir / "config" / "localconfig.vdf"
    try:
        with open(cfg_file, encoding="utf-8") as f:
            data = vdf.load(f)
        return data["UserLocalConfigStore"]["friends"]["PersonaName"]
    except (FileNotFoundError, KeyError):
        return None


def get_autoexec_path() -> Path | None:
    """Ищет autoexec.cfg в папке установки игры."""
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
    steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
    # InstallPath может быть в реестре, но часто совпадает с SteamPath
    try:
        install_key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Valve\Steam",
        )
        install_path, _ = winreg.QueryValueEx(install_key, "InstallPath")
    except FileNotFoundError:
        install_path = steam_path

    candidate = Path(install_path) / "steamapps" / "common" / \
        "Counter-Strike Global Offensive" / "game" / "csgo" / "cfg" / "autoexec.cfg"
    return candidate if candidate.exists() else None