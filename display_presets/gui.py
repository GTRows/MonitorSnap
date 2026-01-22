from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QListWidget, QPushButton, QLabel,
                             QRadioButton, QButtonGroup, QMessageBox, QInputDialog,
                             QTextEdit, QFrame, QScrollArea, QSplitter, QLineEdit,
                             QStackedWidget, QCheckBox, QSlider, QToolTip)
from PyQt6.QtCore import Qt, pyqtSignal, QFileSystemWatcher, QPoint, QRect, QRectF
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QIcon, QCursor, QBrush
from display_presets.display_config import DisplayConfigManager
from display_presets.preset_service import PresetService
from display_presets.settings import Settings
from display_presets.hotkey_manager import HotkeyManager, parse_hotkey_string, format_hotkey
from display_presets import autostart
from display_presets.config import get_app_dir, get_presets_dir
from display_presets.theme_colors import get_stylesheet, get_help_label_style, get_monitor_preview_colors, GitHubDark, GitHubLight
import subprocess
import os


class MonitorPreviewWidget(QFrame):
    """Interactive visual preview of monitor configuration with edit mode"""

    # Signals
    config_changed = pyqtSignal(dict)  # Emitted when monitors are moved in edit mode
    primary_changed = pyqtSignal(int)  # Emitted when primary monitor is changed

    SNAP_THRESHOLD = 20  # Pixels for snap-to-edge

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_data = None
        self.monitors = []  # Parsed monitor data
        self.setMinimumSize(400, 300)
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(1)

        # Edit mode state
        self.edit_mode = False
        self.dragging = False
        self.dragged_monitor_idx = -1
        self.drag_start_pos = None
        self.drag_start_monitor_pos = None
        self.hovered_monitor_idx = -1

        # Scale and offset for coordinate transformation
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

    def set_edit_mode(self, enabled):
        """Enable or disable edit mode"""
        self.edit_mode = enabled
        if enabled:
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.update()

    def set_config(self, config_data):
        """Set the display configuration to preview"""
        self.config_data = config_data
        self._parse_monitors()
        self.update()

    def clear(self):
        """Clear the preview"""
        self.config_data = None
        self.monitors = []
        self.update()

    def get_modified_config(self):
        """Get the modified configuration after edit"""
        if not self.config_data:
            return None

        # Deep copy the config
        import copy
        modified = copy.deepcopy(self.config_data)
        config = modified.get('config', {})
        modes = config.get('modes', [])

        # Update positions from monitors list
        for monitor in self.monitors:
            source_idx = monitor.get('source_mode_idx')
            if source_idx is not None and source_idx < len(modes):
                mode = modes[source_idx]
                if mode.get('infoType') == 1:
                    mode['sourceMode']['position']['x'] = monitor['x']
                    mode['sourceMode']['position']['y'] = monitor['y']

        return modified

    def _parse_monitors(self):
        """Parse config data into monitor list"""
        self.monitors = []
        if not self.config_data:
            return

        config = self.config_data.get('config', {})
        paths = config.get('paths', [])
        modes = config.get('modes', [])

        if not paths or not modes:
            return

        for path_idx, path in enumerate(paths):
            if not path.get('targetInfo', {}).get('targetAvailable'):
                continue

            source_idx = path.get('sourceInfo', {}).get('modeInfoIdx')
            if source_idx is None or source_idx >= len(modes):
                continue

            mode = modes[source_idx]
            if mode.get('infoType') != 1:
                continue

            source_mode = mode.get('sourceMode', {})
            pos = source_mode.get('position', {})

            self.monitors.append({
                'x': pos.get('x', 0),
                'y': pos.get('y', 0),
                'width': source_mode.get('width', 0),
                'height': source_mode.get('height', 0),
                'id': path.get('targetInfo', {}).get('id', 0),
                'source_id': path.get('sourceInfo', {}).get('id', 0),
                'is_primary': bool(path.get('flags', 0) & 0x1),
                'path_idx': path_idx,
                'source_mode_idx': source_idx
            })

        # Assign display numbers
        monitors_sorted = sorted(enumerate(self.monitors), key=lambda x: (x[1]['y'], x[1]['x']))
        for display_num, (idx, _) in enumerate(monitors_sorted, start=1):
            self.monitors[idx]['display_number'] = display_num

    def _calculate_transform(self):
        """Calculate scale and offset for coordinate transformation"""
        if not self.monitors:
            return

        min_x = min(m['x'] for m in self.monitors)
        min_y = min(m['y'] for m in self.monitors)
        max_x = max(m['x'] + m['width'] for m in self.monitors)
        max_y = max(m['y'] + m['height'] for m in self.monitors)

        total_width = max_x - min_x
        total_height = max_y - min_y

        padding = 40
        scale_x = (self.width() - padding * 2) / total_width if total_width > 0 else 1
        scale_y = (self.height() - padding * 2) / total_height if total_height > 0 else 1
        self.scale = min(scale_x, scale_y, 0.15)  # Cap scale for large resolutions

        self.offset_x = (self.width() - total_width * self.scale) / 2 - min_x * self.scale
        self.offset_y = (self.height() - total_height * self.scale) / 2 - min_y * self.scale

    def _monitor_to_screen(self, x, y):
        """Convert monitor coordinates to screen coordinates"""
        return (self.offset_x + x * self.scale, self.offset_y + y * self.scale)

    def _screen_to_monitor(self, sx, sy):
        """Convert screen coordinates to monitor coordinates"""
        return (int((sx - self.offset_x) / self.scale), int((sy - self.offset_y) / self.scale))

    def _get_monitor_rect(self, monitor):
        """Get screen rectangle for a monitor"""
        x, y = self._monitor_to_screen(monitor['x'], monitor['y'])
        w = monitor['width'] * self.scale
        h = monitor['height'] * self.scale
        return QRectF(x, y, w, h)

    def _get_monitor_at(self, pos):
        """Get monitor index at screen position, -1 if none"""
        for i, monitor in enumerate(self.monitors):
            rect = self._get_monitor_rect(monitor)
            if rect.contains(pos.x(), pos.y()):
                return i
        return -1

    def _snap_to_edges(self, monitor_idx, new_x, new_y):
        """Snap monitor to edges of other monitors"""
        monitor = self.monitors[monitor_idx]
        w, h = monitor['width'], monitor['height']

        # Edges of the dragged monitor
        left, right = new_x, new_x + w
        top, bottom = new_y, new_y + h

        snap_x, snap_y = new_x, new_y

        for i, other in enumerate(self.monitors):
            if i == monitor_idx:
                continue

            o_left, o_right = other['x'], other['x'] + other['width']
            o_top, o_bottom = other['y'], other['y'] + other['height']

            # Horizontal snapping
            # Right edge to left edge
            if abs(right - o_left) < self.SNAP_THRESHOLD / self.scale:
                snap_x = o_left - w
            # Left edge to right edge
            elif abs(left - o_right) < self.SNAP_THRESHOLD / self.scale:
                snap_x = o_right
            # Left edge to left edge
            elif abs(left - o_left) < self.SNAP_THRESHOLD / self.scale:
                snap_x = o_left
            # Right edge to right edge
            elif abs(right - o_right) < self.SNAP_THRESHOLD / self.scale:
                snap_x = o_right - w

            # Vertical snapping
            # Bottom edge to top edge
            if abs(bottom - o_top) < self.SNAP_THRESHOLD / self.scale:
                snap_y = o_top - h
            # Top edge to bottom edge
            elif abs(top - o_bottom) < self.SNAP_THRESHOLD / self.scale:
                snap_y = o_bottom
            # Top edge to top edge
            elif abs(top - o_top) < self.SNAP_THRESHOLD / self.scale:
                snap_y = o_top
            # Bottom edge to bottom edge
            elif abs(bottom - o_bottom) < self.SNAP_THRESHOLD / self.scale:
                snap_y = o_bottom - h

        return int(snap_x), int(snap_y)

    def mousePressEvent(self, event):
        if not self.edit_mode or event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)

        idx = self._get_monitor_at(event.pos())
        if idx >= 0:
            self.dragging = True
            self.dragged_monitor_idx = idx
            self.drag_start_pos = event.pos()
            self.drag_start_monitor_pos = (self.monitors[idx]['x'], self.monitors[idx]['y'])
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))

    def mouseMoveEvent(self, event):
        if not self.edit_mode:
            return super().mouseMoveEvent(event)

        if self.dragging and self.dragged_monitor_idx >= 0:
            # Calculate delta in screen coordinates
            delta = event.pos() - self.drag_start_pos

            # Convert to monitor coordinates
            delta_mx = int(delta.x() / self.scale)
            delta_my = int(delta.y() / self.scale)

            # New position
            new_x = self.drag_start_monitor_pos[0] + delta_mx
            new_y = self.drag_start_monitor_pos[1] + delta_my

            # Snap to edges
            new_x, new_y = self._snap_to_edges(self.dragged_monitor_idx, new_x, new_y)

            # Update monitor position
            self.monitors[self.dragged_monitor_idx]['x'] = new_x
            self.monitors[self.dragged_monitor_idx]['y'] = new_y

            self.update()
        else:
            # Hover effect
            idx = self._get_monitor_at(event.pos())
            if idx != self.hovered_monitor_idx:
                self.hovered_monitor_idx = idx
                self.update()

    def mouseReleaseEvent(self, event):
        if not self.edit_mode or event.button() != Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)

        if self.dragging:
            self.dragging = False
            self.dragged_monitor_idx = -1
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
            self.config_changed.emit(self.get_modified_config())

    def mouseDoubleClickEvent(self, event):
        """Double click to set primary monitor"""
        if not self.edit_mode:
            return super().mouseDoubleClickEvent(event)

        idx = self._get_monitor_at(event.pos())
        if idx >= 0:
            # Set this monitor as primary
            for i, monitor in enumerate(self.monitors):
                monitor['is_primary'] = (i == idx)
            self.primary_changed.emit(idx)
            self.update()

    def leaveEvent(self, event):
        self.hovered_monitor_idx = -1
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_dark_mode = self.palette().color(self.backgroundRole()).lightness() < 128

        # Draw background hint in edit mode
        if self.edit_mode and not self.monitors:
            painter.setPen(QColor('#8b949e' if is_dark_mode else '#57606a'))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No monitors to edit")
            return

        if not self.monitors:
            return

        self._calculate_transform()

        # Group monitors by position (to detect duplicates)
        position_groups = {}
        for i, monitor in enumerate(self.monitors):
            pos_key = (monitor['x'], monitor['y'], monitor['width'], monitor['height'])
            if pos_key not in position_groups:
                position_groups[pos_key] = []
            position_groups[pos_key].append(i)

        # Draw monitors
        for i, monitor in enumerate(self.monitors):
            rect = self._get_monitor_rect(monitor)
            x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

            pos_key = (monitor['x'], monitor['y'], monitor['width'], monitor['height'])
            is_duplicate = len(position_groups[pos_key]) > 1
            is_hovered = (i == self.hovered_monitor_idx) and self.edit_mode
            is_dragging = (i == self.dragged_monitor_idx) and self.dragging

            # Monitor background color
            if is_duplicate:
                bg_color = QColor('#c42b1c' if is_dark_mode else '#d13438')
            elif is_hovered or is_dragging:
                bg_color = QColor('#3b8eea' if is_dark_mode else '#106ebe')
            else:
                bg_color = QColor('#60cdff' if is_dark_mode else '#0078d4')

            painter.setBrush(bg_color)

            # Border
            if is_hovered or is_dragging:
                border_color = QColor('#ffffff' if is_dark_mode else '#000000')
                painter.setPen(QPen(border_color, 2))
            else:
                border_color = QColor(255, 255, 255, 20) if is_dark_mode else QColor(0, 0, 0, 15)
                painter.setPen(QPen(border_color, 1))

            painter.drawRoundedRect(rect, 6, 6)

            # Text
            painter.setPen(QColor('#ffffff'))
            font = QFont("Segoe UI Variable", -1, QFont.Weight.Bold)
            if font.family() != "Segoe UI Variable":
                font = QFont("Segoe UI", -1, QFont.Weight.Bold)
            font.setPixelSize(max(10, int(h * 0.12)))
            painter.setFont(font)

            # Display number
            if is_duplicate:
                display_nums = sorted(set(self.monitors[j]['display_number'] for j in position_groups[pos_key]))
                id_text = f"Monitor {', '.join(map(str, display_nums))}"
            else:
                id_text = f"Monitor {monitor['display_number']}"

            if monitor.get('is_primary', False):
                id_text = f"★ {id_text}"

            painter.drawText(QRectF(x, y + h * 0.15, w, h * 0.3), Qt.AlignmentFlag.AlignCenter, id_text)

            # Resolution
            font.setWeight(QFont.Weight.Normal)
            font.setPixelSize(max(8, int(h * 0.1)))
            painter.setFont(font)
            painter.drawText(QRectF(x, y + h * 0.45, w, h * 0.25), Qt.AlignmentFlag.AlignCenter,
                           f"{monitor['width']}×{monitor['height']}")

            # Duplicate label
            if is_duplicate:
                font.setWeight(QFont.Weight.Bold)
                font.setPixelSize(max(7, int(h * 0.08)))
                painter.setFont(font)
                painter.drawText(QRectF(x, y + h * 0.7, w, h * 0.2), Qt.AlignmentFlag.AlignCenter, "DUPLICATE")

            # Edit mode hint
            if self.edit_mode and is_hovered and not is_dragging:
                hint_font = QFont("Segoe UI", 9)
                painter.setFont(hint_font)
                painter.setPen(QColor(255, 255, 255, 200))
                painter.drawText(QRectF(x, y + h - 20, w, 20), Qt.AlignmentFlag.AlignCenter, "Drag to move • Double-click for primary")

        # Edit mode indicator
        if self.edit_mode:
            painter.setPen(QColor('#1f6feb' if is_dark_mode else '#0969da'))
            font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(10, 20, "EDIT MODE")


