from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QListWidget, QPushButton, QLabel,
                             QRadioButton, QButtonGroup, QMessageBox, QInputDialog,
                             QTextEdit, QFrame, QScrollArea, QSplitter, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QFileSystemWatcher
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QIcon
from display_presets.display_config import DisplayConfigManager
from display_presets.preset_service import PresetService
from display_presets.settings import Settings
from display_presets.hotkey_manager import HotkeyManager, parse_hotkey_string, format_hotkey
from display_presets import autostart
from display_presets.config import get_app_dir, get_presets_dir
import subprocess
import os


class MonitorPreviewWidget(QFrame):
    """Visual preview of monitor configuration"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_data = None
        self.setMinimumSize(400, 300)
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(1)

    def set_config(self, config_data):
        """Set the display configuration to preview"""
        self.config_data = config_data
        self.update()

    def clear(self):
        """Clear the preview"""
        self.config_data = None
        self.update()

    def paintEvent(self, event):
        if not self.config_data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get display config
        config = self.config_data.get('config', {})
        paths = config.get('paths', [])
        modes = config.get('modes', [])

        if not paths or not modes:
            return

        # Find monitor bounds
        monitors = []
        for path_idx, path in enumerate(paths):
            if not path.get('targetInfo', {}).get('targetAvailable'):
                continue

            source_idx = path.get('sourceInfo', {}).get('modeInfoIdx')
            target_idx = path.get('targetInfo', {}).get('modeInfoIdx')

            if source_idx is None or source_idx >= len(modes):
                continue

            mode = modes[source_idx]
            if mode.get('infoType') != 1:  # Source mode
                continue

            source_mode = mode.get('sourceMode', {})
            pos = source_mode.get('position', {})
            width = source_mode.get('width', 0)
            height = source_mode.get('height', 0)

            # Get target info for display ID
            target_info = path.get('targetInfo', {})
            target_id = target_info.get('id', 0)

            # Check if this is the primary monitor
            # DISPLAYCONFIG_PATH_ACTIVE (0x1) flag indicates primary/active path
            is_primary = bool(path.get('flags', 0) & 0x1)

            monitors.append({
                'x': pos.get('x', 0),
                'y': pos.get('y', 0),
                'width': width,
                'height': height,
                'active': True,
                'id': target_id,
                'source_id': path.get('sourceInfo', {}).get('id', 0),
                'is_primary': is_primary
            })

        if not monitors:
            return

        # Sort monitors by position (left to right, top to bottom) and assign display numbers
        monitors_sorted = sorted(monitors, key=lambda m: (m['y'], m['x']))
        for idx, monitor in enumerate(monitors_sorted, start=1):
            monitor['display_number'] = idx

        # Calculate bounds
        min_x = min(m['x'] for m in monitors)
        min_y = min(m['y'] for m in monitors)
        max_x = max(m['x'] + m['width'] for m in monitors)
        max_y = max(m['y'] + m['height'] for m in monitors)

        total_width = max_x - min_x
        total_height = max_y - min_y

        # Calculate scale to fit in widget
        padding = 40
        scale_x = (self.width() - padding * 2) / total_width if total_width > 0 else 1
        scale_y = (self.height() - padding * 2) / total_height if total_height > 0 else 1
        scale = min(scale_x, scale_y, 1.0)  # Don't scale up

        # Center the preview
        offset_x = (self.width() - total_width * scale) / 2 - min_x * scale
        offset_y = (self.height() - total_height * scale) / 2 - min_y * scale

        # Group monitors by position (to detect duplicates)
        position_groups = {}
        for monitor in monitors:
            pos_key = (monitor['x'], monitor['y'], monitor['width'], monitor['height'])
            if pos_key not in position_groups:
                position_groups[pos_key] = []
            position_groups[pos_key].append(monitor)

        # Draw monitors
        for i, monitor in enumerate(monitors):
            x = offset_x + monitor['x'] * scale
            y = offset_y + monitor['y'] * scale
            w = monitor['width'] * scale
            h = monitor['height'] * scale

            # Check if duplicate
            pos_key = (monitor['x'], monitor['y'], monitor['width'], monitor['height'])
            is_duplicate = len(position_groups[pos_key]) > 1

            # Monitor background - Windows 11 Fluent Design
            is_dark_mode = self.palette().color(self.backgroundRole()).lightness() < 128
            if is_duplicate:
                # Red for duplicates (Windows 11 red)
                painter.setBrush(QColor('#c42b1c' if is_dark_mode else '#d13438'))
            else:
                # Blue accent for monitors (Windows 11 blue)
                painter.setBrush(QColor('#60cdff' if is_dark_mode else '#0078d4'))

            # Subtle border
            border_color = QColor(255, 255, 255, 20) if is_dark_mode else QColor(0, 0, 0, 15)
            painter.setPen(QPen(border_color, 1))
            painter.drawRoundedRect(int(x), int(y), int(w), int(h), 6, 6)

            # Monitor info with contrasting text
            painter.setPen(QColor('#ffffff'))
            font = QFont("Segoe UI Variable", -1, QFont.Weight.Bold)
            if font.family() != "Segoe UI Variable":  # Fallback if Variable not available
                font = QFont("Segoe UI", -1, QFont.Weight.Bold)
            font.setPixelSize(max(10, int(h * 0.12)))
            painter.setFont(font)

            # Display number at top
            if is_duplicate:
                # Show all display numbers in duplicate group
                display_nums = sorted(set(m['display_number'] for m in position_groups[pos_key]))
                id_text = f"Monitor {', '.join(map(str, display_nums))}"
            else:
                id_text = f"Monitor {monitor['display_number']}"

            # Add primary indicator
            if monitor.get('is_primary', False):
                id_text = f"★ {id_text}"

            painter.drawText(int(x), int(y + h * 0.2), int(w), int(h * 0.3),
                           Qt.AlignmentFlag.AlignCenter, id_text)

            # Resolution at bottom
            font = QFont("Segoe UI Variable", -1, QFont.Weight.Normal)
            if font.family() != "Segoe UI Variable":
                font = QFont("Segoe UI", -1, QFont.Weight.Normal)
            font.setPixelSize(max(8, int(h * 0.1)))
            painter.setFont(font)
            painter.drawText(int(x), int(y + h * 0.5), int(w), int(h * 0.5),
                           Qt.AlignmentFlag.AlignCenter,
                           f"{monitor['width']}×{monitor['height']}")

            if is_duplicate:
                # "DUPLICATE" label
                font = QFont("Segoe UI Variable", -1, QFont.Weight.Bold)
                if font.family() != "Segoe UI Variable":
                    font = QFont("Segoe UI", -1, QFont.Weight.Bold)
                font.setPixelSize(max(7, int(h * 0.08)))
                painter.setFont(font)
                painter.drawText(int(x), int(y + h * 0.7), int(w), int(h * 0.3),
                               Qt.AlignmentFlag.AlignCenter, "DUPLICATE")


class MainWindow(QMainWindow):
    closed = pyqtSignal()

    def __init__(self, hotkey_manager=None):
        super().__init__()
        self.display = DisplayConfigManager()
        self.presets = PresetService()
        self.settings = Settings()
        self.hotkey_manager = hotkey_manager if hotkey_manager else HotkeyManager()
        self.preset_hotkeys = {}  # hotkey_id -> preset_name mapping

        self.setWindowTitle("Display Presets")
        self.setGeometry(100, 100, 1100, 700)
        self.setMinimumSize(1000, 650)

        # Set window icon
        # Get path to assets/icons/app.ico (project root/assets/icons/)
        project_root = os.path.dirname(os.path.dirname(__file__))
        icon_path = os.path.join(project_root, "assets", "icons", "app.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setup_ui()
        self.apply_theme()

        # Setup file watcher for preset folder
        self.file_watcher = QFileSystemWatcher()
        presets_dir = str(get_presets_dir())
        self.file_watcher.addPath(presets_dir)
        self.file_watcher.directoryChanged.connect(self.on_presets_changed)

        if not hotkey_manager:
            # Only setup if we created our own manager
            self.setup_hotkeys()

    def apply_theme(self):
        is_dark = self.settings.dark_mode

        if is_dark:
            # Windows 11 Dark Theme - Fluent Design
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #202020;
                }
                QWidget {
                    background-color: #202020;
                    color: #ffffff;
                    font-family: "Segoe UI Variable", "Segoe UI", system-ui, sans-serif;
                    font-size: 14px;
                }
                QTabWidget::pane {
                    border: none;
                    background-color: transparent;
                }
                QTabBar::tab {
                    background-color: transparent;
                    color: #a0a0a0;
                    padding: 12px 24px;
                    margin-right: 4px;
                    border: none;
                    border-bottom: 2px solid transparent;
                    font-size: 14px;
                    font-weight: 400;
                }
                QTabBar::tab:selected {
                    color: #ffffff;
                    border-bottom: 2px solid #60cdff;
                }
                QTabBar::tab:hover:!selected {
                    color: #e0e0e0;
                    background-color: rgba(255, 255, 255, 0.05);
                }
                QListWidget {
                    background-color: rgba(255, 255, 255, 0.03);
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    padding: 4px;
                    font-size: 14px;
                    outline: none;
                }
                QListWidget::item {
                    background-color: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 6px;
                    padding: 14px 16px;
                    margin: 4px 2px;
                }
                QListWidget::item:selected {
                    background-color: rgba(96, 205, 255, 0.15);
                    border: 1px solid #60cdff;
                    color: #ffffff;
                }
                QListWidget::item:hover:!selected {
                    background-color: rgba(255, 255, 255, 0.08);
                    border-color: rgba(255, 255, 255, 0.12);
                }
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.06);
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: 400;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.09);
                    border-color: rgba(255, 255, 255, 0.12);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.03);
                }
                QPushButton#primary {
                    background-color: #0078d4;
                    color: #ffffff;
                    border: 1px solid #0078d4;
                }
                QPushButton#primary:hover {
                    background-color: #1084d8;
                }
                QPushButton#primary:pressed {
                    background-color: #006cbe;
                }
                QPushButton#danger {
                    background-color: #c42b1c;
                    color: #ffffff;
                    border: 1px solid #c42b1c;
                }
                QPushButton#danger:hover {
                    background-color: #d13438;
                }
                QPushButton#danger:pressed {
                    background-color: #a52313;
                }
                QRadioButton {
                    color: #ffffff;
                    spacing: 10px;
                    font-size: 14px;
                    padding: 8px;
                }
                QRadioButton::indicator {
                    width: 20px;
                    height: 20px;
                    border-radius: 10px;
                    border: 1px solid rgba(255, 255, 255, 0.54);
                    background-color: transparent;
                }
                QRadioButton::indicator:checked {
                    border: 6px solid #60cdff;
                    background-color: transparent;
                }
                QRadioButton::indicator:hover {
                    border-color: #60cdff;
                }
                QTextEdit {
                    background-color: rgba(255, 255, 255, 0.03);
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 6px;
                    padding: 16px;
                    font-size: 14px;
                    line-height: 1.6;
                    selection-background-color: rgba(96, 205, 255, 0.3);
                }
                QLabel {
                    color: #ffffff;
                    background-color: transparent;
                }
                QLabel#title {
                    font-size: 32px;
                    font-weight: 600;
                    color: #ffffff;
                }
                QLabel#subtitle {
                    font-size: 14px;
                    color: #a0a0a0;
                }
                QLabel#section {
                    font-size: 18px;
                    font-weight: 600;
                    color: #ffffff;
                    padding: 12px 0 8px 0;
                }
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                QLineEdit {
                    background-color: rgba(255, 255, 255, 0.06);
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 6px;
                    padding: 10px 14px;
                    font-size: 14px;
                    selection-background-color: rgba(96, 205, 255, 0.3);
                }
                QLineEdit:focus {
                    border: 2px solid #60cdff;
                    padding: 9px 13px;
                }
                QSplitter::handle {
                    background-color: rgba(255, 255, 255, 0.08);
                    width: 1px;
                }
                QFrame[frameShape="4"] {
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    background-color: rgba(255, 255, 255, 0.03);
                }
            """)
        else:
            # Windows 11 Light Theme - Fluent Design
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f3f3f3;
                }
                QWidget {
                    background-color: #f3f3f3;
                    color: #1c1c1c;
                    font-family: "Segoe UI Variable", "Segoe UI", system-ui, sans-serif;
                    font-size: 14px;
                }
                QTabWidget::pane {
                    border: none;
                    background-color: transparent;
                }
                QTabBar::tab {
                    background-color: transparent;
                    color: #605e5c;
                    padding: 12px 24px;
                    margin-right: 4px;
                    border: none;
                    border-bottom: 2px solid transparent;
                    font-size: 14px;
                    font-weight: 400;
                }
                QTabBar::tab:selected {
                    color: #1c1c1c;
                    border-bottom: 2px solid #0078d4;
                }
                QTabBar::tab:hover:!selected {
                    color: #323130;
                    background-color: rgba(0, 0, 0, 0.03);
                }
                QListWidget {
                    background-color: #ffffff;
                    color: #1c1c1c;
                    border: 1px solid rgba(0, 0, 0, 0.08);
                    border-radius: 8px;
                    padding: 4px;
                    font-size: 14px;
                    outline: none;
                }
                QListWidget::item {
                    background-color: #fafafa;
                    border: 1px solid rgba(0, 0, 0, 0.06);
                    border-radius: 6px;
                    padding: 14px 16px;
                    margin: 4px 2px;
                }
                QListWidget::item:selected {
                    background-color: rgba(0, 120, 212, 0.08);
                    border: 1px solid #0078d4;
                    color: #1c1c1c;
                }
                QListWidget::item:hover:!selected {
                    background-color: rgba(0, 0, 0, 0.03);
                    border-color: rgba(0, 0, 0, 0.1);
                }
                QPushButton {
                    background-color: #fafafa;
                    color: #1c1c1c;
                    border: 1px solid rgba(0, 0, 0, 0.08);
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: 400;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                    border-color: rgba(0, 0, 0, 0.12);
                }
                QPushButton:pressed {
                    background-color: #e8e8e8;
                }
                QPushButton#primary {
                    background-color: #0078d4;
                    color: #ffffff;
                    border: 1px solid #0078d4;
                }
                QPushButton#primary:hover {
                    background-color: #106ebe;
                }
                QPushButton#primary:pressed {
                    background-color: #005a9e;
                }
                QPushButton#danger {
                    background-color: #d13438;
                    color: #ffffff;
                    border: 1px solid #d13438;
                }
                QPushButton#danger:hover {
                    background-color: #e81123;
                }
                QPushButton#danger:pressed {
                    background-color: #a80000;
                }
                QRadioButton {
                    color: #1c1c1c;
                    spacing: 10px;
                    font-size: 14px;
                    padding: 8px;
                }
                QRadioButton::indicator {
                    width: 20px;
                    height: 20px;
                    border-radius: 10px;
                    border: 1px solid #605e5c;
                    background-color: #ffffff;
                }
                QRadioButton::indicator:checked {
                    border: 6px solid #0078d4;
                    background-color: #ffffff;
                }
                QRadioButton::indicator:hover {
                    border-color: #0078d4;
                }
                QTextEdit {
                    background-color: #ffffff;
                    color: #1c1c1c;
                    border: 1px solid rgba(0, 0, 0, 0.08);
                    border-radius: 6px;
                    padding: 16px;
                    font-size: 14px;
                    line-height: 1.6;
                    selection-background-color: rgba(0, 120, 212, 0.3);
                }
                QLabel {
                    color: #1c1c1c;
                    background-color: transparent;
                }
                QLabel#title {
                    font-size: 32px;
                    font-weight: 600;
                    color: #1c1c1c;
                }
                QLabel#subtitle {
                    font-size: 14px;
                    color: #605e5c;
                }
                QLabel#section {
                    font-size: 18px;
                    font-weight: 600;
                    color: #1c1c1c;
                    padding: 12px 0 8px 0;
                }
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                QLineEdit {
                    background-color: #ffffff;
                    color: #1c1c1c;
                    border: 1px solid rgba(0, 0, 0, 0.12);
                    border-radius: 6px;
                    padding: 10px 14px;
                    font-size: 14px;
                    selection-background-color: rgba(0, 120, 212, 0.3);
                }
                QLineEdit:focus {
                    border: 2px solid #0078d4;
                    padding: 9px 13px;
                }
                QSplitter::handle {
                    background-color: rgba(0, 0, 0, 0.08);
                    width: 1px;
                }
                QFrame[frameShape="4"] {
                    border: 1px solid rgba(0, 0, 0, 0.08);
                    border-radius: 8px;
                    background-color: #ffffff;
                }
            """)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        layout.addWidget(tabs)

        self.main_tab = QWidget()
        self.settings_tab = QWidget()
        self.about_tab = QWidget()

        tabs.addTab(self.main_tab, "Presets")
        tabs.addTab(self.settings_tab, "Settings")
        tabs.addTab(self.about_tab, "About")

        self.setup_main_tab()
        self.setup_settings_tab()
        self.setup_about_tab()

    def setup_main_tab(self):
        layout = QVBoxLayout(self.main_tab)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # Header
        header = QVBoxLayout()
        header.setSpacing(4)

        title = QLabel("Display Presets")
        title.setObjectName("title")
        header.addWidget(title)

        subtitle = QLabel("Save and restore monitor configurations")
        subtitle.setObjectName("subtitle")
        header.addWidget(subtitle)

        layout.addLayout(header)
        layout.addSpacing(12)

        # Split view: List on left, Preview on right
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: Preset list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)

        self.preset_list = QListWidget()
        self.preset_list.setToolTip("Your saved display configurations. Double-click to apply.")
        self.preset_list.itemDoubleClicked.connect(self.apply_selected)
        self.preset_list.currentItemChanged.connect(self.on_preset_selected)
        left_layout.addWidget(self.preset_list)

        # Buttons below list
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        new_btn = QPushButton("New")
        new_btn.setObjectName("primary")
        new_btn.setMinimumHeight(32)
        new_btn.setToolTip("Save your current display configuration as a new preset")
        new_btn.clicked.connect(self.new_preset)
        btn_layout.addWidget(new_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.setMinimumHeight(32)
        apply_btn.setToolTip("Apply the selected preset to your displays (or double-click the preset)")
        apply_btn.clicked.connect(self.apply_selected)
        btn_layout.addWidget(apply_btn)

        rename_btn = QPushButton("Rename")
        rename_btn.setMinimumHeight(32)
        rename_btn.setToolTip("Change the name of the selected preset")
        rename_btn.clicked.connect(self.rename_selected)
        btn_layout.addWidget(rename_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("danger")
        delete_btn.setMinimumHeight(32)
        delete_btn.setToolTip("Permanently delete the selected preset")
        delete_btn.clicked.connect(self.delete_selected)
        btn_layout.addWidget(delete_btn)

        left_layout.addLayout(btn_layout)

        # Right side: Preview panel
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(12)

        preview_title = QLabel("Preview")
        preview_title.setObjectName("section")
        right_layout.addWidget(preview_title)

        # Monitor preview
        self.monitor_preview = MonitorPreviewWidget()
        right_layout.addWidget(self.monitor_preview, stretch=1)

        # Preset details section
        details_section = QWidget()
        details_layout = QVBoxLayout(details_section)
        details_layout.setContentsMargins(0, 12, 0, 0)
        details_layout.setSpacing(8)

        # Hotkey section label
        hotkey_section_label = QLabel("Hotkey Assignment")
        hotkey_section_label.setObjectName("section")
        details_layout.addWidget(hotkey_section_label)

        # Hotkey input row
        hotkey_layout = QHBoxLayout()
        hotkey_layout.setSpacing(8)

        self.hotkey_input = QLineEdit()
        self.hotkey_input.setPlaceholderText("Enter hotkey combination (e.g., Ctrl+Shift+1) - Optional")
        self.hotkey_input.setToolTip(
            "Assign a global hotkey to instantly apply this preset.\n\n"
            "Examples: Ctrl+Shift+1, Ctrl+Alt+F1, Ctrl+Shift+M\n\n"
            "The hotkey will work even when this window is closed."
        )
        self.hotkey_input.setMinimumHeight(36)
        hotkey_layout.addWidget(self.hotkey_input, stretch=1)

        save_hotkey_btn = QPushButton("Save")
        save_hotkey_btn.setMinimumHeight(36)
        save_hotkey_btn.setMinimumWidth(80)
        save_hotkey_btn.setToolTip("Save the hotkey assignment for the selected preset")
        save_hotkey_btn.clicked.connect(self.save_hotkey)
        hotkey_layout.addWidget(save_hotkey_btn)

        details_layout.addLayout(hotkey_layout)

        right_layout.addWidget(details_section)

        # Add to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        self.refresh_preset_list()

    def setup_settings_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)

        # Header
        title = QLabel("Settings")
        title.setObjectName("title")
        layout.addWidget(title)

        # Appearance Section
        appearance_label = QLabel("Appearance")
        appearance_label.setObjectName("section")
        layout.addWidget(appearance_label)

        theme_group = QButtonGroup(self)
        self.system_theme = QRadioButton("System theme")
        self.dark_theme = QRadioButton("Dark")
        self.light_theme = QRadioButton("Light")

        theme_group.addButton(self.system_theme)
        theme_group.addButton(self.dark_theme)
        theme_group.addButton(self.light_theme)

        if self.settings.theme_mode == "system":
            self.system_theme.setChecked(True)
        elif self.settings.theme_mode == "dark":
            self.dark_theme.setChecked(True)
        else:
            self.light_theme.setChecked(True)

        self.system_theme.toggled.connect(lambda: self.change_theme("system"))
        self.dark_theme.toggled.connect(lambda: self.change_theme("dark"))
        self.light_theme.toggled.connect(lambda: self.change_theme("light"))

        layout.addWidget(self.system_theme)
        layout.addWidget(self.dark_theme)
        layout.addWidget(self.light_theme)

        layout.addSpacing(8)

        # Startup Section
        startup_label = QLabel("Startup")
        startup_label.setObjectName("section")
        layout.addWidget(startup_label)

        autostart_text = QLabel("Run Display Presets when Windows starts")
        autostart_text.setObjectName("subtitle")
        layout.addWidget(autostart_text)

        autostart_btn = QPushButton("Enable autostart" if not autostart.is_enabled() else "Disable autostart")
        autostart_btn.setMinimumHeight(36)
        autostart_btn.setMaximumWidth(200)
        autostart_btn.clicked.connect(self.toggle_autostart)
        layout.addWidget(autostart_btn)
        self.autostart_btn = autostart_btn

        layout.addSpacing(8)

        # Data Section
        data_label = QLabel("Data")
        data_label.setObjectName("section")
        layout.addWidget(data_label)

        folder_label = QLabel(str(get_app_dir()))
        folder_label.setObjectName("subtitle")
        folder_label.setWordWrap(True)
        layout.addWidget(folder_label)

        open_folder_btn = QPushButton("Open in Explorer")
        open_folder_btn.setMinimumHeight(36)
        open_folder_btn.setMaximumWidth(200)
        open_folder_btn.clicked.connect(self.open_data_folder)
        layout.addWidget(open_folder_btn)

        layout.addStretch()

        scroll.setWidget(content)

        main_layout = QVBoxLayout(self.settings_tab)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def setup_about_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        title = QLabel("About Display Presets")
        title.setObjectName("title")
        layout.addWidget(title)

        version = QLabel("Version 1.0.0")
        version.setObjectName("subtitle")
        layout.addWidget(version)

        layout.addSpacing(16)

        text = QTextEdit()
        text.setReadOnly(True)

        info = f"""Display Presets is a Windows utility for saving and restoring monitor configurations.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HOW TO USE

