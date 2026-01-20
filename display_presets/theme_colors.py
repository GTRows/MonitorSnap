# GitHub Theme Colors for Display Presets
# All colors should be referenced from here

class GitHubDark:
    """GitHub Dark Theme Colors"""
    # Backgrounds
    BG_PRIMARY = "#0d1117"
    BG_SECONDARY = "#161b22"
    BG_TERTIARY = "#21262d"

    # Borders
    BORDER_DEFAULT = "#30363d"
    BORDER_MUTED = "#21262d"
    BORDER_EMPHASIS = "#484f58"

    # Text
    TEXT_PRIMARY = "#c9d1d9"
    TEXT_SECONDARY = "#8b949e"
    TEXT_MUTED = "#6e7681"

    # Accent colors
    ACCENT_BLUE = "#1f6feb"
    ACCENT_BLUE_LIGHT = "#58a6ff"

    # Semantic colors
    SUCCESS = "#238636"
    SUCCESS_EMPHASIS = "#2ea043"
    DANGER = "#da3633"
    DANGER_EMPHASIS = "#f85149"
    WARNING = "#d29922"

    # Interactive states
    HOVER_BG = "#21262d"
    SELECTED_BG = "rgba(31, 111, 235, 0.15)"


class GitHubLight:
    """GitHub Light Theme Colors"""
    # Backgrounds
    BG_PRIMARY = "#ffffff"
    BG_SECONDARY = "#f6f8fa"
    BG_TERTIARY = "#f3f4f6"

    # Borders
    BORDER_DEFAULT = "#d0d7de"
    BORDER_MUTED = "#d8dee4"
    BORDER_EMPHASIS = "#afb8c1"

    # Text
    TEXT_PRIMARY = "#24292f"
    TEXT_SECONDARY = "#57606a"
    TEXT_MUTED = "#6e7781"

    # Accent colors
    ACCENT_BLUE = "#0969da"
    ACCENT_BLUE_LIGHT = "#218bff"

    # Semantic colors
    SUCCESS = "#1a7f37"
    SUCCESS_EMPHASIS = "#2c974b"
    DANGER = "#cf222e"
    DANGER_EMPHASIS = "#a40e26"
    WARNING = "#9a6700"

    # Interactive states
    HOVER_BG = "#f3f4f6"
    SELECTED_BG = "rgba(9, 105, 218, 0.1)"


def get_theme(is_dark: bool):
    """Get theme colors based on dark/light mode"""
    return GitHubDark if is_dark else GitHubLight