class MainWindow(QMainWindow):
    closed = pyqtSignal()

    def __init__(self, hotkey_manager=None, settings=None):
        super().__init__()
        self.display = DisplayConfigManager()
        self.presets = PresetService()
        self.settings = settings if settings else Settings()
        self.hotkey_manager = hotkey_manager if hotkey_manager else HotkeyManager()
        self.preset_hotkeys = {}  # hotkey_id -> preset_name mapping

        self.setWindowTitle("Display Presets")
        # Use settings for window size
        self.setGeometry(100, 100, self.settings.window_width, self.settings.window_height)
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
            # GitHub Dark Theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #0d1117;
                }
                QWidget {
                    background-color: #0d1117;
                    color: #c9d1d9;
                    font-family: "Segoe UI Variable", "Segoe UI", system-ui, sans-serif;
                    font-size: 14px;
                }
                QTabWidget::pane {
                    border: none;
                    background-color: transparent;
                }
                QTabBar::tab {
                    background-color: transparent;
                    color: #8b949e;
                    padding: 12px 24px;
                    margin-right: 4px;
                    border: none;
                    border-bottom: 2px solid transparent;
                    font-size: 14px;
                    font-weight: 400;
                }
                QTabBar::tab:selected {
                    color: #c9d1d9;
                    border-bottom: 2px solid #1f6feb;
                }
                QTabBar::tab:hover:!selected {
                    color: #c9d1d9;
                    background-color: rgba(255, 255, 255, 0.05);
                }
                QListWidget {
                    background-color: #161b22;
                    color: #c9d1d9;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    padding: 4px;
                    font-size: 14px;
                    outline: none;
                }
                QListWidget::item {
                    background-color: #0d1117;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    padding: 14px 16px;
                    margin: 4px 2px;
                }
                QListWidget::item:selected {
                    background-color: rgba(31, 111, 235, 0.15);
                    border: 1px solid #1f6feb;
                    color: #c9d1d9;
                }
                QListWidget::item:hover:!selected {
                    background-color: #161b22;
                    border-color: #484f58;
                }
                QPushButton {
                    background-color: #21262d;
                    color: #c9d1d9;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #30363d;
                    border-color: #8b949e;
                }
                QPushButton:pressed {
                    background-color: #161b22;
                }
                QPushButton#primary {
                    background-color: #238636;
                    color: #ffffff;
                    border: 1px solid #238636;
                }
                QPushButton#primary:hover {
                    background-color: #2ea043;
                }
                QPushButton#primary:pressed {
                    background-color: #196c2e;
                }
                QPushButton#danger {
                    background-color: #da3633;
                    color: #ffffff;
                    border: 1px solid #da3633;
                }
                QPushButton#danger:hover {
                    background-color: #f85149;
                }
                QPushButton#danger:pressed {
                    background-color: #b62324;
                }
                QRadioButton {
                    color: #c9d1d9;
                    spacing: 12px;
                    font-size: 14px;
                    padding: 8px 4px;
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 8px;
                    border: 1px solid #30363d;
                    background-color: #0d1117;
                }
                QRadioButton::indicator:checked {
                    border: 5px solid #1f6feb;
                    background-color: #0d1117;
                }
                QRadioButton::indicator:hover {
                    border-color: #1f6feb;
                }
                QCheckBox {
                    color: #c9d1d9;
                    spacing: 12px;
                    font-size: 14px;
                    padding: 8px 4px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 3px;
                    border: 1px solid #30363d;
                    background-color: #0d1117;
                }
                QCheckBox::indicator:checked {
                    background-color: #238636;
                    border: 1px solid #238636;
                }
                QCheckBox::indicator:hover {
                    border-color: #238636;
                }
                QPushButton#category_button {
                    background-color: transparent;
                    color: #8b949e;
                    border: none;
                    border-radius: 0;
                    padding: 16px 20px;
                    text-align: left;
                    font-size: 14px;
                }
                QPushButton#category_button:hover {
                    background-color: #21262d;
                    color: #c9d1d9;
                }
                QPushButton#category_button:checked {
                    background-color: rgba(31, 111, 235, 0.15);
                    color: #58a6ff;
                    border-left: 3px solid #1f6feb;
                }
                QWidget#settings_sidebar {
                    background-color: #161b22;
                    border-right: 1px solid #30363d;
                }
                QSlider::groove:horizontal {
                    background-color: #30363d;
                    height: 6px;
                    border-radius: 3px;
                }
                QSlider::sub-page:horizontal {
                    background-color: #1f6feb;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background-color: #c9d1d9;
                    border: 2px solid #1f6feb;
                    width: 16px;
                    height: 16px;
                    margin: -6px 0;
                    border-radius: 8px;
                }
                QSlider::handle:horizontal:hover {
                    background-color: #1f6feb;
                }
                QTextEdit {
                    background-color: #161b22;
                    color: #c9d1d9;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    padding: 16px;
                    font-size: 14px;
                    line-height: 1.6;
                    selection-background-color: rgba(31, 111, 235, 0.4);
                }
                QLabel {
                    color: #c9d1d9;
                    background-color: transparent;
                }
                QLabel#title {
                    font-size: 32px;
                    font-weight: 600;
                    color: #c9d1d9;
                }
                QLabel#subtitle {
                    font-size: 14px;
                    color: #8b949e;
                }
                QLabel#section {
                    font-size: 18px;
                    font-weight: 600;
                    color: #c9d1d9;
                    padding: 12px 0 8px 0;
                }
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                QLineEdit {
                    background-color: #0d1117;
                    color: #c9d1d9;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    padding: 10px 14px;
                    font-size: 14px;
                    selection-background-color: rgba(31, 111, 235, 0.4);
                }
                QLineEdit:focus {
                    border: 2px solid #1f6feb;
                    padding: 9px 13px;
                }
                QSplitter::handle {
                    background-color: #30363d;
                    width: 1px;
                }
                QFrame[frameShape="4"] {
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    background-color: #161b22;
                }
            """)
        else:
            # GitHub Light Theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #ffffff;
                }
                QWidget {
                    background-color: #ffffff;
                    color: #24292f;
                    font-family: "Segoe UI Variable", "Segoe UI", system-ui, sans-serif;
                    font-size: 14px;
                }
                QTabWidget::pane {
                    border: none;
                    background-color: transparent;
                }
                QTabBar::tab {
                    background-color: transparent;
                    color: #57606a;
                    padding: 12px 24px;
                    margin-right: 4px;
                    border: none;
                    border-bottom: 2px solid transparent;
                    font-size: 14px;
                    font-weight: 400;
                }
                QTabBar::tab:selected {
                    color: #24292f;
                    border-bottom: 2px solid #0969da;
                }
                QTabBar::tab:hover:!selected {
                    color: #24292f;
                    background-color: rgba(0, 0, 0, 0.03);
                }
                QListWidget {
                    background-color: #f6f8fa;
                    color: #24292f;
                    border: 1px solid #d0d7de;
                    border-radius: 6px;
                    padding: 4px;
                    font-size: 14px;
                    outline: none;
                }
                QListWidget::item {
                    background-color: #ffffff;
                    border: 1px solid #d0d7de;
                    border-radius: 6px;
                    padding: 14px 16px;
                    margin: 4px 2px;
                }
                QListWidget::item:selected {
                    background-color: rgba(9, 105, 218, 0.1);
                    border: 1px solid #0969da;
                    color: #24292f;
                }
                QListWidget::item:hover:!selected {
                    background-color: #f6f8fa;
                    border-color: #afb8c1;
                }
                QPushButton {
                    background-color: #f6f8fa;
                    color: #24292f;
                    border: 1px solid #d0d7de;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #f3f4f6;
                    border-color: #afb8c1;
                }
                QPushButton:pressed {
                    background-color: #ebecf0;
                }
                QPushButton#primary {
                    background-color: #1a7f37;
                    color: #ffffff;
                    border: 1px solid #1a7f37;
                }
                QPushButton#primary:hover {
                    background-color: #2c974b;
                }
                QPushButton#primary:pressed {
                    background-color: #116329;
                }
                QPushButton#danger {
                    background-color: #cf222e;
                    color: #ffffff;
                    border: 1px solid #cf222e;
                }
                QPushButton#danger:hover {
                    background-color: #a40e26;
                }
                QPushButton#danger:pressed {
                    background-color: #82071e;
                }
                QRadioButton {
                    color: #24292f;
                    spacing: 12px;
                    font-size: 14px;
                    padding: 8px 4px;
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 8px;
                    border: 1px solid #d0d7de;
                    background-color: #ffffff;
                }
                QRadioButton::indicator:checked {
                    border: 5px solid #0969da;
                    background-color: #ffffff;
                }
                QRadioButton::indicator:hover {
                    border-color: #0969da;
                }
                QCheckBox {
                    color: #24292f;
                    spacing: 12px;
                    font-size: 14px;
                    padding: 8px 4px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 3px;
                    border: 1px solid #d0d7de;
                    background-color: #ffffff;
                }
                QCheckBox::indicator:checked {
                    background-color: #1a7f37;
                    border: 1px solid #1a7f37;
                }
                QCheckBox::indicator:hover {
                    border-color: #1a7f37;
                }
                QPushButton#category_button {
                    background-color: transparent;
                    color: #57606a;
                    border: none;
                    border-radius: 0;
                    padding: 16px 20px;
                    text-align: left;
                    font-size: 14px;
                }
                QPushButton#category_button:hover {
                    background-color: rgba(0, 0, 0, 0.03);
                    color: #24292f;
                }
                QPushButton#category_button:checked {
                    background-color: rgba(9, 105, 218, 0.1);
                    color: #0969da;
                    border-left: 3px solid #0969da;
                }
                QWidget#settings_sidebar {
                    background-color: #f6f8fa;
                    border-right: 1px solid #d0d7de;
                }
                QSlider::groove:horizontal {
                    background-color: #d0d7de;
                    height: 6px;
                    border-radius: 3px;
                }
                QSlider::sub-page:horizontal {
                    background-color: #0969da;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background-color: #ffffff;
                    border: 2px solid #0969da;
                    width: 16px;
                    height: 16px;
                    margin: -6px 0;
                    border-radius: 8px;
                }
                QSlider::handle:horizontal:hover {
                    background-color: #0969da;
                }
                QTextEdit {
                    background-color: #ffffff;
                    color: #24292f;
                    border: 1px solid #d0d7de;
                    border-radius: 6px;
                    padding: 16px;
                    font-size: 14px;
                    line-height: 1.6;
                    selection-background-color: rgba(9, 105, 218, 0.3);
                }
                QLabel {
                    color: #24292f;
                    background-color: transparent;
                }
                QLabel#title {
                    font-size: 32px;
                    font-weight: 600;
                    color: #24292f;
                }
                QLabel#subtitle {
                    font-size: 14px;
                    color: #57606a;
                }
                QLabel#section {
                    font-size: 18px;
                    font-weight: 600;
                    color: #24292f;
                    padding: 12px 0 8px 0;
                }
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                QLineEdit {
                    background-color: #ffffff;
                    color: #24292f;
                    border: 1px solid #d0d7de;
                    border-radius: 6px;
                    padding: 10px 14px;
                    font-size: 14px;
                    selection-background-color: rgba(0, 120, 212, 0.3);
                }
                QLineEdit:focus {
                    border: 2px solid #0969da;
                    padding: 9px 13px;
                }
                QSplitter::handle {
                    background-color: #d0d7de;
                    width: 1px;
                }
                QFrame[frameShape="4"] {
                    border: 1px solid #d0d7de;
                    border-radius: 6px;
                    background-color: #f6f8fa;
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

        # Preview header with Edit Mode toggle
        preview_header = QHBoxLayout()
        preview_title = QLabel("Preview")
        preview_title.setObjectName("section")
        preview_header.addWidget(preview_title)
        preview_header.addStretch()

        self.edit_mode_btn = QPushButton("Edit Layout")
        self.edit_mode_btn.setCheckable(True)
        self.edit_mode_btn.setMinimumHeight(32)
        self.edit_mode_btn.setToolTip("Enable edit mode to drag monitors and change layout")
        self.edit_mode_btn.clicked.connect(self.toggle_edit_mode)
        preview_header.addWidget(self.edit_mode_btn)

        right_layout.addLayout(preview_header)

        # Monitor preview
        self.monitor_preview = MonitorPreviewWidget()
        self.monitor_preview.config_changed.connect(self.on_preview_config_changed)
        self.monitor_preview.primary_changed.connect(self.on_preview_primary_changed)
        right_layout.addWidget(self.monitor_preview, stretch=1)

        # Edit mode action buttons (hidden by default)
        self.edit_actions_widget = QWidget()
        edit_actions_layout = QHBoxLayout(self.edit_actions_widget)
        edit_actions_layout.setContentsMargins(0, 8, 0, 0)
        edit_actions_layout.setSpacing(8)

        self.apply_layout_btn = QPushButton("Apply Layout")
        self.apply_layout_btn.setObjectName("primary")
        self.apply_layout_btn.setMinimumHeight(36)
        self.apply_layout_btn.setToolTip("Apply the modified layout to your displays")
        self.apply_layout_btn.clicked.connect(self.apply_edited_layout)
        edit_actions_layout.addWidget(self.apply_layout_btn)

        self.save_as_preset_btn = QPushButton("Save as New Preset")
        self.save_as_preset_btn.setMinimumHeight(36)
        self.save_as_preset_btn.setToolTip("Save the modified layout as a new preset")
        self.save_as_preset_btn.clicked.connect(self.save_edited_as_preset)
        edit_actions_layout.addWidget(self.save_as_preset_btn)

        self.reset_layout_btn = QPushButton("Reset")
        self.reset_layout_btn.setMinimumHeight(36)
        self.reset_layout_btn.setToolTip("Reset layout to original positions")
        self.reset_layout_btn.clicked.connect(self.reset_edited_layout)
        edit_actions_layout.addWidget(self.reset_layout_btn)

        edit_actions_layout.addStretch()
        self.edit_actions_widget.hide()
        right_layout.addWidget(self.edit_actions_widget)

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
        # Main horizontal layout: categories on left, settings on right
        main_layout = QHBoxLayout(self.settings_tab)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left sidebar - Categories
        sidebar = QWidget()
        sidebar.setObjectName("settings_sidebar")
        sidebar.setMinimumWidth(200)
        sidebar.setMaximumWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Category buttons
        self.category_buttons = []
        categories = ["General", "Notifications", "Behavior", "Advanced"]

        for category in categories:
            btn = QPushButton(category)
            btn.setObjectName("category_button")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, c=category: self.switch_settings_category(c))
            sidebar_layout.addWidget(btn)
            self.category_buttons.append(btn)

        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)

        # Right side - Settings content
        self.settings_stack = QStackedWidget()
        main_layout.addWidget(self.settings_stack)

        # Create each category page
        self.setup_general_settings()
        self.setup_notification_settings()
        self.setup_behavior_settings()
        self.setup_advanced_settings()

        # Select first category by default
        self.category_buttons[0].setChecked(True)
        self.settings_stack.setCurrentIndex(0)

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

        # Restore selection - either from current or from settings
        restore_name = current_name
        if not restore_name and self.settings.remember_last_preset:
            restore_name = self.settings.last_selected_preset

        if restore_name:
            items = self.preset_list.findItems(restore_name, Qt.MatchFlag.MatchExactly)
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

        # Save last selected preset if enabled
        if self.settings.remember_last_preset:
            self.settings.last_selected_preset = name
            self.settings.save()

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

        # Exit edit mode when switching presets
        if self.edit_mode_btn.isChecked():
            self.edit_mode_btn.setChecked(False)
            self.toggle_edit_mode()

    def toggle_edit_mode(self):
        """Toggle edit mode for monitor preview"""
        enabled = self.edit_mode_btn.isChecked()
        self.monitor_preview.set_edit_mode(enabled)
        self.edit_actions_widget.setVisible(enabled)

        if enabled:
            self.edit_mode_btn.setText("Exit Edit")
            # Store original config for reset
            self._original_config = self.monitor_preview.config_data
        else:
            self.edit_mode_btn.setText("Edit Layout")

    def on_preview_config_changed(self, modified_config):
        """Called when monitors are moved in edit mode"""
        # Config has been modified, enable apply button
        pass

    def on_preview_primary_changed(self, monitor_idx):
        """Called when primary monitor is changed in edit mode"""
        pass

    def apply_edited_layout(self):
        """Apply the edited layout to displays"""
        modified_config = self.monitor_preview.get_modified_config()
        if not modified_config:
            return

        try:
            result = self.display.apply(modified_config['config'])
            if result == 0:
                if self.settings.notify_preset_applied:
                    QMessageBox.information(
                        self,
                        "Layout Applied",
                        "The modified display layout has been applied successfully."
                    )
                # Exit edit mode
                self.edit_mode_btn.setChecked(False)
                self.toggle_edit_mode()
            else:
                if self.settings.show_error_messages:
                    QMessageBox.critical(
                        self,
                        "Failed to Apply Layout",
                        f"Could not apply the modified layout.\nError code: {result}"
                    )
        except Exception as e:
            if self.settings.show_error_messages:
                QMessageBox.critical(self, "Error", f"Failed to apply layout:\n{e}")

    def save_edited_as_preset(self):
        """Save the edited layout as a new preset"""
        modified_config = self.monitor_preview.get_modified_config()
        if not modified_config:
            return

        name, ok = QInputDialog.getText(
            self,
            "Save Modified Layout",
            "Enter a name for this preset:"
        )
        if ok and name and name.strip():
            try:
                self.presets.save(name.strip(), modified_config['config'])
                if self.settings.notify_preset_saved:
                    QMessageBox.information(
                        self,
                        "Preset Saved",
                        f"Layout saved as preset '{name}'."
                    )
                self.refresh_preset_list()
                # Exit edit mode
                self.edit_mode_btn.setChecked(False)
                self.toggle_edit_mode()
            except Exception as e:
                if self.settings.show_error_messages:
                    QMessageBox.critical(self, "Error", f"Failed to save preset:\n{e}")

    def reset_edited_layout(self):
        """Reset the layout to original positions"""
        if hasattr(self, '_original_config') and self._original_config:
            self.monitor_preview.set_config(self._original_config)

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

            if self.settings.notify_hotkey_changed:
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
            if self.settings.show_error_messages:
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
                if self.settings.notify_preset_applied:
                    QMessageBox.information(
                        self,
                        "Display Configuration Applied",
                        f"Preset '{name}' has been applied successfully.\n\n"
                        f"Your monitors have been configured according to the saved settings."
                    )
                # Minimize window if enabled
                if self.settings.minimize_after_apply:
                    self.hide()
            else:
                if self.settings.show_error_messages:
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
                if self.settings.notify_preset_saved:
                    QMessageBox.information(
                        self,
                        "Preset Saved Successfully",
                        f"Preset '{name}' has been saved.\n\n"
                        f"You can now apply this configuration anytime by selecting it from the list."
                    )
                self.refresh_preset_list()
            except Exception as e:
                if self.settings.show_error_messages:
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
                if self.settings.notify_preset_renamed:
                    QMessageBox.information(
                        self,
                        "Preset Renamed",
                        f"Preset has been renamed from '{old_name}' to '{new_name}'."
                    )
                self.refresh_preset_list()
            except Exception as e:
                if self.settings.show_error_messages:
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

        # Show confirmation dialog if enabled
        confirm = True
        if self.settings.confirm_preset_delete:
            reply = QMessageBox.question(
                self,
                "Delete Preset",
                f"Are you sure you want to delete preset '{name}'?\n\n"
                f"This action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            confirm = reply == QMessageBox.StandardButton.Yes

        if confirm:
            try:
                self.presets.delete(name)
                if self.settings.notify_preset_deleted:
                    QMessageBox.information(
                        self,
                        "Preset Deleted",
                        f"Preset '{name}' has been permanently deleted."
                    )
                self.refresh_preset_list()
            except Exception as e:
                if self.settings.show_error_messages:
                    QMessageBox.critical(self, "Error", f"Failed to delete preset:\n{e}")

    def change_theme(self, mode):
        # Uncheck other theme buttons
        for btn_mode, btn in self.theme_buttons:
            if btn_mode != mode:
                btn.setChecked(False)
            else:
                btn.setChecked(True)

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

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key.Key_Escape and self.settings.esc_to_minimize:
            self.hide()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if event.spontaneous():
            # User clicked X button - just hide
            event.ignore()
            self.hide()
        else:
            # App is closing
            self.hotkey_manager.stop_listening()
            event.accept()

    def switch_settings_category(self, category):
        """Switch between settings categories"""
        category_map = {
            "General": 0,
            "Notifications": 1,
            "Behavior": 2,
            "Advanced": 3
        }

        index = category_map.get(category, 0)
        self.settings_stack.setCurrentIndex(index)

        # Update button states
        for i, btn in enumerate(self.category_buttons):
            btn.setChecked(i == index)

    def create_help_label(self, tooltip_text):
        """Create a help icon (?) with tooltip - shows instantly on hover"""
        from PyQt6.QtWidgets import QToolTip

        class HoverHelpLabel(QLabel):
            def __init__(self, text, tooltip, parent=None):
                super().__init__(text, parent)
                self._tooltip = tooltip

            def enterEvent(self, event):
                # Show tooltip immediately on hover (no delay)
                QToolTip.showText(self.mapToGlobal(self.rect().bottomLeft()), self._tooltip, self)
                super().enterEvent(event)

        help_label = HoverHelpLabel("?", tooltip_text)

        # GitHub themed colors
        if self.settings.dark_mode:
            help_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(88, 166, 255, 0.15);
                    color: #58a6ff;
                    border: 1px solid #58a6ff;
                    border-radius: 9px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 2px;
                    min-width: 16px;
                    max-width: 16px;
                    min-height: 16px;
                    max-height: 16px;
                }
                QLabel:hover {
                    background-color: rgba(88, 166, 255, 0.3);
                }
            """)
        else:
            help_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(9, 105, 218, 0.1);
                    color: #0969da;
                    border: 1px solid #0969da;
                    border-radius: 9px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 2px;
                    min-width: 16px;
                    max-width: 16px;
                    min-height: 16px;
                    max-height: 16px;
                }
                QLabel:hover {
                    background-color: rgba(9, 105, 218, 0.2);
                }
            """)

        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return help_label

    def create_setting_row(self, widget, help_text):
        """Create a row with widget and help icon"""
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(widget)
        row.addWidget(self.create_help_label(help_text))
        row.addStretch()
        return row

    def setup_general_settings(self):
        """General settings page"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)

        # Header
        title = QLabel("General Settings")
        title.setObjectName("section")
        layout.addWidget(title)

        # Theme Section
        theme_label = QLabel("Theme")
        theme_label.setObjectName("subtitle")
        layout.addWidget(theme_label)

        # Theme selector with card-style buttons
        theme_container = QWidget()
        theme_layout = QHBoxLayout(theme_container)
        theme_layout.setContentsMargins(0, 8, 0, 0)
        theme_layout.setSpacing(12)

        self.theme_buttons = []
        theme_options = [("system", "System"), ("dark", "Dark"), ("light", "Light")]

        # Get theme colors for styling
        is_dark = self.settings.dark_mode
        if is_dark:
            card_bg = "#161b22"
            card_bg_hover = "#21262d"
            card_bg_selected = "rgba(31, 111, 235, 0.15)"
            card_border = "#30363d"
            card_border_selected = "#1f6feb"
            text_primary = "#c9d1d9"
        else:
            card_bg = "#f6f8fa"
            card_bg_hover = "#f3f4f6"
            card_bg_selected = "rgba(9, 105, 218, 0.1)"
            card_border = "#d0d7de"
            card_border_selected = "#0969da"
            text_primary = "#24292f"

        for mode, label in theme_options:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setMinimumHeight(44)
            btn.setMinimumWidth(100)

            # Create layout for button content
            btn_layout = QVBoxLayout(btn)
            btn_layout.setContentsMargins(16, 10, 16, 10)

            title_label = QLabel(label)
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_label.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {text_primary}; background: transparent;")

            btn_layout.addWidget(title_label)

            # Style the button
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {card_bg};
                    border: 1px solid {card_border};
                    border-radius: 8px;
                }}
                QPushButton:hover {{
                    background-color: {card_bg_hover};
                    border-color: {card_border_selected};
                }}
                QPushButton:checked {{
                    background-color: {card_bg_selected};
                    border: 2px solid {card_border_selected};
                }}
            """)

            # Check if this is the current theme
            if self.settings.theme_mode == mode:
                btn.setChecked(True)

            btn.clicked.connect(lambda checked, m=mode: self.change_theme(m) if checked else None)
            theme_layout.addWidget(btn)
            self.theme_buttons.append((mode, btn))

        theme_layout.addStretch()
        layout.addWidget(theme_container)

        layout.addSpacing(16)

        # Startup options
        startup_label = QLabel("Startup")
        startup_label.setObjectName("subtitle")
        layout.addWidget(startup_label)

        self.start_with_windows_cb = QCheckBox("Start with Windows")
        self.start_with_windows_cb.setChecked(autostart.is_enabled())
        self.start_with_windows_cb.stateChanged.connect(self.on_start_with_windows_changed)
        layout.addLayout(self.create_setting_row(
            self.start_with_windows_cb,
            "Automatically start Display Presets when Windows boots up"
        ))

        self.start_minimized_cb = QCheckBox("Start minimized to tray")
        self.start_minimized_cb.setChecked(self.settings.start_minimized)
        self.start_minimized_cb.stateChanged.connect(self.on_start_minimized_changed)
        layout.addLayout(self.create_setting_row(
            self.start_minimized_cb,
            "Start the application in the system tray without opening the main window"
        ))

        layout.addSpacing(16)

        # Preset options
        preset_label = QLabel("Presets")
        preset_label.setObjectName("subtitle")
        layout.addWidget(preset_label)

        self.remember_preset_cb = QCheckBox("Remember last selected preset")
        self.remember_preset_cb.setChecked(self.settings.remember_last_preset)
        self.remember_preset_cb.stateChanged.connect(self.on_remember_preset_changed)
        layout.addLayout(self.create_setting_row(
            self.remember_preset_cb,
            "When opening the app, automatically select the last preset you were viewing"
        ))

        layout.addSpacing(16)

        # Data folder
        data_label = QLabel("Data Location")
        data_label.setObjectName("subtitle")
        layout.addWidget(data_label)

        folder_label = QLabel(str(get_app_dir()))
        folder_label.setWordWrap(True)
        layout.addWidget(folder_label)

        open_folder_btn = QPushButton("Open in Explorer")
        open_folder_btn.setMinimumHeight(36)
        open_folder_btn.setMaximumWidth(200)
        open_folder_btn.clicked.connect(self.open_data_folder)
        layout.addWidget(open_folder_btn)

        layout.addStretch()
        scroll.setWidget(content)
        self.settings_stack.addWidget(scroll)

    def setup_notification_settings(self):
        """Notification settings page"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)

        # Header
        title = QLabel("Notification Settings")
        title.setObjectName("section")
        layout.addWidget(title)

        subtitle = QLabel("Choose which notifications to display")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # Success notifications
        success_label = QLabel("Success Notifications")
        success_label.setObjectName("subtitle")
        layout.addWidget(success_label)

        self.notify_applied_cb = QCheckBox("Show notification when preset is applied")
        self.notify_applied_cb.setChecked(self.settings.notify_preset_applied)
        self.notify_applied_cb.stateChanged.connect(self.on_notify_applied_changed)
        layout.addLayout(self.create_setting_row(
            self.notify_applied_cb,
            "Display a popup notification when you successfully apply a display preset"
        ))

        self.notify_saved_cb = QCheckBox("Show notification when preset is saved")
        self.notify_saved_cb.setChecked(self.settings.notify_preset_saved)
        self.notify_saved_cb.stateChanged.connect(self.on_notify_saved_changed)
        layout.addLayout(self.create_setting_row(
            self.notify_saved_cb,
            "Display a popup notification when you save a new preset"
        ))

        self.notify_renamed_cb = QCheckBox("Show notification when preset is renamed")
        self.notify_renamed_cb.setChecked(self.settings.notify_preset_renamed)
        self.notify_renamed_cb.stateChanged.connect(self.on_notify_renamed_changed)
        layout.addLayout(self.create_setting_row(
            self.notify_renamed_cb,
            "Display a popup notification when you rename a preset"
        ))

        self.notify_deleted_cb = QCheckBox("Show notification when preset is deleted")
        self.notify_deleted_cb.setChecked(self.settings.notify_preset_deleted)
        self.notify_deleted_cb.stateChanged.connect(self.on_notify_deleted_changed)
        layout.addLayout(self.create_setting_row(
            self.notify_deleted_cb,
            "Display a popup notification when you delete a preset"
        ))

        self.notify_hotkey_cb = QCheckBox("Show notification when hotkey is assigned/removed")
        self.notify_hotkey_cb.setChecked(self.settings.notify_hotkey_changed)
        self.notify_hotkey_cb.stateChanged.connect(self.on_notify_hotkey_changed)
        layout.addLayout(self.create_setting_row(
            self.notify_hotkey_cb,
            "Display a popup notification when you assign or remove a hotkey from a preset"
        ))

        layout.addSpacing(16)

        # Confirmation dialogs
        confirm_label = QLabel("Confirmation Dialogs")
        confirm_label.setObjectName("subtitle")
        layout.addWidget(confirm_label)

        self.confirm_delete_cb = QCheckBox("Ask for confirmation before deleting presets")
        self.confirm_delete_cb.setChecked(self.settings.confirm_preset_delete)
        self.confirm_delete_cb.stateChanged.connect(self.on_confirm_delete_changed)
        layout.addLayout(self.create_setting_row(
            self.confirm_delete_cb,
            "Show a confirmation dialog before permanently deleting a preset to prevent accidental deletion"
        ))

        layout.addStretch()
        scroll.setWidget(content)
        self.settings_stack.addWidget(scroll)

    def setup_behavior_settings(self):
        """Behavior settings page"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)

        # Header
        title = QLabel("Behavior Settings")
        title.setObjectName("section")
        layout.addWidget(title)

        subtitle = QLabel("Customize application behavior")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # Window behavior
        window_label = QLabel("Window Behavior")
        window_label.setObjectName("subtitle")
        layout.addWidget(window_label)

        self.minimize_after_apply_cb = QCheckBox("Minimize window after applying preset")
        self.minimize_after_apply_cb.setChecked(self.settings.minimize_after_apply)
        self.minimize_after_apply_cb.stateChanged.connect(self.on_minimize_after_apply_changed)
        layout.addLayout(self.create_setting_row(
            self.minimize_after_apply_cb,
            "Automatically minimize the window to system tray after successfully applying a preset"
        ))

        self.esc_to_minimize_cb = QCheckBox("Press ESC to minimize window")
        self.esc_to_minimize_cb.setChecked(self.settings.esc_to_minimize)
        self.esc_to_minimize_cb.stateChanged.connect(self.on_esc_to_minimize_changed)
        layout.addLayout(self.create_setting_row(
            self.esc_to_minimize_cb,
            "Allow pressing the ESC key to quickly minimize the window to system tray"
        ))

        layout.addStretch()
        scroll.setWidget(content)
        self.settings_stack.addWidget(scroll)

    def setup_advanced_settings(self):
        """Advanced settings page"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)

        # Header
        title = QLabel("Advanced Settings")
        title.setObjectName("section")
        layout.addWidget(title)

        subtitle = QLabel("Advanced options for power users")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # Font size
        font_header = QHBoxLayout()
        font_label = QLabel("Font Size")
        font_label.setObjectName("subtitle")
        font_header.addWidget(font_label)
        font_header.addWidget(self.create_help_label(
            "Adjust the size of all text in the application. Restart required for full effect."
        ))
        font_header.addStretch()
        layout.addLayout(font_header)

        # Font size slider container
        font_container = QWidget()
        font_container_layout = QVBoxLayout(font_container)
        font_container_layout.setContentsMargins(0, 0, 0, 0)
        font_container_layout.setSpacing(8)

        # Current value - large and centered
        font_value_label = QLabel(f"{self.settings.font_size_multiplier:.1f}x")
        font_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font_value_label.setStyleSheet("font-size: 24px; font-weight: 600; padding: 8px;")
        font_container_layout.addWidget(font_value_label)

        # Slider with min/max labels
        slider_row = QHBoxLayout()
        slider_row.setSpacing(12)

        min_label = QLabel("Small\n0.8x")
        min_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        min_label.setStyleSheet("font-size: 11px; color: #888;")

        font_slider = QSlider(Qt.Orientation.Horizontal)
        font_slider.setMinimum(8)  # 0.8x
        font_slider.setMaximum(15)  # 1.5x
        font_slider.setValue(int(self.settings.font_size_multiplier * 10))
        font_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        font_slider.setTickInterval(2)
        font_slider.valueChanged.connect(lambda v: self.on_font_size_changed(v, font_value_label))

        max_label = QLabel("Large\n1.5x")
        max_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        max_label.setStyleSheet("font-size: 11px; color: #888;")

        slider_row.addWidget(min_label)
        slider_row.addWidget(font_slider, 1)
        slider_row.addWidget(max_label)

        font_container_layout.addLayout(slider_row)
        layout.addWidget(font_container)

        layout.addSpacing(16)

        # Window size
        window_header = QHBoxLayout()
        window_label = QLabel("Window Size")
        window_label.setObjectName("subtitle")
        window_header.addWidget(window_label)
        window_header.addWidget(self.create_help_label(
            "Set the default window size (width × height in pixels). Takes effect on next app start."
        ))
        window_header.addStretch()
        layout.addLayout(window_header)

        size_layout = QHBoxLayout()
        size_layout.setSpacing(16)

        width_input = QLineEdit(str(self.settings.window_width))
        width_input.setPlaceholderText("Width (1000-2000)")
        width_input.setMaximumWidth(150)
        width_input.textChanged.connect(lambda v: self.on_window_width_changed(v))

        height_input = QLineEdit(str(self.settings.window_height))
        height_input.setPlaceholderText("Height (650-1500)")
        height_input.setMaximumWidth(150)
        height_input.textChanged.connect(lambda v: self.on_window_height_changed(v))

        size_layout.addWidget(QLabel("Width:"))
        size_layout.addWidget(width_input)
        size_layout.addWidget(QLabel("Height:"))
        size_layout.addWidget(height_input)
        size_layout.addStretch()

        layout.addLayout(size_layout)

        layout.addSpacing(16)

        # Import/Export
        backup_header = QHBoxLayout()
        import_export_label = QLabel("Settings Backup")
        import_export_label.setObjectName("subtitle")
        backup_header.addWidget(import_export_label)
        backup_header.addWidget(self.create_help_label(
            "Export your settings to a JSON file for backup, or import settings from another computer"
        ))
        backup_header.addStretch()
        layout.addLayout(backup_header)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)

        export_btn = QPushButton("Export Settings")
        export_btn.setMinimumHeight(36)
        export_btn.setMaximumWidth(150)
        export_btn.clicked.connect(self.export_settings)

        import_btn = QPushButton("Import Settings")
        import_btn.setMinimumHeight(36)
        import_btn.setMaximumWidth(150)
        import_btn.clicked.connect(self.import_settings)

        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(import_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        layout.addSpacing(16)

        # Reset
        reset_header = QHBoxLayout()
        reset_label = QLabel("Reset Settings")
        reset_label.setObjectName("subtitle")
        reset_header.addWidget(reset_label)
        reset_header.addWidget(self.create_help_label(
            "Reset all settings to their default values. This action cannot be undone. Presets are not affected."
        ))
        reset_header.addStretch()
        layout.addLayout(reset_header)

        reset_btn = QPushButton("Reset All Settings to Defaults")
        reset_btn.setMinimumHeight(36)
        reset_btn.setMaximumWidth(250)
        reset_btn.setObjectName("danger")
        reset_btn.clicked.connect(self.reset_all_settings)
        layout.addWidget(reset_btn)

        layout.addStretch()
        scroll.setWidget(content)
        self.settings_stack.addWidget(scroll)

    # Settings callbacks
    def on_start_with_windows_changed(self, state):
        try:
            enabled = state == Qt.CheckState.Checked.value
            if enabled != autostart.is_enabled():
                autostart.toggle()
            self.settings.start_with_windows = enabled
            self.settings.save()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to change autostart:\n{e}")

    def on_start_minimized_changed(self, state):
        self.settings.start_minimized = state == Qt.CheckState.Checked.value
        self.settings.save()

    def on_remember_preset_changed(self, state):
        self.settings.remember_last_preset = state == Qt.CheckState.Checked.value
        self.settings.save()

    def on_notify_applied_changed(self, state):
        self.settings.notify_preset_applied = state == Qt.CheckState.Checked.value
        self.settings.save()

    def on_notify_saved_changed(self, state):
        self.settings.notify_preset_saved = state == Qt.CheckState.Checked.value
        self.settings.save()

    def on_notify_renamed_changed(self, state):
        self.settings.notify_preset_renamed = state == Qt.CheckState.Checked.value
        self.settings.save()

    def on_notify_deleted_changed(self, state):
        self.settings.notify_preset_deleted = state == Qt.CheckState.Checked.value
        self.settings.save()

    def on_notify_hotkey_changed(self, state):
        self.settings.notify_hotkey_changed = state == Qt.CheckState.Checked.value
        self.settings.save()

    def on_confirm_delete_changed(self, state):
        self.settings.confirm_preset_delete = state == Qt.CheckState.Checked.value
        self.settings.save()

    def on_minimize_after_apply_changed(self, state):
        self.settings.minimize_after_apply = state == Qt.CheckState.Checked.value
        self.settings.save()

    def on_esc_to_minimize_changed(self, state):
        self.settings.esc_to_minimize = state == Qt.CheckState.Checked.value
        self.settings.save()

    def on_font_size_changed(self, value, label):
        multiplier = value / 10.0
        label.setText(f"{multiplier:.1f}x")
        self.settings.font_size_multiplier = multiplier
        self.settings.save()

    def on_window_width_changed(self, value):
        try:
            width = int(value)
            if 1000 <= width <= 2000:
                self.settings.window_width = width
                self.settings.save()
        except ValueError:
            pass

    def on_window_height_changed(self, value):
        try:
            height = int(value)
            if 650 <= height <= 1500:
                self.settings.window_height = height
                self.settings.save()
        except ValueError:
            pass

    def export_settings(self):
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Settings",
            "display_presets_settings.json",
            "JSON Files (*.json)"
        )
        if file_path:
            try:
                import json
                with open(file_path, 'w') as f:
                    json.dump(self.settings.export_to_dict(), f, indent=2)
                QMessageBox.information(self, "Export Successful", f"Settings exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export settings:\n{e}")

    def import_settings(self):
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Settings",
            "",
            "JSON Files (*.json)"
        )
        if file_path:
            try:
                import json
                with open(file_path, 'r') as f:
                    data = json.load(f)
                self.settings.import_from_dict(data)
                QMessageBox.information(
                    self,
                    "Import Successful",
                    "Settings imported successfully.\nPlease restart the application for changes to take effect."
                )
            except Exception as e:
                QMessageBox.critical(self, "Import Failed", f"Failed to import settings:\n{e}")

    def reset_all_settings(self):
        reply = QMessageBox.question(
            self,
            "Reset All Settings",
            "Are you sure you want to reset all settings to default values?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings.reset_to_defaults()
            QMessageBox.information(
                self,
                "Settings Reset",
                "All settings have been reset to defaults.\nPlease restart the application for changes to take effect."
            )
