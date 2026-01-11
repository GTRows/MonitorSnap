from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen
from PyQt6.QtCore import Qt


def create_app_icon(size=256):
    """Create application icon with 3 monitors"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Colors
    bg_color = QColor('#0969da')  # GitHub blue
    accent_color = QColor('#58a6ff')
    stand_color = QColor('#24292f')

    # Back monitor (large, centered back)
    back_w = size * 0.7
    back_h = size * 0.45
    back_x = (size - back_w) / 2
    back_y = size * 0.15

    # Draw back monitor with slight transparency
    painter.setOpacity(0.6)
    painter.setPen(QPen(stand_color, 3))
    painter.setBrush(bg_color)
    painter.drawRoundedRect(int(back_x), int(back_y), int(back_w), int(back_h), 8, 8)

    # Stand for back monitor
    stand_w = 4
    stand_h = size * 0.08
    painter.drawRect(int(size / 2 - stand_w / 2), int(back_y + back_h), int(stand_w), int(stand_h))
    painter.drawRect(int(size / 2 - back_w * 0.15), int(back_y + back_h + stand_h - 4), int(back_w * 0.3), 4)

    # Front monitors (smaller, side by side)
    painter.setOpacity(1.0)
    front_w = size * 0.35
    front_h = size * 0.3
    front_y = size * 0.45
    gap = size * 0.05

    # Left front monitor
    left_x = size * 0.12
    painter.setPen(QPen(stand_color, 3))
    painter.setBrush(accent_color)
    painter.drawRoundedRect(int(left_x), int(front_y), int(front_w), int(front_h), 6, 6)

    # Stand for left monitor
    painter.drawRect(int(left_x + front_w / 2 - stand_w / 2), int(front_y + front_h), int(stand_w), int(stand_h * 0.8))
    painter.drawRect(int(left_x + front_w / 2 - front_w * 0.2), int(front_y + front_h + stand_h * 0.8 - 3), int(front_w * 0.4), 3)

    # Right front monitor
    right_x = size - left_x - front_w
    painter.drawRoundedRect(int(right_x), int(front_y), int(front_w), int(front_h), 6, 6)

    # Stand for right monitor
    painter.drawRect(int(right_x + front_w / 2 - stand_w / 2), int(front_y + front_h), int(stand_w), int(stand_h * 0.8))
    painter.drawRect(int(right_x + front_w / 2 - front_w * 0.2), int(front_y + front_h + stand_h * 0.8 - 3), int(front_w * 0.4), 3)

    painter.end()
    return pixmap


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # Generate icon in multiple sizes for Windows
    sizes = [16, 32, 48, 64, 128, 256]

    for size in sizes:
        icon = create_app_icon(size)
        icon.save(f"icon_{size}.png")
        print(f"Generated icon_{size}.png")

    print("\nTo create .ico file, use:")
    print("magick convert icon_16.png icon_32.png icon_48.png icon_64.png icon_128.png icon_256.png app.ico")
    print("Or use an online converter: https://convertio.co/png-ico/")