Save a Preset
  1. Arrange your monitors in Windows Display Settings
  2. Click "New" button or use the tray menu
  3. Enter a name for your preset
  4. Your configuration is saved automatically

Restore a Preset
  1. Select a preset from the list
  2. Click "Apply" or double-click the preset
  3. Your monitors will be configured instantly

Manage Presets
  • Rename - Change the preset name
  • Delete - Remove a preset permanently
  • Hotkeys - Assign keyboard shortcuts for instant switching

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT GETS SAVED

• Monitor positions (X, Y coordinates)
• Screen resolutions (width and height)
• Refresh rates
• Screen orientation (rotation)
• Primary monitor selection
• Display topology (extend/duplicate/single)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TECHNICAL DETAILS

Uses Windows Display Configuration API:
• GetDisplayConfigBufferSizes
• QueryDisplayConfig
• SetDisplayConfig

Data Location: {get_app_dir()}

Presets are saved as JSON files and persist across restarts.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

KNOWN LIMITATIONS

• All monitors from a preset must be connected to apply it
• Some docking stations may need a few seconds to stabilize
• Cannot override hardware or driver limitations
• Custom refresh rates from GPU control panels may not be saved

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OPEN SOURCE

This project is released under the MIT License.
Contributions, bug reports, and feature requests are welcome!

