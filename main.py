import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from app.ui.mainwindow import MainWindow
from app.core.paths import resource_path

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Иконка приложения
    icon_path = resource_path("app/resources/icons/app_icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    win = MainWindow()
    win.show()
    sys.exit(app.exec())