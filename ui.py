import os
import datetime

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame, QScrollArea,
    QGraphicsDropShadowEffect, QApplication, QSizePolicy, QLineEdit, QLayout
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPixmap, QTransform


class CommandsPill(QFrame):
    @staticmethod
    def tint_pixmap(pixmap, color):
        if pixmap.isNull():
            return pixmap

        tinted = QPixmap(pixmap.size())
        tinted.fill(Qt.transparent)

        painter = QPainter(tinted)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(tinted.rect(), color)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        return tinted

    def __init__(
        self,
        menu_icon_path,
        next_icon_path,
        icon_size=16,
        arrow_size=10,
        horizontal_padding=15,
        item_spacing=8,
        border_radius=19
    ):
        super().__init__()

        self.setFixedSize(170, 38)
        self.setCursor(Qt.PointingHandCursor)

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 155);
                border: 1px solid rgba(59, 130, 246, 210);
                border-radius: %dpx;
            }

            QFrame:hover {
                background-color: rgba(37, 99, 235, 120);
                border: 1px solid rgba(147, 197, 253, 230);
            }

            QLabel {
                background: transparent;
                border: none;
            }
        """ % border_radius)

        self.menu_label = QLabel()
        self.menu_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.menu_label.setFixedSize(18, 18)
        self.menu_label.setAlignment(Qt.AlignCenter)
        self.arrow_size = arrow_size

        self.icon_color = QColor("#93c5fd")

        menu_pixmap = self.tint_pixmap(QPixmap(menu_icon_path), self.icon_color)
        if not menu_pixmap.isNull():
            self.menu_label.setPixmap(
                menu_pixmap.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        self.text_label = QLabel("Commands")
        self.text_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.text_label.setStyleSheet("""
            QLabel {
                color: #dbeafe;
                font-size: 11px;
                font-weight: 750;
                background-color: transparent;
                border: none;
                outline: none;
            }
        """)

        self.arrow_label = QLabel()
        self.arrow_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.arrow_label.setFixedSize(14, 14)
        self.arrow_label.setAlignment(Qt.AlignCenter)

        self.arrow_pixmap = self.tint_pixmap(QPixmap(next_icon_path), self.icon_color)
        self.setText("Commands  >")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(horizontal_padding, 0, horizontal_padding, 0)
        layout.setSpacing(item_spacing)
        layout.addWidget(self.menu_label)
        layout.addWidget(self.text_label)
        layout.addStretch()
        layout.addWidget(self.arrow_label)

    def setText(self, text):
        if self.arrow_pixmap.isNull():
            self.arrow_label.setText("<" if "<" in text or "‹" in text else ">")
            return

        pixmap = self.arrow_pixmap
        if "<" in text or "‹" in text:
            pixmap = pixmap.transformed(QTransform().scale(-1, 1))

        self.arrow_label.setPixmap(
            pixmap.scaled(self.arrow_size, self.arrow_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )


class OptionsMenuItem(QPushButton):
    def __init__(self, text, icon_path=None, fallback_icon=""):
        super().__init__()

        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(34)
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                background-color: rgba(15, 23, 42, 70);
                color: #e5e7eb;
                border: 1px solid rgba(71, 85, 105, 105);
                border-radius: 9px;
                padding-left: 42px;
                font-size: 12px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: rgba(37, 99, 235, 75);
                border: 1px solid rgba(96, 165, 250, 125);
            }
        """)

        icon_box = QFrame(self)
        icon_box.setObjectName("options_item_icon_box")
        icon_box.setGeometry(6, 4, 26, 26)
        icon_box.setStyleSheet("""
            QFrame#options_item_icon_box {
                background-color: rgba(30, 41, 59, 145);
                border: 1px solid rgba(96, 165, 250, 145);
                border-radius: 8px;
            }
        """)
        icon_box.setAttribute(Qt.WA_TransparentForMouseEvents)

        icon_label = QLabel(icon_box)
        icon_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        icon_label.setGeometry(5, 5, 16, 16)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent; border: none;")

        if icon_path:
            pixmap = CommandsPill.tint_pixmap(QPixmap(icon_path), QColor("#f9fafb"))
            if not pixmap.isNull():
                icon_label.setPixmap(
                    pixmap.scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
        else:
            icon_label.setText(fallback_icon)
            icon_label.setStyleSheet("""
                QLabel {
                    color: #f9fafb;
                    background: transparent;
                    border: none;
                    font-size: 14px;
                    font-weight: 800;
                }
            """)

        self.setText(text)


class ModernGestureCard(QFrame):
    clicked = Signal()
    expand_clicked = Signal()

    def __init__(self, title="", image_path=None, description="", expandable=False, featured=False):
        super().__init__()

        self.setObjectName("modern_gesture_card")
        self.featured = featured
        self.is_active = False
        self.blink_state = False
        self.icon_radius = 14 if featured else 12
        self.title_font = 16 if featured else 13
        self.description_font = 11 if featured else 10

        self.setMinimumWidth(148)
        self.setFixedHeight(186 if featured else 78)

        icon_size = 96 if featured else 56
        pixmap_size = 80 if featured else 46

        self.icon_box = QFrame()
        self.icon_box.setObjectName("modern_icon_box")
        if featured:
            self.icon_box.setObjectName("featured_icon_box")
        self.icon_box.setFixedSize(icon_size, icon_size)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("background: transparent; border: none;")

        if image_path:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                self.icon_label.setPixmap(
                    pixmap.scaled(
                        pixmap_size,
                        pixmap_size,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                )
            else:
                self.icon_label.setText("?")
        else:
            self.icon_label.setText("?")

        icon_layout = QVBoxLayout(self.icon_box)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(self.icon_label)

        self.title_label = QLabel(title)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("background: transparent; border: none;")

        self.description_label = QLabel(description)
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("background: transparent; border: none;")

        if featured:
            self.title_label.setAlignment(Qt.AlignCenter)
            self.description_label.setAlignment(Qt.AlignCenter)

            content_layout = QVBoxLayout()
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(8)
            content_layout.addWidget(self.icon_box, alignment=Qt.AlignCenter)
            content_layout.addWidget(self.title_label)
            content_layout.addWidget(self.description_label)
            content_layout.addStretch()
        else:
            text_layout = QVBoxLayout()
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(3)
            text_layout.addStretch()
            text_layout.addWidget(self.title_label)
            text_layout.addWidget(self.description_label)
            text_layout.addSpacing(4)
            text_layout.addStretch()

            content_layout = QHBoxLayout()
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(14)
            content_layout.addWidget(self.icon_box, alignment=Qt.AlignVCenter)
            content_layout.addLayout(text_layout, stretch=1)
            content_layout.setAlignment(self.icon_box, Qt.AlignVCenter)

        self.expand_label = None
        if expandable:
            # Icons:
            # Open menu icons created by bqlqn - Flaticon
            # Next icons created by Roundicons - Flaticon
            self.expand_label = CommandsPill(
                os.path.join("slike", "menu.png"),
                os.path.join("slike", "right-arrow.png")
            )
            self.expand_label.mousePressEvent = self.handle_expand_label_click

        layout = QVBoxLayout(self)
        if featured:
            layout.setContentsMargins(12, 14, 12, 12)
        else:
            layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        layout.addLayout(content_layout)

        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(0)
        self.shadow.setOffset(0, 0)
        self.shadow.setColor(QColor(96, 165, 250, 0))
        self.setGraphicsEffect(self.shadow)

        self.set_inactive()

    def handle_expand_label_click(self, event):
        if event.button() == Qt.LeftButton:
            self.expand_clicked.emit()
            event.accept()
            return

        QLabel.mousePressEvent(self.expand_label, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

        super().mousePressEvent(event)

    def set_active(self):
        self.is_active = True
        self.blink_state = not self.blink_state

        border_color = "#60a5fa" if self.blink_state else "#93c5fd"
        glow_alpha = 150 if self.blink_state else 85

        self.setStyleSheet(f"""
            QFrame#modern_gesture_card {{
                background-color: rgba(37, 99, 235, 95);
                border: 1px solid {border_color};
                border-radius: 14px;
            }}

            QFrame#modern_icon_box {{
                background-color: rgba(37, 99, 235, 145);
                border: 1px solid rgba(147, 197, 253, 180);
                border-radius: {self.icon_radius}px;
            }}

            QFrame#featured_icon_box {{
                background-color: transparent;
                border: none;
                border-radius: 0px;
            }}
        """)

        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: #ffffff;
                font-size: {self.title_font}px;
                font-weight: 750;
                background: transparent;
                border: none;
            }}
        """)
        self.description_label.setStyleSheet(f"""
            QLabel {{
                color: #dbeafe;
                font-size: {self.description_font}px;
                background: transparent;
                border: none;
            }}
        """)
        self.shadow.setBlurRadius(24)
        self.shadow.setColor(QColor(96, 165, 250, glow_alpha))

    def set_inactive(self):
        self.is_active = False
        self.blink_state = False

        self.setStyleSheet(f"""
            QFrame#modern_gesture_card {{
                background-color: rgba(15, 23, 42, 140);
                border: 1px solid rgba(71, 85, 105, 130);
                border-radius: 14px;
            }}

            QFrame#modern_gesture_card:hover {{
                background-color: rgba(30, 41, 59, 165);
                border: 1px solid rgba(96, 165, 250, 130);
            }}

            QFrame#modern_icon_box {{
                background-color: rgba(30, 41, 59, 175);
                border: 1px solid rgba(96, 165, 250, 100);
                border-radius: {self.icon_radius}px;
            }}

            QFrame#featured_icon_box {{
                background-color: transparent;
                border: none;
                border-radius: 0px;
            }}
        """)

        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: #f8fafc;
                font-size: {self.title_font}px;
                font-weight: 750;
                background: transparent;
                border: none;
            }}
        """)
        self.description_label.setStyleSheet(f"""
            QLabel {{
                color: #94a3b8;
                font-size: {self.description_font}px;
                background: transparent;
                border: none;
            }}
        """)
        self.shadow.setBlurRadius(0)
        self.shadow.setColor(QColor(96, 165, 250, 0))