Repository: github.com/yourusername/DisplayPresets

To contribute:
1. Visit the GitHub repository
2. Open an issue or pull request
3. Follow the contributing guidelines in README.md
"""

        text.setText(info)
        layout.addWidget(text)

        scroll.setWidget(content)

        main_layout = QVBoxLayout(self.about_tab)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def refresh_preset_list(self):
        # Remember current selection
        current = self.preset_list.currentItem()
        current_name = current.text() if current else None

        self.preset_list.clear()
        for name in self.presets.list_names():
            self.preset_list.addItem(name)

        # Restore selection if possible
        if current_name:
            items = self.preset_list.findItems(current_name, Qt.MatchFlag.MatchExactly)
            if items:
                self.preset_list.setCurrentItem(items[0])

    def on_presets_changed(self, path):
        """Called when preset folder changes"""
        # Refresh the list
        self.refresh_preset_list()
        # Re-register hotkeys in case they changed
        self.setup_hotkeys()

    def on_preset_selected(self, current, previous):
        """Called when a preset is selected in the list"""
        if not current:
            self.monitor_preview.clear()
            self.hotkey_input.clear()
            return

        name = current.text()
        try:
            # Load preset data
            data = self.presets.load(name)

            # Update preview
            self.monitor_preview.set_config(data)

            # Update hotkey input
            hotkey = data.get('hotkey')
            if hotkey:
                self.hotkey_input.setText(hotkey)
            else:
                self.hotkey_input.clear()
        except Exception as e:
            print(f"Error loading preset preview: {e}")

    def save_hotkey(self):
        """Save hotkey for selected preset"""
        current = self.preset_list.currentItem()
        if not current:
            QMessageBox.warning(
                self,
                "No Preset Selected",
                "Please select a preset to assign a hotkey to it."
            )
            return

        name = current.text()
        hotkey_str = self.hotkey_input.text().strip()

        try:
            # Validate hotkey if provided
            if hotkey_str:
                parsed = parse_hotkey_string(hotkey_str)
                if not parsed:
                    QMessageBox.warning(
                        self,
                        "Invalid Hotkey Format",
                        "Please use a valid hotkey format.\n\n"
                        "Examples:\n"
                        "• Ctrl+Shift+1\n"
                        "• Ctrl+Alt+F1\n"
                        "• Ctrl+Shift+M\n\n"
                        "Supported modifiers: Ctrl, Alt, Shift\n"
                        "Supported keys: A-Z, 0-9, F1-F12"
                    )
                    return

            # Save hotkey
            self.presets.set_hotkey(name, hotkey_str if hotkey_str else None)

            # Re-register hotkeys
            self.setup_hotkeys()

            if hotkey_str:
                QMessageBox.information(
                    self,
                    "Hotkey Assigned",
                    f"Hotkey '{hotkey_str}' has been assigned to preset '{name}'.\n\n"
                    f"You can now press {hotkey_str} anytime to instantly apply this preset."
                )
            else:
                QMessageBox.information(
                    self,
                    "Hotkey Removed",
                    f"Hotkey has been removed from preset '{name}'."
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save hotkey:\n{e}")

    def setup_hotkeys(self):
        """Setup all hotkeys for presets"""
        # Unregister all existing hotkeys
        self.hotkey_manager.unregister_all()
        self.preset_hotkeys.clear()

        # Register hotkeys for each preset
        preset_names = self.presets.list_names()
        hotkey_id = 1

        for name in preset_names:
            try:
                data = self.presets.load(name)
                hotkey_str = data.get('hotkey')

                if hotkey_str:
                    parsed = parse_hotkey_string(hotkey_str)
                    if parsed:
                        modifiers, key = parsed
                        if self.hotkey_manager.register(modifiers, key, hotkey_id):
                            self.preset_hotkeys[hotkey_id] = name
                            hotkey_id += 1
            except Exception as e:
                print(f"Error registering hotkey for {name}: {e}")

        # Connect hotkey signals
        try:
            self.hotkey_manager.hotkey_pressed.disconnect()
        except:
            pass
        self.hotkey_manager.hotkey_pressed.connect(self.on_hotkey_pressed)
        self.hotkey_manager.start_listening()

    def on_hotkey_pressed(self, hotkey_id):
        """Handle hotkey press"""
        if hotkey_id in self.preset_hotkeys:
            name = self.preset_hotkeys[hotkey_id]
            try:
                data = self.presets.load(name)
                result = self.display.apply(data['config'])
                if result != 0:
                    print(f"Failed to apply preset '{name}': error code {result}")
            except Exception as e:
                print(f"Error applying preset from hotkey: {e}")

    def apply_selected(self):
        current = self.preset_list.currentItem()
        if not current:
            QMessageBox.warning(
                self,
                "No Preset Selected",
                "Please select a preset from the list to apply it to your displays."
            )
            return

        name = current.text()
        try:
            data = self.presets.load(name)
            result = self.display.apply(data['config'])

            if result == 0:
                QMessageBox.information(
                    self,
                    "Display Configuration Applied",
                    f"Preset '{name}' has been applied successfully.\n\n"
                    f"Your monitors have been configured according to the saved settings."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Failed to Apply Configuration",
                    f"Could not apply preset '{name}'.\n\n"
                    f"Error code: {result}\n\n"
                    f"Make sure all monitors from this preset are currently connected."
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply preset:\n{e}")

    def new_preset(self):
        name, ok = QInputDialog.getText(
            self,
            "Save Current Display Configuration",
            "This will save your current monitor setup as a preset.\n\n"
            "Your current settings will be saved:\n"
            "• Monitor positions and arrangement\n"
            "• Screen resolutions and refresh rates\n"
            "• Display orientation\n"
            "• Primary monitor\n\n"
            "Enter a name for this preset:"
        )
        if ok and name and name.strip():
            try:
                cfg = self.display.get_current()
                self.presets.save(name.strip(), cfg)
                QMessageBox.information(
                    self,
                    "Preset Saved Successfully",
                    f"Preset '{name}' has been saved.\n\n"
                    f"You can now apply this configuration anytime by selecting it from the list."
                )
                self.refresh_preset_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save preset:\n{e}")

    def rename_selected(self):
        current = self.preset_list.currentItem()
        if not current:
            QMessageBox.warning(
                self,
                "No Preset Selected",
                "Please select a preset from the list to rename it."
            )
            return

        old_name = current.text()
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Preset",
            f"Enter a new name for preset '{old_name}':",
            text=old_name
        )

        if ok and new_name and new_name.strip() and new_name != old_name:
            try:
                self.presets.rename(old_name, new_name.strip())
                QMessageBox.information(
                    self,
                    "Preset Renamed",
                    f"Preset has been renamed from '{old_name}' to '{new_name}'."
                )
                self.refresh_preset_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to rename preset:\n{e}")

    def delete_selected(self):
        current = self.preset_list.currentItem()
        if not current:
            QMessageBox.warning(
                self,
                "No Preset Selected",
                "Please select a preset from the list to delete it."
            )
            return

        name = current.text()
        reply = QMessageBox.question(
            self,
            "Delete Preset",
            f"Are you sure you want to delete preset '{name}'?\n\n"
            f"This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.presets.delete(name)
                QMessageBox.information(
                    self,
                    "Preset Deleted",
                    f"Preset '{name}' has been permanently deleted."
                )
                self.refresh_preset_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete preset:\n{e}")

    def change_theme(self, mode):
        if self.sender().isChecked():
            self.settings.set_theme(mode)
            QMessageBox.information(self, "Theme changed",
                                   "Restart the application to apply the new theme.")
            self.closed.emit()

    def toggle_autostart(self):
        try:
            enabled = autostart.toggle()
            self.autostart_btn.setText("Disable autostart" if enabled else "Enable autostart")
            msg = "Display Presets will start with Windows." if enabled else "Autostart disabled."
            QMessageBox.information(self, "Autostart", msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to toggle autostart:\n{e}")

    def open_data_folder(self):
        try:
            subprocess.Popen(f'explorer "{get_app_dir()}"')
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Can't open folder:\n{e}")

    def closeEvent(self, event):
        if event.spontaneous():
            # User clicked X button - just hide
            event.ignore()
            self.hide()
        else:
            # App is closing
            self.hotkey_manager.stop_listening()
            event.accept()
