import urllib.request
import re
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtWidgets import (QMainWindow, QMessageBox, QInputDialog,
                             QListWidgetItem, QMenu)
from PyQt6.QtGui import QPixmap, QIcon, QAction
from PyQt6.QtCore import Qt

from app.core.steam import find_accounts, get_username, get_autoexec_path
from app.core.categories import get_files_for, get_rel_paths
from app.core.configs import (save_to_storage, apply_to_account, list_profiles,
                              delete_profile, list_backups, rollback_backup,
                              get_profile_contents)
from app.core.paths import data_path, resource_path
from app.core.logger import log


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ui_path = Path(__file__).parent / "mainwindow.ui"
        uic.loadUi(ui_path, self)

        # Установка иконки окна (если файл есть)
        icon_path = resource_path("app/resources/icons/app_icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.accounts: list[dict] = []
        self.current_cfg_root: Path | None = None
        self.current_profile: str | None = None

        # Подключение сигналов
        self.btnFindAccounts.clicked.connect(self.on_find_accounts)
        self.accountsList.currentRowChanged.connect(self.on_account_selected)
        self.configsList.currentRowChanged.connect(self.on_profile_selected)
        self.btnSave.clicked.connect(self.on_save)
        self.btnApply.clicked.connect(self.on_apply)

        # Контекстное меню для профилей
        self.configsList.customContextMenuRequested.connect(self.show_profile_menu)

        # Бэкапы
        self.btnRollback.clicked.connect(self.on_rollback)
        self.tabsStorage.currentChanged.connect(self.on_tab_changed)

        self._avatar_cache: dict[str, QPixmap] = {}
        self.refresh_profiles()
        self.refresh_backups()

        self.statusBar().showMessage("Готов к работе")
        log.info("--- Программа запущена ---")

    # --- Аватарки и Steam ---
    def _to_steam64(self, steam_id: str) -> str:
        try:
            return str(76561197960265728 + int(steam_id))
        except ValueError:
            return steam_id

    def _avatar_path(self, steam_id: str) -> Path:
        avatars_dir = data_path() / "_avatars"
        avatars_dir.mkdir(exist_ok=True)
        return avatars_dir / f"{steam_id}.jpg"

    def _load_avatar(self, steam_id: str) -> QPixmap | None:
        if steam_id in self._avatar_cache:
            return self._avatar_cache[steam_id]

        cached = self._avatar_path(steam_id)
        if cached.exists():
            pix = QPixmap(str(cached))
            if not pix.isNull():
                self._avatar_cache[steam_id] = pix
                return pix

        try:
            steam64 = self._to_steam64(steam_id)
            url = f"https://steamcommunity.com/profiles/{steam64}/?xml=1"
            req = urllib.request.Request(
                url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                text = resp.read().decode("utf-8", errors="ignore")

            m = re.search(r"<avatarMedium><!\[CDATA\[(.*?)\]\]></avatarMedium>", text)
            if m:
                img_url = m.group(1)
                img_req = urllib.request.Request(
                    img_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(img_req, timeout=5) as img_resp:
                    data = img_resp.read()
                cached.write_bytes(data)
                pix = QPixmap()
                pix.loadFromData(data)
                self._avatar_cache[steam_id] = pix
                return pix
        except Exception as e:
            log.warning(f"Не удалось загрузить аватарку {steam_id}: {e}")
        return None

    # --- Вспомогательное ---
    def refresh_profiles(self):
        self.configsList.clear()
        for p in list_profiles():
            self.configsList.addItem(p)

    def refresh_backups(self):
        self.backupsList.clear()
        for b in list_backups():
            self.backupsList.addItem(b)

    def _selected_categories(self) -> list[str]:
        cats = []
        if self.chkGraphics.isChecked(): cats.append("graphics")
        if self.chkKeys.isChecked(): cats.append("gameplay")
        if self.chkAutoexec.isChecked(): cats.append("autoexec")
        return cats

    # --- Обработчики UI ---
    def on_find_accounts(self):
        try:
            self.accounts = find_accounts()
        except Exception as e:
            log.error(f"Ошибка поиска аккаунтов: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось найти аккаунты:\n{e}")
            return

        self.accountsList.clear()
        for acc in self.accounts:
            nick = get_username(acc["user_dir"]) or "—"
            item = QListWidgetItem(f"{nick} ({acc['steam_id']})")
            pix = self._load_avatar(acc["steam_id"])
            if pix and not pix.isNull():
                scaled = pix.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
                item.setIcon(QIcon(scaled))
            self.accountsList.addItem(item)

        self.statusBar().showMessage(f"Найдено аккаунтов: {len(self.accounts)}")
        log.info(f"Поиск аккаунтов завершен. Найдено: {len(self.accounts)}")

    def on_account_selected(self, row: int):
        if 0 <= row < len(self.accounts):
            self.current_cfg_root = self.accounts[row]["cfg_path"]
        else:
            self.current_cfg_root = None

    def on_profile_selected(self, row: int):
        if row < 0:
            self.current_profile = None
            return
        item = self.configsList.item(row)
        self.current_profile = item.text() if item else None

        # Показываем содержимое профиля в статус-баре
        if self.current_profile:
            contents = get_profile_contents(self.current_profile)
            parts = []
            parts.append(f"Графика: {'✅' if contents['graphics'] else '❌'}")
            parts.append(f"Игровой процесс: {'✅' if contents['gameplay'] else '❌'}")
            parts.append(f"Автоэкзек: {'✅' if contents['autoexec'] else '❌'}")
            self.statusBar().showMessage(" | ".join(parts))

    def on_tab_changed(self, index: int):
        if index == 1:  # Вкладка бэкапов
            self.refresh_backups()

    # --- Действия ---
    def on_save(self):
        if not self.current_cfg_root:
            QMessageBox.warning(self, "Внимание", "Выбери аккаунт из списка слева")
            return
        cats = self._selected_categories()
        if not cats:
            QMessageBox.warning(self, "Внимание", "Поставь хотя бы одну галочку")
            return

        files = get_files_for(cats, self.current_cfg_root)
        if "autoexec" in cats:
            autoexec = get_autoexec_path()
            if autoexec: files.append(autoexec)

        if not files:
            QMessageBox.warning(self, "Пусто", "В аккаунте нет файлов выбранных категорий")
            return

        profile_name, ok = QInputDialog.getText(self, "Имя профиля", "Куда сохранить?", text="default")
        if not ok or not profile_name.strip(): return
        profile_name = profile_name.strip()

        try:
            count = save_to_storage(files, self.current_cfg_root, profile_name)
            self.refresh_profiles()
            self.statusBar().showMessage(f"Сохранено {count} файл(ов) в '{profile_name}'")
        except Exception as e:
            log.error(f"Ошибка сохранения: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")

    def on_apply(self):
        if not self.current_cfg_root:
            QMessageBox.warning(self, "Внимание", "Выбери аккаунт из списка слева")
            return
        if not self.current_profile:
            QMessageBox.warning(self, "Внимание", "Выбери профиль из списка справа")
            return
        cats = self._selected_categories()
        if not cats:
            QMessageBox.warning(self, "Внимание", "Поставь хотя бы одну галочку")
            return

        rel_paths = get_rel_paths(cats)

        confirm = QMessageBox.question(
            self, "Подтверждение",
            f"Применить профиль '{self.current_profile}' к аккаунту?\nТекущие файлы будут сохранены в _backup.",
        )
        if confirm != QMessageBox.StandardButton.Yes: return

        try:
            count = apply_to_account(rel_paths, self.current_cfg_root, self.current_profile)
            self.statusBar().showMessage(f"Применено {count} файл(ов)")
        except Exception as e:
            log.error(f"Ошибка применения: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось применить:\n{e}")

    def show_profile_menu(self, pos):
        item = self.configsList.itemAt(pos)
        if not item: return

        menu = QMenu()
        delete_action = QAction("🗑 Удалить профиль", self)
        delete_action.triggered.connect(self.on_delete_profile)
        menu.addAction(delete_action)
        menu.exec(self.configsList.mapToGlobal(pos))

    def on_delete_profile(self):
        if not self.current_profile: return
        confirm = QMessageBox.question(
            self, "Удаление",
            f"Точно удалить профиль '{self.current_profile}'?\nЭто действие необратимо."
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                delete_profile(self.current_profile)
                self.refresh_profiles()
                self.statusBar().showMessage(f"Профиль '{self.current_profile}' удален")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить:\n{e}")

    def on_rollback(self):
        if not self.current_cfg_root:
            QMessageBox.warning(self, "Внимание", "Выбери аккаунт слева (к которому нужно откатить бэкап)")
            return

        item = self.backupsList.currentItem()
        if not item:
            QMessageBox.warning(self, "Внимание", "Выбери бэкап из списка")
            return

        backup_name = item.text()
        confirm = QMessageBox.question(
            self, "Откат",
            f"Восстановить файлы из бэкапа '{backup_name}' в текущий аккаунт?\nТекущие файлы будут перезаписаны."
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                count = rollback_backup(backup_name, self.current_cfg_root)
                self.statusBar().showMessage(f"Откат завершен. Восстановлено {count} файлов.")
            except Exception as e:
                log.error(f"Ошибка отката: {e}")
                QMessageBox.critical(self, "Ошибка", f"Не удалось откатить:\n{e}")