class HorizontalGestureCard(QFrame):
    clicked = Signal()
    expand_clicked = Signal()

    def __init__(self, title="", image_path=None, description="", expandable=False, featured=False):
        super().__init__()

        self.setObjectName("horizontal_gesture_card")
        self.featured = featured
        self.is_active = False
        self.blink_state = False
        self.expand_label = None

        self.setFixedSize(260 if featured else 108, 124)

        layout = QHBoxLayout(self) if featured else QVBoxLayout(self)
        layout.setContentsMargins(14 if featured else 10, 10, 14 if featured else 10, 10)
        layout.setSpacing(10 if featured else 4)

        self.icon_box = QFrame()
        self.icon_box.setObjectName("horizontal_icon_box")
        if featured:
            self.icon_box.setObjectName("horizontal_featured_icon_box")
        self.icon_box.setFixedSize(80 if featured else 62, 80 if featured else 62)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("background: transparent; border: none;")

        if image_path:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                pixmap_size = 72 if featured else 48
                self.icon_label.setPixmap(
                    pixmap.scaled(pixmap_size, pixmap_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )

        icon_layout = QVBoxLayout(self.icon_box)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(self.icon_label)

        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter if not featured else Qt.AlignLeft)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("background: transparent; border: none;")

        self.description_label = QLabel(description)
        self.description_label.setAlignment(Qt.AlignCenter if not featured else Qt.AlignLeft)
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("background: transparent; border: none;")

        if featured:
            text_layout = QVBoxLayout()
            text_layout.setContentsMargins(0, 10, 0, 0)
            text_layout.setSpacing(4)
            text_layout.addStretch(2)
            text_layout.addWidget(self.title_label)
            text_layout.addWidget(self.description_label)

            if expandable:
                text_layout.addSpacing(8)
                self.expand_label = CommandsPill(
                    os.path.join("slike", "menu.png"),
                    os.path.join("slike", "right-arrow.png"),
                    icon_size=12,
                    arrow_size=8,
                    horizontal_padding=12,
                    item_spacing=6,
                    border_radius=16
                )
                self.expand_label.setFixedSize(138, 32)
                self.expand_label.mousePressEvent = self.handle_expand_label_click
                text_layout.addWidget(self.expand_label)

            text_layout.addStretch(1)

            layout.addWidget(self.icon_box, alignment=Qt.AlignVCenter)
            layout.addLayout(text_layout, stretch=1)
        else:
            layout.addWidget(self.icon_box, alignment=Qt.AlignCenter)
            layout.addWidget(self.title_label)
            layout.addWidget(self.description_label)

        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(0)
        self.shadow.setOffset(0, 0)
        self.shadow.setColor(QColor(96, 165, 250, 0))
        self.setGraphicsEffect(self.shadow)

        self.set_inactive()

    def handle_expand_label_click(self, event):
        if event.button() == Qt.LeftButton:
            self.expand_clicked.emit()
            event.accept()
            return

        QLabel.mousePressEvent(self.expand_label, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

        super().mousePressEvent(event)

    def set_active(self):
        self.is_active = True
        self.blink_state = not self.blink_state
        border_color = "#60a5fa" if self.blink_state else "#93c5fd"
        glow_alpha = 140 if self.blink_state else 80

        self.apply_style(
            "rgba(37, 99, 235, 95)",
            border_color,
            "rgba(37, 99, 235, 145)",
            "rgba(147, 197, 253, 180)",
            "#ffffff",
            "#dbeafe"
        )
        self.shadow.setBlurRadius(22)
        self.shadow.setColor(QColor(96, 165, 250, glow_alpha))

    def set_inactive(self):
        self.is_active = False
        self.blink_state = False
        self.apply_style(
            "rgba(15, 23, 42, 140)",
            "rgba(71, 85, 105, 130)",
            "rgba(30, 41, 59, 175)",
            "rgba(96, 165, 250, 100)",
            "#f8fafc",
            "#94a3b8"
        )
        self.shadow.setBlurRadius(0)
        self.shadow.setColor(QColor(96, 165, 250, 0))

    def apply_style(self, card_bg, card_border, icon_bg, icon_border, title_color, description_color):
        self.setStyleSheet(f"""
            QFrame#horizontal_gesture_card {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 16px;
            }}

            QFrame#horizontal_gesture_card:hover {{
                background-color: rgba(30, 41, 59, 165);
                border: 1px solid rgba(96, 165, 250, 150);
            }}

            QFrame#horizontal_icon_box {{
                background-color: {icon_bg};
                border: 1px solid {icon_border};
                border-radius: 14px;
            }}

            QFrame#horizontal_featured_icon_box {{
                background-color: transparent;
                border: none;
                border-radius: 0px;
            }}
        """)

        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {title_color};
                font-size: {14 if self.featured else 12}px;
                font-weight: 750;
                background: transparent;
                border: none;
            }}
        """)
        self.description_label.setStyleSheet(f"""
            QLabel {{
                color: {description_color};
                font-size: {10 if self.featured else 9}px;
                background: transparent;
                border: none;
            }}
        """)

class VerticalResizeHandle(QFrame):
    def __init__(self, target_widget):
        super().__init__()

        self.target_widget = target_widget

        self.setFixedHeight(30)
        self.setCursor(Qt.SizeVerCursor)

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 150);
                border: 1px solid rgba(96, 165, 250, 105);
                border-radius: 15px;
            }

            QFrame:hover {
                background-color: rgba(37, 99, 235, 115);
                border: 1px solid rgba(147, 197, 253, 175);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(0)

        label = QLabel("↕")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                color: #dbeafe;
                font-size: 12px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)

        layout.addWidget(label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            window_handle = self.target_widget.windowHandle()

            if window_handle:
                window_handle.startSystemResize(Qt.BottomEdge)

            event.accept()
        else:
            super().mousePressEvent(event)    


class HorizontalResizeHandle(QFrame):
    def __init__(self, target_widget):
        super().__init__()

        self.target_widget = target_widget

        self.setFixedWidth(24)
        self.setCursor(Qt.SizeHorCursor)

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 150);
                border: 1px solid rgba(96, 165, 250, 105);
                border-radius: 12px;
            }

            QFrame:hover {
                background-color: rgba(37, 99, 235, 115);
                border: 1px solid rgba(147, 197, 253, 175);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(0)

        label = QLabel("⟷")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                color: #dbeafe;
                font-size: 10px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
        """)

        layout.addWidget(label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            window_handle = self.target_widget.windowHandle()

            if window_handle:
                window_handle.startSystemResize(Qt.RightEdge)

            event.accept()
        else:
            super().mousePressEvent(event)

class AssistantSidebar(QWidget):
    close_requested = Signal()
    voice_requested = Signal()
    camera_toggle_requested = Signal()
    chat_text_submitted = Signal(str)
    chat_voice_requested = Signal()

    def __init__(self):
        super().__init__()

        self.expanded_width = 224
        self.collapsed_width = 58
        self.is_collapsed = False
        self.active_gesture_name = "NEUTRAL"
        self.chat_messages = []
        self.default_voice_title = 'Say "Hey Nexa"'
        self.default_voice_description = "Wake with voice"
        self.voice_card_reset_timer = QTimer(self)
        self.voice_card_reset_timer.setSingleShot(True)
        self.voice_card_reset_timer.timeout.connect(self.reset_voice_card_text)

        self.thinking_row = None
        self.thinking_label = None
        self.thinking_dots = 0

        self.thinking_timer = QTimer(self)
        self.thinking_timer.timeout.connect(self.update_thinking_bubble)

        self.is_horizontal = False
        self.vertical_height = None
        self.restore_geometry_after_collapse = None

        self.dragging_window = False
        self.drag_start_position = None
        self.window_start_position = None

        logo_path = os.path.join("slike", "Nexa.png")
        camera_path = os.path.join("slike", "camera.png")
        message_path = os.path.join("slike", "message.png")
        microphone_path = os.path.join("slike", "microphone.png")
        sound_path = os.path.join("slike", "speak.png")
        neutral_hand_path = os.path.join("slike", "neutral.png")
        move_hand_path = os.path.join("slike", "move.png")
        left_click_hand_path = os.path.join("slike", "left.png")
        double_click_hand_path = os.path.join("slike", "double.png")
        right_click_hand_path = os.path.join("slike", "right.png")
        scroll_hand_path = os.path.join("slike", "scroll.png")
        drag_hand_path = os.path.join("slike", "drag.png")
        pinch_volume_hand_path = os.path.join("slike", "volume.png")
        pinch_brightness_hand_path = os.path.join("slike", "brightness.png")
        no_hand_path = os.path.join("slike", "no_hand.png")
        unknown_hand_path = os.path.join("slike", "unknown.png")

        self.setWindowTitle("")
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(self.expanded_width)
        self.setMaximumWidth(self.expanded_width)
        
        self.setMinimumHeight(320)

        screen = QApplication.primaryScreen().availableGeometry()
        self.setMaximumHeight(screen.height())

        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                color: white;
                font-family: Segoe UI;
            }
        """)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(6, 6, 6, 6)
        outer_layout.setSpacing(0)

        self.expanded_container = QFrame()
        self.expanded_container.setObjectName("expanded_container")
        self.expanded_container.setStyleSheet("""
            QFrame#expanded_container {
                background-color: rgba(10, 15, 28, 232);
                border: 1px solid rgba(71, 85, 105, 135);
                border-radius: 14px;
            }
        """)

        expanded_layout = QVBoxLayout(self.expanded_container)
        expanded_layout.setContentsMargins(12, 12, 12, 10)
        expanded_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(3)

        logo_label = QLabel()
        logo_label.setFixedSize(26, 26)
        logo_label.setAlignment(Qt.AlignCenter)
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(
                logo_pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        logo_label.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 41, 59, 180);
                border: 1px solid rgba(96, 165, 250, 120);
                border-radius: 13px;
            }
        """)

        app_title = QLabel("Nexa")
        app_title.setStyleSheet("""
            QLabel {
                color: #f8fafc;
                font-size: 16px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        header_button_style = """
            QPushButton {
                background-color: rgba(15, 23, 42, 190);
                color: #f9fafb;
                border: 1px solid rgba(71, 85, 105, 170);
                border-radius: 13px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: rgba(37, 99, 235, 150);
                border: 1px solid rgba(147, 197, 253, 190);
            }
        """

        camera_button = QPushButton()
        camera_button.setFixedSize(26, 26)
        camera_button.setCursor(Qt.PointingHandCursor)
        camera_button.setStyleSheet(header_button_style)
        camera_button.clicked.connect(self.camera_toggle_requested.emit)

        camera_pixmap = QPixmap(camera_path)
        if not camera_pixmap.isNull():
            camera_pixmap = CommandsPill.tint_pixmap(camera_pixmap, QColor("#f9fafb"))
            camera_icon = QLabel(camera_button)
            camera_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
            camera_icon.setGeometry(5, 5, 16, 16)
            camera_icon.setPixmap(
                camera_pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        options_button = QPushButton("...")
        options_button.setFixedSize(26, 26)
        options_button.setCursor(Qt.PointingHandCursor)
        options_button.clicked.connect(self.toggle_options_panel)
        self.options_button = options_button
        options_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(15, 23, 42, 190);
                color: #f9fafb;
                border: 1px solid rgba(71, 85, 105, 170);
                border-radius: 13px;
                font-size: 12px;
                font-weight: 800;
            }

            QPushButton:hover {
                background-color: rgba(37, 99, 235, 150);
                border: 1px solid rgba(147, 197, 253, 190);
            }
        """)

        close_button = QPushButton("×")
        close_button.setFixedSize(26, 26)
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(15, 23, 42, 190);
                color: #f9fafb;
                border: 1px solid rgba(71, 85, 105, 170);
                border-radius: 13px;
                font-size: 14px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #ef4444;
                color: white;
            }
        """)

        header_layout.addWidget(logo_label)
        header_layout.addWidget(app_title)
        header_layout.addStretch()
        header_layout.addWidget(camera_button)
        header_layout.addWidget(options_button)
        header_layout.addWidget(close_button)

        expanded_layout.addLayout(header_layout)

        self.options_panel = QFrame(None)
        self.options_panel.setObjectName("options_panel")
        self.options_panel.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.options_panel.setAttribute(Qt.WA_ShowWithoutActivating)
        self.options_panel.setFixedSize(190, 162)
        self.options_panel.setStyleSheet("""
            QFrame#options_panel {
                background-color: rgba(15, 23, 42, 245);
                border: 1px solid rgba(96, 165, 250, 190);
                border-radius: 14px;
            }
        """)

        option_grid = QVBoxLayout(self.options_panel)
        option_grid.setContentsMargins(10, 10, 10, 10)
        option_grid.setSpacing(6)

        switch_side_button = OptionsMenuItem(
            "Switch side",
            os.path.join("slike", "switch_side.png")
        )
        switch_side_button.clicked.connect(self.toggle_orientation)

        minimize_button = OptionsMenuItem("Minimize sidebar", fallback_icon="−")
        minimize_button.clicked.connect(self.toggle_collapsed)

        panel_chat_button = OptionsMenuItem(
            "Chat",
            os.path.join("slike", "chat.png")
        )
        panel_chat_button.clicked.connect(self.options_panel.hide)
        panel_chat_button.clicked.connect(self.toggle_chat_panel)

        info_button = OptionsMenuItem(
            "About",
            os.path.join("slike", "about.png")
        )

        option_grid.addWidget(switch_side_button)
        option_grid.addWidget(minimize_button)
        option_grid.addWidget(panel_chat_button)
        option_grid.addWidget(info_button)
        self.options_panel.hide()

        title = QLabel("Controls")
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 800;
                color: #f9fafb;
                background: transparent;
                padding-top: 2px;
            }
        """)
        expanded_layout.addWidget(title)

        title_accent = QFrame()
        title_accent.setFixedSize(28, 3)
        title_accent.setStyleSheet("""
            QFrame {
                background-color: #60a5fa;
                border: none;
                border-radius: 1px;
            }
        """)
        expanded_layout.addWidget(title_accent)

        self.cards = {}

        self.gestures = [
            ("VOICE WAKE", self.default_voice_title, self.default_voice_description, sound_path),
            ("NEUTRAL", "Neutral", "Relaxed hand", neutral_hand_path),
            ("MOVE", "Move", "Move cursor", move_hand_path),
            ("LEFT CLICK", "Left click", "Single click", left_click_hand_path),
            ("DOUBLE CLICK", "Double click", "Double tap", double_click_hand_path),
            ("RIGHT CLICK", "Right click", "Context menu", right_click_hand_path),
            ("SCROLL", "Scroll", "Scroll page", scroll_hand_path),
            ("DRAG", "Drag & select", "Hold and move", drag_hand_path),
            ("PINCH VOLUME", "Volume", "Adjust sound", pinch_volume_hand_path),
            ("PINCH BRIGHTNESS", "Brightness", "Adjust screen light", pinch_brightness_hand_path),
            ("No hand detected", "No hand", "Camera cannot see hand", no_hand_path),
            ("Gesture not recognized", "Unknown", "Gesture not matched", unknown_hand_path),
        ]

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background: transparent;
                border-radius: 3px;
            }

            QScrollArea:hover QScrollBar::handle:vertical {
                background: rgba(96, 165, 250, 120);
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")

        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)

        for key, title_text, description, image_path in self.gestures:
            card = ModernGestureCard(
                title=title_text,
                image_path=image_path,
                description=description,
                expandable=(key == "VOICE WAKE"),
                featured=(key == "VOICE WAKE")
            )
            self.cards[key] = card
            scroll_layout.addWidget(card)

            if key == "VOICE WAKE":
                if card.expand_label is not None:
                    scroll_layout.addWidget(card.expand_label, alignment=Qt.AlignCenter)

                section_row = QFrame()
                section_row.setStyleSheet("background: transparent; border: none;")

                section_row_layout = QHBoxLayout(section_row)
                section_row_layout.setContentsMargins(0, 4, 0, 2)
                section_row_layout.setSpacing(10)

                left_line = QFrame()
                left_line.setFixedHeight(1)
                left_line.setStyleSheet("""
                    QFrame {
                        background-color: rgba(71, 85, 105, 150);
                        border: none;
                    }
                """)

                section_label = QLabel("GESTURES")
                section_label.setAlignment(Qt.AlignCenter)
                section_label.setStyleSheet("""
                    QLabel {
                        color: #94a3b8;
                        font-size: 10px;
                        font-weight: 800;
                        background: transparent;
                        border: none;
                    }
                """)

                right_line = QFrame()
                right_line.setFixedHeight(1)
                right_line.setStyleSheet("""
                    QFrame {
                        background-color: rgba(71, 85, 105, 150);
                        border: none;
                    }
                """)

                section_row_layout.addWidget(left_line, stretch=1)
                section_row_layout.addWidget(section_label)
                section_row_layout.addWidget(right_line, stretch=1)

                scroll_layout.addWidget(section_row)

        self.cards["VOICE WAKE"].expand_clicked.connect(self.toggle_voice_commands)

        self.voice_commands_panel = QFrame(None)
        self.voice_commands_panel.setObjectName("voice_commands_panel")
        self.voice_commands_panel.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.voice_commands_panel.setAttribute(Qt.WA_ShowWithoutActivating)
        self.voice_commands_panel.setFixedWidth(240)
        self.voice_commands_panel.setFixedHeight(320)

        self.voice_commands_panel.setStyleSheet("""
            QFrame#voice_commands_panel {
                background-color: rgba(17, 24, 39, 245);
                border: 1px solid rgba(96, 165, 250, 130);
                border-radius: 18px;
            }

            QLabel {
                background: transparent;
                border: none;
            }
        """)

        voice_panel_layout = QVBoxLayout(self.voice_commands_panel)
        voice_panel_layout.setContentsMargins(12, 12, 12, 12)
        voice_panel_layout.setSpacing(8)

        voice_title = QLabel("Voice commands")
        voice_title.setStyleSheet("""
            QLabel {
                color: #f9fafb;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }
        """)
        voice_panel_layout.addWidget(voice_title)

        voice_subtitle = QLabel('Say "hey Nexa", then speak a command.')
        voice_subtitle.setWordWrap(True)
        voice_subtitle.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 10px;
                background: transparent;
                padding-bottom: 4px;
            }
        """)
        voice_panel_layout.addWidget(voice_subtitle)

        voice_commands_scroll_area = QScrollArea()
        voice_commands_scroll_area.setWidgetResizable(True)
        voice_commands_scroll_area.setFrameShape(QFrame.NoFrame)
        voice_commands_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        voice_commands_scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background: rgba(75, 85, 99, 170);
                border-radius: 3px;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        voice_commands_content = QWidget()
        voice_commands_content.setStyleSheet("background: transparent;")

        voice_commands_layout = QVBoxLayout(voice_commands_content)
        voice_commands_layout.setContentsMargins(0, 0, 0, 0)
        voice_commands_layout.setSpacing(8)

        def add_command_section(section_title, commands):
            section_label = QLabel(section_title)
            section_label.setStyleSheet("""
                QLabel {
                    color: #93c5fd;
                    font-size: 10px;
                    font-weight: bold;
                    background: transparent;
                    padding-top: 4px;
                }
            """)
            voice_commands_layout.addWidget(section_label)

            for command in commands:
                command_label = QLabel(command)
                command_label.setWordWrap(True)
                command_label.setStyleSheet("""
                    QLabel {
                        color: #e5e7eb;
                        font-size: 10px;
                        background-color: rgba(31, 41, 55, 180);
                        border: 1px solid rgba(75, 85, 99, 130);
                        border-radius: 8px;
                        padding: 4px 7px;
                    }
                """)
                voice_commands_layout.addWidget(command_label)


        add_command_section("Start", [
            'say "hey Nexa"',
            "stop listening",
            "stop talking",
            "stop action"
        ])

        add_command_section("Apps", [
            "open google",
            "open youtube",
            "open google maps",
            "open calculator",
            "open notepad"
        ])

        add_command_section("System", [
            "show desktop",
            "take screenshot",
            "what time is it",
            "what is the date",
            "weather"
        ])

        add_command_section("Pointer actions", [
            "open this",
            "select this",
            "show options",
            "start dragging",
            "drop here",
            "scroll up",
            "scroll down"
        ])

        add_command_section("Search", [
            "search"
        ])

        add_command_section("Chat", [
            "ask Nexa",
            "chat",
            "talk to Nexa"
        ])

        add_command_section("Safety", [
            "cancel action",
            "stop speaking",
            "be quiet"
        ])

        voice_commands_scroll_area.setWidget(voice_commands_content)
        voice_panel_layout.addWidget(voice_commands_scroll_area, stretch=1)

        self.voice_commands_panel.hide()

        self.chat_panel = QFrame(None)
        self.chat_panel.setObjectName("chat_panel")
        self.chat_panel.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.chat_panel.setAttribute(Qt.WA_ShowWithoutActivating)
        self.chat_panel.setFixedSize(360, 500)

        self.chat_panel.setStyleSheet("""
            QFrame#chat_panel {
                background-color: rgba(10, 15, 28, 248);
                border: 1px solid rgba(59, 130, 246, 170);
                border-radius: 22px;
            }

            QLabel {
                background: transparent;
                border: none;
            }
        """)

        chat_panel_layout = QVBoxLayout(self.chat_panel)
        chat_panel_layout.setContentsMargins(14, 14, 14, 14)
        chat_panel_layout.setSpacing(10)

        chat_header_layout = QHBoxLayout()
        chat_header_layout.setContentsMargins(0, 0, 0, 0)
        chat_header_layout.setSpacing(9)

        chat_logo_label = QLabel()
        chat_logo_label.setFixedSize(34, 34)
        chat_logo_label.setAlignment(Qt.AlignCenter)
        chat_logo_pixmap = QPixmap(logo_path)
        if not chat_logo_pixmap.isNull():
            chat_logo_label.setPixmap(
                chat_logo_pixmap.scaled(25, 25, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        chat_logo_label.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 41, 59, 180);
                border: 1px solid rgba(96, 165, 250, 130);
                border-radius: 17px;
            }
        """)

        chat_title_stack = QVBoxLayout()
        chat_title_stack.setContentsMargins(0, 0, 0, 0)
        chat_title_stack.setSpacing(1)

        chat_title = QLabel("Nexa Chat")
        chat_title.setStyleSheet("""
            QLabel {
                color: #f9fafb;
                font-size: 16px;
                font-weight: 800;
                background: transparent;
            }
        """)

        chat_subtitle = QLabel("Conversation with Nexa")
        chat_subtitle.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 10px;
                background: transparent;
            }
        """)

        chat_title_stack.addWidget(chat_title)
        chat_title_stack.addWidget(chat_subtitle)

        chat_close_button = QPushButton("×")
        chat_close_button.setFixedSize(24, 24)
        chat_close_button.setCursor(Qt.PointingHandCursor)
        chat_close_button.clicked.connect(self.chat_panel.hide)
        chat_close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(31, 41, 55, 220);
                color: #f9fafb;
                border: 1px solid #374151;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #ef4444;
                color: white;
            }
        """)

        chat_header_layout.addWidget(chat_logo_label)
        chat_header_layout.addLayout(chat_title_stack)
        chat_header_layout.addStretch()
        chat_header_layout.addWidget(chat_close_button)

        chat_panel_layout.addLayout(chat_header_layout)

        chat_divider = QFrame()
        chat_divider.setFixedHeight(1)
        chat_divider.setStyleSheet("background-color: rgba(30, 41, 59, 190); border: none;")
        chat_panel_layout.addWidget(chat_divider)

        self.chat_scroll_area = QScrollArea()
        self.chat_scroll_area.setWidgetResizable(True)
        self.chat_scroll_area.setFrameShape(QFrame.NoFrame)
        self.chat_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background: transparent;
                border-radius: 3px;
            }

            QScrollArea:hover QScrollBar::handle:vertical {
                background: rgba(75, 85, 99, 180);
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        chat_scroll_content = QWidget()
        chat_scroll_content.setStyleSheet("background: transparent;")

        self.chat_messages_layout = QVBoxLayout(chat_scroll_content)
        self.chat_messages_layout.setContentsMargins(0, 4, 0, 4)
        self.chat_messages_layout.setSpacing(16)

        self.chat_empty_label = QLabel(
            "Ask Nexa about gestures, voice commands, or multimodal interfaces."
        )
        self.chat_empty_label.setWordWrap(True)
        self.chat_empty_label.setAlignment(Qt.AlignCenter)
        self.chat_empty_label.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 11px;
                background-color: rgba(15, 23, 42, 120);
                border: 1px solid rgba(71, 85, 105, 110);
                border-radius: 12px;
                padding: 14px;
            }
        """)
        self.chat_messages_layout.addWidget(self.chat_empty_label)
        self.chat_messages_layout.addStretch()

        self.chat_scroll_area.setWidget(chat_scroll_content)
        chat_panel_layout.addWidget(self.chat_scroll_area)

        chat_input_frame = QFrame()
        chat_input_frame.setObjectName("chat_input_frame")
        chat_input_frame.setStyleSheet("""
            QFrame#chat_input_frame {
                background-color: rgba(15, 23, 42, 190);
                border: 1px solid rgba(59, 130, 246, 170);
                border-radius: 18px;
            }
        """)

        chat_input_layout = QHBoxLayout(chat_input_frame)
        chat_input_layout.setContentsMargins(12, 7, 7, 7)
        chat_input_layout.setSpacing(7)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask Nexa something...")
        self.chat_input.returnPressed.connect(self.submit_chat_text)
        self.chat_input.setStyleSheet("""
            QLineEdit {
                color: #f9fafb;
                background: transparent;
                border: none;
                font-size: 12px;
            }
        """)

        chat_mic_button = QPushButton("")
        chat_mic_button.setFixedSize(34, 30)
        chat_mic_button.setCursor(Qt.PointingHandCursor)
        chat_mic_button.clicked.connect(self.chat_voice_requested.emit)
        chat_mic_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(15, 23, 42, 200);
                color: #93c5fd;
                border: 1px solid rgba(71, 85, 105, 170);
                border-radius: 15px;
                font-size: 10px;
                font-weight: 750;
            }

            QPushButton:hover {
                background-color: rgba(37, 99, 235, 120);
                border: 1px solid rgba(147, 197, 253, 200);
            }
        """)

        mic_pixmap = QPixmap(microphone_path)
        if not mic_pixmap.isNull():
            mic_pixmap = CommandsPill.tint_pixmap(mic_pixmap, QColor("#93c5fd"))
            mic_icon = QLabel(chat_mic_button)
            mic_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
            mic_icon.setGeometry(9, 7, 16, 16)
            mic_icon.setPixmap(
                mic_pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            mic_icon.setAlignment(Qt.AlignCenter)
            mic_icon.setStyleSheet("background: transparent; border: none;")

        chat_send_button = QPushButton("")
        chat_send_button.setFixedSize(30, 30)
        chat_send_button.setCursor(Qt.PointingHandCursor)
        chat_send_button.clicked.connect(self.submit_chat_text)
        chat_send_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(37, 99, 235, 210);
                color: #f9fafb;
                border: 1px solid rgba(96, 165, 250, 190);
                border-radius: 15px;
                font-size: 14px;
                font-weight: 800;
            }

            QPushButton:hover {
                background-color: rgba(59, 130, 246, 235);
            }
        """)

        send_pixmap = QPixmap(message_path)
        if not send_pixmap.isNull():
            send_pixmap = CommandsPill.tint_pixmap(send_pixmap, QColor("#f9fafb"))
            send_icon = QLabel(chat_send_button)
            send_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
            send_icon.setGeometry(7, 7, 16, 16)
            send_icon.setPixmap(
                send_pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            send_icon.setAlignment(Qt.AlignCenter)
            send_icon.setStyleSheet("background: transparent; border: none;")

        chat_input_layout.addWidget(self.chat_input, stretch=1)
        chat_input_layout.addWidget(chat_mic_button)
        chat_input_layout.addWidget(chat_send_button)

        chat_panel_layout.addWidget(chat_input_frame)

        self.chat_panel.hide()

        scroll_layout.addStretch()

        self.scroll_area.setWidget(scroll_content)
        expanded_layout.addWidget(self.scroll_area, stretch=1)

        expanded_resize_handle = VerticalResizeHandle(self)
        expanded_layout.addWidget(expanded_resize_handle)

        self.collapsed_container = QFrame()
        self.collapsed_container.setObjectName("collapsed_container")
        self.collapsed_container.setStyleSheet("""
            QFrame#collapsed_container {
                background-color: rgba(17, 24, 39, 175);
                border: 1px solid rgba(75, 85, 99, 120);
                border-radius: 20px;
            }
        """)

        collapsed_layout = QVBoxLayout(self.collapsed_container)
        collapsed_layout.setContentsMargins(6, 8, 6, 8)
        collapsed_layout.setSpacing(8)

        expand_button = QPushButton("›")
        expand_button.setFixedSize(30, 30)
        expand_button.setCursor(Qt.PointingHandCursor)
        expand_button.clicked.connect(self.toggle_collapsed)
        expand_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(31, 41, 55, 220);
                color: #f9fafb;
                border: 1px solid #374151;
                border-radius: 15px;
                font-size: 18px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #2563eb;
            }
        """)

        collapsed_layout.addWidget(expand_button, alignment=Qt.AlignCenter)

        collapsed_layout.addStretch()

        self.collapsed_resize_handle = VerticalResizeHandle(self)
        collapsed_layout.addWidget(self.collapsed_resize_handle)


        # Horizontal container
        self.horizontal_container = QFrame()
        self.horizontal_container.setObjectName("horizontal_container")
        self.horizontal_container.setStyleSheet("""
            QFrame#horizontal_container {
                background-color: rgba(10, 15, 28, 232);
                border: 1px solid rgba(59, 130, 246, 150);
                border-radius: 30px;
            }
        """)

        horizontal_layout = QHBoxLayout(self.horizontal_container)
        horizontal_layout.setContentsMargins(6, 16, 18, 16)
        horizontal_layout.setSpacing(12)

        horizontal_brand_panel = QFrame()
        horizontal_brand_panel.setObjectName("horizontal_brand_panel")
        horizontal_brand_panel.setFixedWidth(150)
        horizontal_brand_panel.setFixedHeight(132)
        horizontal_brand_panel.setStyleSheet("""
            QFrame#horizontal_brand_panel {
                background: transparent;
                border: none;
            }
        """)

        horizontal_brand_layout = QVBoxLayout(horizontal_brand_panel)
        horizontal_brand_layout.setContentsMargins(0, 0, 0, 0)
        horizontal_brand_layout.setSpacing(0)

        horizontal_title_wrapper = QFrame(horizontal_brand_panel)
        horizontal_title_wrapper.setStyleSheet("background: transparent; border: none;")
        horizontal_title_wrapper.setContentsMargins(0, 0, 0, 0)
        horizontal_title_wrapper.setGeometry(0, 6, 150, 40)

        horizontal_title_row = QHBoxLayout(horizontal_title_wrapper)
        horizontal_title_row.setContentsMargins(26, 0, 0, 0)
        horizontal_title_row.setSpacing(8)

        horizontal_logo_label = QLabel()
        horizontal_logo_label.setFixedSize(34, 34)
        horizontal_logo_label.setAlignment(Qt.AlignCenter)
        horizontal_logo_pixmap = QPixmap(logo_path)
        if not horizontal_logo_pixmap.isNull():
            horizontal_logo_label.setPixmap(
                horizontal_logo_pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        horizontal_logo_label.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 41, 59, 180);
                border: 1px solid rgba(96, 165, 250, 130);
                border-radius: 17px;
            }
        """)

        horizontal_title = QLabel("Nexa")
        horizontal_title.setStyleSheet("""
            QLabel {
                color: #f8fafc;
                font-size: 20px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        horizontal_title_row.addWidget(horizontal_logo_label)
        horizontal_title_row.addWidget(horizontal_title)
        horizontal_title_row.addStretch()

        horizontal_controls_row = QHBoxLayout()
        horizontal_controls_row.setContentsMargins(0, 0, 0, 0)
        horizontal_controls_row.setSpacing(0)
        horizontal_button_size = 26
        horizontal_button_gap = 3
        horizontal_controls_panel = QFrame(horizontal_brand_panel)
        horizontal_controls_panel.setFixedSize(
            horizontal_button_size * 3 + horizontal_button_gap * 2,
            horizontal_button_size
        )
        horizontal_controls_panel.setGeometry(35,80, horizontal_controls_panel.width(), horizontal_controls_panel.height())
        horizontal_controls_panel.setStyleSheet("background: transparent; border: none;")

        horizontal_button_style = """
            QPushButton {
                background-color: rgba(15, 23, 42, 190);
                color: #f9fafb;
                border: 1px solid rgba(71, 85, 105, 170);
                border-radius: 13px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: rgba(37, 99, 235, 150);
                border: 1px solid rgba(147, 197, 253, 190);
            }
        """

        horizontal_camera_button = QPushButton(horizontal_controls_panel)
        horizontal_camera_button.setGeometry(0, 0, horizontal_button_size, horizontal_button_size)
        horizontal_camera_button.setCursor(Qt.PointingHandCursor)
        horizontal_camera_button.setStyleSheet(horizontal_button_style)
        horizontal_camera_button.clicked.connect(self.camera_toggle_requested.emit)

        horizontal_camera_pixmap = QPixmap(camera_path)
        if not horizontal_camera_pixmap.isNull():
            horizontal_camera_pixmap = CommandsPill.tint_pixmap(horizontal_camera_pixmap, QColor("#f9fafb"))
            horizontal_camera_icon = QLabel(horizontal_camera_button)
            horizontal_camera_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
            horizontal_camera_icon.setGeometry(5, 5, 16, 16)
            horizontal_camera_icon.setPixmap(
                horizontal_camera_pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        horizontal_options_button = QPushButton("...", horizontal_controls_panel)
        horizontal_options_button.setGeometry(
            horizontal_button_size + horizontal_button_gap,
            0,
            horizontal_button_size,
            horizontal_button_size
        )
        horizontal_options_button.setCursor(Qt.PointingHandCursor)
        horizontal_options_button.clicked.connect(self.toggle_options_panel)
        horizontal_options_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(15, 23, 42, 190);
                color: #f9fafb;
                border: 1px solid rgba(71, 85, 105, 170);
                border-radius: 13px;
                font-size: 12px;
                font-weight: 800;
            }

            QPushButton:hover {
                background-color: rgba(37, 99, 235, 150);
                border: 1px solid rgba(147, 197, 253, 190);
            }
        """)
        self.horizontal_options_button = horizontal_options_button

        horizontal_close_button = QPushButton("")
        horizontal_close_button.setParent(horizontal_controls_panel)
        horizontal_close_button.setGeometry(
            (horizontal_button_size + horizontal_button_gap) * 2,
            0,
            horizontal_button_size,
            horizontal_button_size
        )
        horizontal_close_button.setCursor(Qt.PointingHandCursor)
        horizontal_close_button.clicked.connect(self.close)
        horizontal_close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(15, 23, 42, 190);
                color: #f9fafb;
                border: 1px solid rgba(71, 85, 105, 170);
                border-radius: 13px;
            }

            QPushButton:hover {
                background-color: rgba(239, 68, 68, 170);
                border: 1px solid rgba(252, 165, 165, 210);
                color: white;
            }
        """)

        horizontal_close_label = QLabel("×", horizontal_close_button)
        horizontal_close_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        horizontal_close_label.setGeometry(0, -1, horizontal_button_size, horizontal_button_size)
        horizontal_close_label.setAlignment(Qt.AlignCenter)
        horizontal_close_label.setStyleSheet("""
            QLabel {
                color: #f9fafb;
                background: transparent;
                border: none;
                font-size: 16px;
                font-weight: 700;
            }
        """)

        horizontal_separator_left = QFrame()
        horizontal_separator_left.setFixedWidth(1)
        horizontal_separator_left.setStyleSheet("""
            QFrame {
                background-color: rgba(71, 85, 105, 150);
                border: none;
            }
        """)

        self.horizontal_scroll_area = QScrollArea()
        self.horizontal_scroll_area.setWidgetResizable(True)
        self.horizontal_scroll_area.setFrameShape(QFrame.NoFrame)
        self.horizontal_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.horizontal_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.horizontal_scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }

            QScrollBar:horizontal {
                background: transparent;
                height: 6px;
                margin: 0px;
            }

            QScrollBar::handle:horizontal {
                background: transparent;
                border-radius: 3px;
            }

            QScrollArea:hover QScrollBar::handle:horizontal {
                background: rgba(75, 85, 99, 180);
            }

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

        horizontal_scroll_content = QWidget()
        horizontal_scroll_content.setStyleSheet("background: transparent;")

        horizontal_cards_layout = QHBoxLayout(horizontal_scroll_content)
        horizontal_cards_layout.setContentsMargins(0, 0, 0, 0)
        horizontal_cards_layout.setSpacing(12)
        horizontal_cards_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.horizontal_cards = {}

        for key, title_text, description, image_path in self.gestures:
            horizontal_description = "No hand visible" if key == "No hand detected" else description

            card = HorizontalGestureCard(
                title=title_text,
                image_path=image_path,
                description=horizontal_description,
                expandable=(key == "VOICE WAKE"),
                featured=(key == "VOICE WAKE")
            )
            self.horizontal_cards[key] = card
            horizontal_cards_layout.addWidget(card, 0, Qt.AlignVCenter)

            if key == "VOICE WAKE":
                horizontal_voice_separator = QFrame()
                horizontal_voice_separator.setFixedSize(1, 96)
                horizontal_voice_separator.setStyleSheet("""
                    QFrame {
                        background-color: rgba(71, 85, 105, 150);
                        border: none;
                    }
                """)
                horizontal_cards_layout.addWidget(horizontal_voice_separator, 0, Qt.AlignVCenter)

        self.horizontal_cards["VOICE WAKE"].expand_clicked.connect(self.toggle_voice_commands)

        horizontal_cards_layout.addStretch()

        self.horizontal_scroll_area.setWidget(horizontal_scroll_content)

        horizontal_layout.addWidget(horizontal_brand_panel, alignment=Qt.AlignVCenter)
        horizontal_layout.addWidget(horizontal_separator_left)
        horizontal_layout.addWidget(self.horizontal_scroll_area, stretch=1)
        horizontal_resize_handle = HorizontalResizeHandle(self)
        horizontal_layout.addWidget(horizontal_resize_handle)

        outer_layout.addWidget(self.expanded_container)
        outer_layout.addWidget(self.collapsed_container)
        outer_layout.addWidget(self.horizontal_container)

        self.collapsed_container.hide()
        self.horizontal_container.hide()

        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.update_blink)
        self.blink_timer.start(550)

        self.set_active_gesture("NEUTRAL")

    def get_voice_card(self):
        if self.is_horizontal:
            return self.horizontal_cards.get("VOICE WAKE")

        return self.cards.get("VOICE WAKE")
    
    def position_voice_panel(self):
        voice_card = self.get_voice_card()
        if voice_card is None:
            return

        card_global = voice_card.mapToGlobal(voice_card.rect().topLeft())

        if self.is_horizontal:
            panel_x = card_global.x()
            panel_y = self.y() - self.voice_commands_panel.height() - 12
        else:
            self.voice_commands_panel.adjustSize()
            panel_x = card_global.x() - self.voice_commands_panel.width() - 10
            panel_y = card_global.y()

        screen = QApplication.primaryScreen().availableGeometry()
        panel_y = max(screen.top() + 10, panel_y)

        max_y = screen.bottom() - self.voice_commands_panel.height() - 10
        panel_y = min(panel_y, max_y)

        self.voice_commands_panel.move(panel_x, panel_y)

    def position_options_panel(self):
        self.options_panel.adjustSize()
        anchor_button = self.horizontal_options_button if self.is_horizontal else self.options_button

        button_global = anchor_button.mapToGlobal(anchor_button.rect().bottomLeft())

        panel_x = button_global.x() - self.options_panel.width() + anchor_button.width()

        if self.is_horizontal:
            button_top = anchor_button.mapToGlobal(anchor_button.rect().topLeft())
            panel_y = button_top.y() - self.options_panel.height() - 10
        else:
            panel_y = button_global.y() + 8

        screen = QApplication.primaryScreen().availableGeometry()
        panel_x = max(screen.left() + 10, panel_x)
        panel_x = min(panel_x, screen.right() - self.options_panel.width() - 10)
        panel_y = max(screen.top() + 10, panel_y)
        panel_y = min(panel_y, screen.bottom() - self.options_panel.height() - 10)

        self.options_panel.move(panel_x, panel_y)

    def toggle_options_panel(self):
        if self.options_panel.isVisible():
            self.options_panel.hide()
        else:
            self.position_options_panel()
            self.options_panel.show()
            self.options_panel.raise_()

    def toggle_voice_commands(self):
        voice_card = self.get_voice_card()

        if self.voice_commands_panel.isVisible():
            self.voice_commands_panel.hide()

            if voice_card and voice_card.expand_label is not None:
                voice_card.expand_label.setText("Commands  >")
        else:
            self.position_voice_panel()
            self.voice_commands_panel.show()
            self.voice_commands_panel.raise_()

            if voice_card and voice_card.expand_label is not None:
                voice_card.expand_label.setText("Commands  <")

    def reposition_to_right_edge(self):
        screen = QApplication.primaryScreen().availableGeometry()

        x = screen.x() + screen.width() - self.width()
        y = self.y()

        if y < screen.y():
            y = screen.y()

        if y + self.height() > screen.y() + screen.height():
            y = screen.y() + screen.height() - self.height()

        self.move(x, y)

        if self.voice_commands_panel.isVisible():
            self.position_voice_panel()

    def toggle_orientation(self):
        screen = QApplication.primaryScreen().availableGeometry()

        self.options_panel.hide()
        self.voice_commands_panel.hide()

        voice_card = self.get_voice_card()
        if voice_card and voice_card.expand_label is not None:
            voice_card.expand_label.setText("Commands  >")

        if not self.is_horizontal:
            self.is_horizontal = True
            self.vertical_height = self.height()

            self.expanded_container.hide()
            self.collapsed_container.hide()
            self.horizontal_container.show()

            horizontal_height = 174
            horizontal_width = min(max(self.vertical_height or 882, 882), screen.width() - 80)

            self.setMinimumWidth(620)
            self.setMaximumWidth(screen.width() - 40)
            self.setMinimumHeight(horizontal_height)
            self.setMaximumHeight(horizontal_height)

            x = screen.x() + (screen.width() - horizontal_width) // 2
            y = screen.y() + screen.height() - horizontal_height - 24

            self.setGeometry(x, y, horizontal_width, horizontal_height)

        else:
            self.is_horizontal = False

            self.horizontal_container.hide()

            self.setMinimumHeight(320)
            self.setMaximumHeight(screen.height())

            if self.is_collapsed:
                self.collapsed_container.show()
                self.expanded_container.hide()

                self.setMinimumWidth(self.collapsed_width)
                self.setMaximumWidth(self.collapsed_width)
                width = self.collapsed_width
            else:
                self.expanded_container.show()
                self.collapsed_container.hide()

                self.setMinimumWidth(self.expanded_width)
                self.setMaximumWidth(self.expanded_width)
                width = self.expanded_width

            restored_height = self.vertical_height or int(screen.height() * 0.85)

            x = screen.x() + screen.width() - width
            y = screen.y() + 40

            if y + restored_height > screen.y() + screen.height():
                restored_height = screen.height() - 40

            self.setGeometry(x, y, width, restored_height)
    
    def toggle_collapsed(self):
        screen = QApplication.primaryScreen().availableGeometry()
        right_edge = screen.x() + screen.width()
        current_height = self.height()
        current_y = self.y()

        self.is_collapsed = not self.is_collapsed

        if self.is_collapsed:
            self.restore_geometry_after_collapse = (
                self.x(),
                self.y(),
                self.width(),
                self.height()
            )

            self.options_panel.hide()
            self.voice_commands_panel.hide()

            voice_card = self.get_voice_card()
            if voice_card and voice_card.expand_label is not None:
                voice_card.expand_label.setText("Commands  >")

            self.expanded_container.hide()
            self.horizontal_container.hide()
            self.collapsed_container.show()
            self.collapsed_resize_handle.setVisible(not self.is_horizontal)
            
            self.setMinimumWidth(self.collapsed_width)
            self.setMaximumWidth(self.collapsed_width)
            self.setGeometry(
                right_edge - self.collapsed_width,
                current_y,
                self.collapsed_width,
                current_height
            )
        else:
            self.collapsed_container.hide()

            if self.is_horizontal:
                self.expanded_container.hide()
                self.horizontal_container.show()

                horizontal_height = 174

                self.setMinimumWidth(620)
                self.setMaximumWidth(screen.width() - 40)
                self.setMinimumHeight(horizontal_height)
                self.setMaximumHeight(horizontal_height)

                if self.restore_geometry_after_collapse is not None:
                    x, y, width, height = self.restore_geometry_after_collapse
                    height = horizontal_height
                else:
                    width = min(max(self.vertical_height or 882, 882), screen.width() - 80)
                    x = screen.x() + (screen.width() - width) // 2
                    y = screen.y() + screen.height() - horizontal_height - 24

                self.setGeometry(x, y, width, height)
            else:
                self.horizontal_container.hide()
                self.expanded_container.show()
                
                self.setMinimumHeight(320)
                self.setMaximumHeight(screen.height())
                self.setMinimumWidth(self.expanded_width)
                self.setMaximumWidth(self.expanded_width)
                self.setGeometry(
                    right_edge - self.expanded_width,
                    current_y,
                    self.expanded_width,
                    current_height
                )

            self.restore_geometry_after_collapse = None

        #self.reposition_to_right_edge()

    def set_active_gesture(self, gesture_name):
        self.active_gesture_name = gesture_name

        active_card = None
        active_horizontal_card = None

        for key, card in self.cards.items():
            if key == "VOICE WAKE":
                continue

            if key == gesture_name:
                card.set_active()
                active_card = card
            else:
                card.set_inactive()

        if hasattr(self, "horizontal_cards"):
            for key, card in self.horizontal_cards.items():
                if key == "VOICE WAKE":
                    continue

                if key == gesture_name:
                    card.set_active()
                    active_horizontal_card = card
                else:
                    card.set_inactive()

        if self.is_horizontal:
            if active_horizontal_card is not None:
                QTimer.singleShot(
                    0,
                    lambda: self.horizontal_scroll_area.ensureWidgetVisible(active_horizontal_card, 20, 0)
                )
        else:
            if active_card is not None and not self.is_collapsed:
                QTimer.singleShot(
                    0,
                    lambda: self.scroll_area.ensureWidgetVisible(active_card, 0, 20)
                )

    def update_blink(self):
        if self.active_gesture_name in self.cards:
            self.cards[self.active_gesture_name].set_active()

        if hasattr(self, "horizontal_cards") and self.active_gesture_name in self.horizontal_cards:
            self.horizontal_cards[self.active_gesture_name].set_active()

    def set_voice_status(self, status):
        status_lower = status.lower()

        if status == "Generating answer...":
            self.show_thinking_bubble()
            self.set_voice_card_text(
                "Nexa Chat",
                "Conversation in progress",
                auto_reset=False
            )
        else:
            self.hide_thinking_bubble()

        if status in ["Question answered", "Command executed", "Unknown command", "Search failed", "Listening cancelled"]:
            self.voice_card_reset_timer.start(2500)

        listening_statuses = [
            "listening...",
            "listening for command...",
            "listening for search text...",
            "listening for maps search...",
            "listening for youtube search...",
            "wake word detected",
            "voice requested"
        ]

        voice_card = self.get_voice_card()

        if voice_card is None:
            return

        if status_lower in listening_statuses:
            voice_card.set_active()

            if self.is_horizontal:
                QTimer.singleShot(
                    0,
                    lambda: self.horizontal_scroll_area.ensureWidgetVisible(voice_card, 20, 0)
                )
            elif not self.is_collapsed:
                QTimer.singleShot(
                    0,
                    lambda: self.scroll_area.ensureWidgetVisible(voice_card, 0, 20)
                )
        else:
            voice_card.set_inactive()

    def set_voice_card_text(self, title, description, auto_reset=False):
        self.voice_card_reset_timer.stop()

        for card in (
            self.cards.get("VOICE WAKE"),
            self.horizontal_cards.get("VOICE WAKE") if hasattr(self, "horizontal_cards") else None
        ):
            if card is None:
                continue

            card.title_label.setText(title)
            card.description_label.setText(description)

        if auto_reset:
            self.voice_card_reset_timer.start(3500)

    def reset_voice_card_text(self):
        self.voice_card_reset_timer.stop()
        self.set_voice_card_text(
            self.default_voice_title,
            self.default_voice_description
        )

    def set_last_voice(self, text):
        clean_text = " ".join(str(text).split())

        if not clean_text:
            self.reset_voice_card_text()
            return

        lower_text = clean_text.lower()
        reset_phrases = [
            "wake word ready",
            "starting camera",
            "listening timeout",
            "could not understand audio",
            "google could not understand",
            "search text was not recognized",
            "i could not understand",
            "speech service error",
            "microphone error"
        ]

        if any(phrase in lower_text for phrase in reset_phrases):
            self.reset_voice_card_text()
            return

        if lower_text == "nexa is ready":
            self.set_voice_card_text("Nexa is ready", 'Say "Hey Nexa"', auto_reset=True)
            return

        if lower_text == "wake word detected":
            self.set_voice_card_text("Wake word detected", "Listening for command")
            return

        if lower_text.startswith("question:"):
            self.set_voice_card_text("Nexa Chat", "Conversation in progress", auto_reset=False)
            return

        chat_phrases = [
            "what would you like to ask",
            "nexa chat response",
            "chat cancelled",
            "i could not understand the question",
            "openai api key is not configured",
            "i could not generate an answer right now"
        ]

        if any(phrase in lower_text for phrase in chat_phrases):
            self.set_voice_card_text("Nexa Chat", "Conversation in progress", auto_reset=True)
            return

        if len(clean_text) <= 28:
            self.set_voice_card_text(clean_text, "Voice update", auto_reset=True)
        else:
            self.set_voice_card_text("Voice update", clean_text, auto_reset=True)

    def start_voice_command(self):
        self.voice_requested.emit()
    
    def position_chat_panel(self):
        self.chat_panel.adjustSize()

        screen = QApplication.primaryScreen().availableGeometry()

        if self.is_horizontal:
            panel_x = self.x() + 20
            panel_y = self.y() - self.chat_panel.height() - 10
        else:
            panel_x = self.x() - self.chat_panel.width() - 10
            panel_y = self.y() + 20

        if panel_x < screen.x() + 10:
            panel_x = screen.x() + 10

        if panel_y < screen.y() + 10:
            panel_y = screen.y() + 10

        max_y = screen.bottom() - self.chat_panel.height() - 10
        panel_y = min(panel_y, max_y)

        self.chat_panel.move(panel_x, panel_y)


    def toggle_chat_panel(self):
        if self.chat_panel.isVisible():
            self.chat_panel.hide()
        else:
            self.position_chat_panel()
            self.chat_panel.show()
            self.chat_panel.raise_()

    def submit_chat_text(self):
        question = self.chat_input.text().strip()

        if not question:
            return

        self.chat_input.clear()
        self.chat_text_submitted.emit(question)


    def add_chat_message(self, sender, message):
        if self.chat_empty_label is not None:
            self.chat_empty_label.hide()

        timestamp = datetime.datetime.now().strftime("%H:%M")
        is_user = sender.lower() == "you"

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)

        message_stack = QVBoxLayout()
        message_stack.setContentsMargins(0, 0, 0, 0)
        message_stack.setSpacing(4)

        meta_label = QLabel(sender)
        meta_label.setStyleSheet(f"""
            QLabel {{
                color: {"#60a5fa" if is_user else "#93c5fd"};
                font-size: 10px;
                font-weight: 800;
                background: transparent;
                border: none;
            }}
        """)
        meta_label.setAlignment(Qt.AlignRight if is_user else Qt.AlignLeft)

        bubble = QFrame()
        bubble.setMaximumWidth(210)
        bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(8, 5, 8, 4)
        bubble_layout.setSpacing(1)
        bubble_layout.setSizeConstraint(QLayout.SetFixedSize)

        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        message_label.setMaximumWidth(184)
        message_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)
        message_label.setStyleSheet("""
            QLabel {
                color: #f9fafb;
                font-size: 12px;
                background: transparent;
                border: none;
            }
        """)

        time_label = QLabel(timestamp)
        time_label.setAlignment(Qt.AlignRight)
        time_label.setStyleSheet("""
            QLabel {
                color: #bfdbfe;
                font-size: 9px;
                background: transparent;
                border: none;
            }
        """)

        bubble_layout.addWidget(message_label)
        bubble_layout.addWidget(time_label)

        if is_user:
            bubble.setStyleSheet("""
                QFrame {
                    background-color: rgba(37, 99, 235, 210);
                    border: 1px solid rgba(96, 165, 250, 190);
                    border-radius: 14px;
                }
            """)
            message_stack.addWidget(meta_label)
            message_stack.addWidget(bubble)
            row_layout.addStretch()
            row_layout.addLayout(message_stack)
        else:
            bubble.setStyleSheet("""
                QFrame {
                    background-color: rgba(31, 41, 55, 205);
                    border: 1px solid rgba(75, 85, 99, 155);
                    border-radius: 14px;
                }
            """)
            time_label.setStyleSheet("""
                QLabel {
                    color: #94a3b8;
                    font-size: 9px;
                    background: transparent;
                    border: none;
                }
            """)
            message_stack.addWidget(meta_label)
            message_stack.addWidget(bubble)
            row_layout.addLayout(message_stack)
            row_layout.addStretch()

        stretch_item = self.chat_messages_layout.takeAt(
            self.chat_messages_layout.count() - 1
        )

        self.chat_messages_layout.addWidget(row)

        if stretch_item is not None:
            self.chat_messages_layout.addItem(stretch_item)

        QTimer.singleShot(0, lambda: self.finalize_chat_bubble(row, bubble))

    def finalize_chat_bubble(self, row, bubble):
        bubble.adjustSize()
        bubble.setMinimumHeight(bubble.sizeHint().height())
        row.adjustSize()
        self.chat_messages_layout.invalidate()
        self.scroll_chat_to_bottom()

    def show_thinking_bubble(self):
        if self.thinking_row is not None:
            return

        if self.chat_empty_label is not None:
            self.chat_empty_label.hide()

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)

        message_stack = QVBoxLayout()
        message_stack.setContentsMargins(0, 0, 0, 0)
        message_stack.setSpacing(4)

        thinking_meta = QLabel("Nexa")
        thinking_meta.setStyleSheet("""
            QLabel {
                color: #93c5fd;
                font-size: 10px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        self.thinking_label = QLabel("•")
        self.thinking_label.setWordWrap(True)
        self.thinking_label.setFixedWidth(76)
        self.thinking_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.thinking_label.setStyleSheet("""
            QLabel {
                color: #60a5fa;
                font-size: 18px;
                font-weight: 800;
                background-color: rgba(31, 41, 55, 205);
                border: 1px solid rgba(75, 85, 99, 155);
                border-radius: 14px;
                padding: 8px;
            }
        """)

        message_stack.addWidget(thinking_meta)
        message_stack.addWidget(self.thinking_label)
        row_layout.addLayout(message_stack)
        row_layout.addStretch()

        stretch_item = self.chat_messages_layout.takeAt(
            self.chat_messages_layout.count() - 1
        )

        self.chat_messages_layout.addWidget(row)

        if stretch_item is not None:
            self.chat_messages_layout.addItem(stretch_item)

        self.thinking_row = row
        self.thinking_dots = 1
        self.thinking_timer.start(500)

        QTimer.singleShot(0, self.scroll_chat_to_bottom)


    def update_thinking_bubble(self):
        if self.thinking_label is None:
            return

        self.thinking_dots += 1
        if self.thinking_dots > 3:
            self.thinking_dots = 1

        dots = " ".join(["•"] * self.thinking_dots)
        self.thinking_label.setText(dots)


    def hide_thinking_bubble(self):
        if self.thinking_row is None:
            return

        self.thinking_timer.stop()

        self.chat_messages_layout.removeWidget(self.thinking_row)
        self.thinking_row.deleteLater()

        self.thinking_row = None
        self.thinking_label = None
        self.thinking_dots = 0
    
    def scroll_chat_to_bottom(self):
        scrollbar = self.chat_scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self.voice_commands_panel.isVisible():
            self.position_voice_panel()

        if self.options_panel.isVisible():
            self.position_options_panel()

        if self.chat_panel.isVisible():
            self.position_chat_panel()
    
    def is_drag_blocked_widget(self, widget):
        while widget is not None:
            if isinstance(widget, (QPushButton, QLineEdit, QScrollArea, ModernGestureCard, VerticalResizeHandle)):
                return True

            widget = widget.parentWidget()

        return False


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            clicked_widget = self.childAt(event.position().toPoint())

            if not self.is_drag_blocked_widget(clicked_widget):
                self.dragging_window = True
                self.drag_start_position = event.globalPosition().toPoint()
                self.window_start_position = self.pos()
                event.accept()
                return

        super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        if self.dragging_window and self.drag_start_position is not None:
            current_position = event.globalPosition().toPoint()
            delta = current_position - self.drag_start_position

            self.move(self.window_start_position + delta)

            if self.voice_commands_panel.isVisible():
                self.position_voice_panel()

            if self.options_panel.isVisible():
                self.position_options_panel()

            if self.chat_panel.isVisible():
                self.position_chat_panel()

            event.accept()
            return

        super().mouseMoveEvent(event)


    def mouseReleaseEvent(self, event):
        self.dragging_window = False
        self.drag_start_position = None
        self.window_start_position = None

        super().mouseReleaseEvent(event)
        
    def closeEvent(self, event):
        self.options_panel.hide()
        self.voice_commands_panel.hide()
        self.chat_panel.hide()
        self.close_requested.emit()
        event.accept()
