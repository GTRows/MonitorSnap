from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PyQt6.QtCore import Qt
from tkinter import Tk, simpledialog, messagebox
from display_presets.display_config import DisplayConfigManager
from display_presets.preset_service import PresetService
from display_presets.settings import Settings
from display_presets.gui import MainWindow
from display_presets.hotkey_manager import HotkeyManager
import sys
import os


class TrayApp:
    def __init__(self):
        self.app = QApplication(sys.argv)

        # Set app icon
        # Get path to assets/icons/app.ico (project root/assets/icons/)
        project_root = os.path.dirname(os.path.dirname(__file__))
        icon_path = os.path.join(project_root, "assets", "icons", "app.ico")
        if os.path.exists(icon_path):
            self.app.setWindowIcon(QIcon(icon_path))

        self.display = DisplayConfigManager()
        self.presets = PresetService()
        self.settings = Settings()
        self.hotkey_manager = HotkeyManager()
        self.gui = None

        self.setup_tray()
        self.setup_global_hotkeys()

        # Open GUI on startup unless start_minimized is enabled
        if not self.settings.start_minimized:
            self.open_gui()

    def create_icon(self):
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Monitor icon - simple and clean
        if self.settings.dark_mode:
            color = QColor('#58a6ff')  # GitHub blue
        else:
            color = QColor('#0969da')  # GitHub blue

        # Monitor screen
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(10, 12, 44, 32, 2, 2)

        # Monitor stand base
        painter.drawRect(22, 44, 20, 3)
        painter.drawRect(28, 43, 8, 2)

        painter.end()
        return QIcon(pixmap)

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self.create_icon(), self.app)
        self.tray.setToolTip("Display Presets")

        self.tray.activated.connect(self.on_tray_activated)

        self.build_menu()
        self.tray.show()

    def build_menu(self):
        menu = QMenu()

        dashboard_action = QAction("Dashboard", menu)
        dashboard_action.triggered.connect(self.open_gui)
        menu.addAction(dashboard_action)

        menu.addSeparator()

        save_action = QAction("Save current preset...", menu)
        save_action.triggered.connect(self.save_preset)
        menu.addAction(save_action)

        menu.addSeparator()

        presets_menu = menu.addMenu("Presets")
        names = self.presets.list_names()

        if names:
            for name in names:
                preset_submenu = presets_menu.addMenu(name)

                apply_action = QAction("Apply", preset_submenu)
                apply_action.triggered.connect(lambda checked, n=name: self.apply_preset(n))
                preset_submenu.addAction(apply_action)

                rename_action = QAction("Rename...", preset_submenu)
                rename_action.triggered.connect(lambda checked, n=name: self.rename_preset(n))
                preset_submenu.addAction(rename_action)

                delete_action = QAction("Delete", preset_submenu)
                delete_action.triggered.connect(lambda checked, n=name: self.delete_preset(n))
                preset_submenu.addAction(delete_action)
        else:
            no_presets = QAction("(No presets)", presets_menu)
            no_presets.setEnabled(False)
            presets_menu.addAction(no_presets)

        menu.addSeparator()

        exit_action = QAction("Exit", menu)
        exit_action.triggered.connect(self.exit_app)
        menu.addAction(exit_action)

        self.tray.setContextMenu(menu)

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_gui()

    def setup_global_hotkeys(self):
        """Setup global hotkeys (shared with GUI)"""
        # Will be initialized by GUI when it opens
        pass

    def open_gui(self):
        if not self.gui:
            self.gui = MainWindow(hotkey_manager=self.hotkey_manager, settings=self.settings)
            self.gui.setup_hotkeys()
            self.gui.closed.connect(self.on_gui_closed)
        self.gui.show()
        self.gui.raise_()
        self.gui.activateWindow()

    def on_gui_closed(self):
        self.tray.setIcon(self.create_icon())
        self.build_menu()
        # Hotkeys are managed by GUI, so they persist after closing

    def save_preset(self):
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        name = simpledialog.askstring(
            "Save Current Display Configuration",
            "This will save your current monitor setup as a preset.\n\n"
            "Enter a name for this preset:",
            parent=root
        )
        if name and name.strip():
            try:
                cfg = self.display.get_current()
                self.presets.save(name.strip(), cfg)
                if self.settings.notify_preset_saved:
                    messagebox.showinfo(
                        "Preset Saved Successfully",
                        f"Preset '{name}' has been saved.\n\n"
                        f"You can now apply it anytime from the tray menu.",
                        parent=root
                    )
                self.build_menu()
            except Exception as e:
                if self.settings.show_error_messages:
                    messagebox.showerror("Error", f"Failed to save preset:\n{e}", parent=root)

        root.destroy()

    def apply_preset(self, name):
        try:
            data = self.presets.load(name)
            cfg = data['config']
            result = self.display.apply(cfg)

            root = Tk()
            root.withdraw()
            root.attributes('-topmost', True)

            if result == 0:
                if self.settings.notify_preset_applied:
                    messagebox.showinfo(
                        "Display Configuration Applied",
                        f"Preset '{name}' has been applied successfully.\n\n"
                        f"Your monitors have been configured according to the saved settings.",
                        parent=root
                    )
            else:
                if self.settings.show_error_messages:
                    messagebox.showerror(
                        "Failed to Apply Configuration",
                        f"Could not apply preset '{name}'.\n\n"
                        f"Error code: {result}\n\n"
                        f"Make sure all monitors from this preset are currently connected.",
                        parent=root
                    )

            root.destroy()
        except Exception as e:
            root = Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            messagebox.showerror("Error", f"Failed to apply preset:\n{e}", parent=root)
            root.destroy()

    def rename_preset(self, old_name):
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        new_name = simpledialog.askstring(
            "Rename Preset",
            f"Enter a new name for preset '{old_name}':",
            initialvalue=old_name,
            parent=root
        )
        if new_name and new_name.strip() and new_name != old_name:
            try:
                self.presets.rename(old_name, new_name.strip())
                if self.settings.notify_preset_renamed:
                    messagebox.showinfo(
                        "Preset Renamed",
                        f"Preset has been renamed from '{old_name}' to '{new_name}'.",
                        parent=root
                    )
                self.build_menu()
            except Exception as e:
                if self.settings.show_error_messages:
                    messagebox.showerror("Error", f"Failed to rename preset:\n{e}", parent=root)

        root.destroy()

    def delete_preset(self, name):
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        # Show confirmation dialog if enabled
        confirm = True
        if self.settings.confirm_preset_delete:
            confirm = messagebox.askyesno(
                "Delete Preset",
                f"Are you sure you want to delete preset '{name}'?\n\n"
                f"This action cannot be undone.",
                parent=root
            )

        if confirm:
            try:
                self.presets.delete(name)
                if self.settings.notify_preset_deleted:
                    messagebox.showinfo(
                        "Preset Deleted",
                        f"Preset '{name}' has been permanently deleted.",
                        parent=root
                    )
                self.build_menu()
            except Exception as e:
                if self.settings.show_error_messages:
                    messagebox.showerror("Error", f"Failed to delete preset:\n{e}", parent=root)

        root.destroy()

    def exit_app(self):
        self.hotkey_manager.stop_listening()
        if self.gui:
            self.gui.close()
        self.tray.hide()
        self.app.quit()

    def run(self):
        sys.exit(self.app.exec())