def get_stylesheet(is_dark: bool) -> str:
    """Generate complete stylesheet for the application"""
    t = get_theme(is_dark)

    return f"""
        QMainWindow {{
            background-color: {t.BG_PRIMARY};
        }}
        QWidget {{
            background-color: {t.BG_PRIMARY};
            color: {t.TEXT_PRIMARY};
            font-family: "Segoe UI Variable", "Segoe UI", system-ui, sans-serif;
            font-size: 14px;
        }}

        /* Tabs */
        QTabWidget::pane {{
            border: none;
            background-color: transparent;
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {t.TEXT_SECONDARY};
            padding: 12px 24px;
            margin-right: 4px;
            border: none;
            border-bottom: 2px solid transparent;
            font-size: 14px;
            font-weight: 400;
        }}
        QTabBar::tab:selected {{
            color: {t.TEXT_PRIMARY};
            border-bottom: 2px solid {t.ACCENT_BLUE};
        }}
        QTabBar::tab:hover:!selected {{
            color: {t.TEXT_PRIMARY};
            background-color: {t.HOVER_BG};
        }}

        /* List Widget */
        QListWidget {{
            background-color: {t.BG_SECONDARY};
            color: {t.TEXT_PRIMARY};
            border: 1px solid {t.BORDER_DEFAULT};
            border-radius: 6px;
            padding: 4px;
            font-size: 14px;
            outline: none;
        }}
        QListWidget::item {{
            background-color: {t.BG_PRIMARY};
            border: 1px solid {t.BORDER_DEFAULT};
            border-radius: 6px;
            padding: 14px 16px;
            margin: 4px 2px;
        }}
        QListWidget::item:selected {{
            background-color: {t.SELECTED_BG};
            border: 1px solid {t.ACCENT_BLUE};
            color: {t.TEXT_PRIMARY};
        }}
        QListWidget::item:hover:!selected {{
            background-color: {t.BG_SECONDARY};
            border-color: {t.BORDER_EMPHASIS};
        }}

        /* Buttons */
        QPushButton {{
            background-color: {t.BG_TERTIARY};
            color: {t.TEXT_PRIMARY};
            border: 1px solid {t.BORDER_DEFAULT};
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {t.HOVER_BG};
            border-color: {t.BORDER_EMPHASIS};
        }}
        QPushButton:pressed {{
            background-color: {t.BG_SECONDARY};
        }}
        QPushButton#primary {{
            background-color: {t.SUCCESS};
            color: #ffffff;
            border: 1px solid {t.SUCCESS};
        }}
        QPushButton#primary:hover {{
            background-color: {t.SUCCESS_EMPHASIS};
        }}
        QPushButton#primary:pressed {{
            background-color: {t.SUCCESS};
        }}
        QPushButton#danger {{
            background-color: {t.DANGER};
            color: #ffffff;
            border: 1px solid {t.DANGER};
        }}
        QPushButton#danger:hover {{
            background-color: {t.DANGER_EMPHASIS};
        }}
        QPushButton#danger:pressed {{
            background-color: {t.DANGER};
        }}

        /* Radio Button */
        QRadioButton {{
            color: {t.TEXT_PRIMARY};
            spacing: 12px;
            font-size: 14px;
            padding: 8px 4px;
        }}
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 8px;
            border: 1px solid {t.BORDER_DEFAULT};
            background-color: {t.BG_PRIMARY};
        }}
        QRadioButton::indicator:checked {{
            border: 5px solid {t.ACCENT_BLUE};
            background-color: {t.BG_PRIMARY};
        }}
        QRadioButton::indicator:hover {{
            border-color: {t.ACCENT_BLUE};
        }}

        /* Checkbox */
        QCheckBox {{
            color: {t.TEXT_PRIMARY};
            spacing: 12px;
            font-size: 14px;
            padding: 8px 4px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 3px;
            border: 1px solid {t.BORDER_DEFAULT};
            background-color: {t.BG_PRIMARY};
        }}
        QCheckBox::indicator:checked {{
            background-color: {t.SUCCESS};
            border: 1px solid {t.SUCCESS};
        }}
        QCheckBox::indicator:hover {{
            border-color: {t.SUCCESS};
        }}

        /* Category Button (Settings Sidebar) */
        QPushButton#category_button {{
            background-color: transparent;
            color: {t.TEXT_SECONDARY};
            border: none;
            border-radius: 0;
            padding: 16px 20px;
            text-align: left;
            font-size: 14px;
        }}
        QPushButton#category_button:hover {{
            background-color: {t.HOVER_BG};
            color: {t.TEXT_PRIMARY};
        }}
        QPushButton#category_button:checked {{
            background-color: {t.SELECTED_BG};
            color: {t.ACCENT_BLUE_LIGHT};
            border-left: 3px solid {t.ACCENT_BLUE};
        }}

        /* Settings Sidebar */
        QWidget#settings_sidebar {{
            background-color: {t.BG_SECONDARY};
            border-right: 1px solid {t.BORDER_DEFAULT};
        }}

        /* Slider */
        QSlider::groove:horizontal {{
            background-color: {t.BORDER_DEFAULT};
            height: 6px;
            border-radius: 3px;
        }}
        QSlider::sub-page:horizontal {{
            background-color: {t.ACCENT_BLUE};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background-color: {t.TEXT_PRIMARY};
            border: 2px solid {t.ACCENT_BLUE};
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }}
        QSlider::handle:horizontal:hover {{
            background-color: {t.ACCENT_BLUE};
        }}

        /* Text Edit */
        QTextEdit {{
            background-color: {t.BG_SECONDARY};
            color: {t.TEXT_PRIMARY};
            border: 1px solid {t.BORDER_DEFAULT};
            border-radius: 6px;
            padding: 16px;
            font-size: 14px;
            line-height: 1.6;
            selection-background-color: {t.SELECTED_BG};
        }}

        /* Labels */
        QLabel {{
            color: {t.TEXT_PRIMARY};
            background-color: transparent;
        }}
        QLabel#title {{
            font-size: 32px;
            font-weight: 600;
            color: {t.TEXT_PRIMARY};
        }}
        QLabel#subtitle {{
            font-size: 14px;
            color: {t.TEXT_SECONDARY};
        }}
        QLabel#section {{
            font-size: 18px;
            font-weight: 600;
            color: {t.TEXT_PRIMARY};
            padding: 12px 0 8px 0;
        }}

        /* Scroll Area */
        QScrollArea {{
            border: none;
            background-color: transparent;
        }}

        /* Line Edit */
        QLineEdit {{
            background-color: {t.BG_PRIMARY};
            color: {t.TEXT_PRIMARY};
            border: 1px solid {t.BORDER_DEFAULT};
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 14px;
            selection-background-color: {t.SELECTED_BG};
        }}
        QLineEdit:focus {{
            border: 2px solid {t.ACCENT_BLUE};
            padding: 9px 13px;
        }}

        /* Splitter */
        QSplitter::handle {{
            background-color: {t.BORDER_DEFAULT};
            width: 1px;
        }}

        /* Frame */
        QFrame[frameShape="4"] {{
            border: 1px solid {t.BORDER_DEFAULT};
            border-radius: 6px;
            background-color: {t.BG_SECONDARY};
        }}
    """


def get_help_label_style(is_dark: bool) -> str:
    """Get stylesheet for help label based on theme"""
    t = get_theme(is_dark)

    return f"""
        QLabel {{
            background-color: {t.SELECTED_BG};
            color: {t.ACCENT_BLUE_LIGHT};
            border: 1px solid {t.ACCENT_BLUE_LIGHT};
            border-radius: 9px;
            font-size: 11px;
            font-weight: bold;
            padding: 2px;
            min-width: 16px;
            max-width: 16px;
            min-height: 16px;
            max-height: 16px;
        }}
        QLabel:hover {{
            background-color: rgba({_hex_to_rgb(t.ACCENT_BLUE)}, 0.3);
        }}
    """


def get_monitor_preview_colors(is_dark: bool) -> dict:
    """Get colors for monitor preview widget"""
    t = get_theme(is_dark)

    return {
        'normal': t.ACCENT_BLUE,
        'duplicate': t.DANGER,
        'text': '#ffffff',
        'primary_indicator': t.SUCCESS,
    }


def _hex_to_rgb(hex_color: str) -> str:
    """Convert hex color to RGB values for use in rgba()"""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"{r}, {g}, {b}"
