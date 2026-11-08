# interface\panels\widgets\buildcard.py
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


def build_card(title: str) -> tuple[QWidget, QVBoxLayout]:
    card = QWidget()

    card.setStyleSheet("""
            QWidget {
                background-color: #141923;
                border: 1px solid #1f2430;
                border-radius: 6px;
            }
        """)

    layout = QVBoxLayout(card)
    layout.setContentsMargins(15, 15, 15, 15)
    layout.setSpacing(10)

    header = QLabel(title)

    header.setStyleSheet("""
            color: #ffaa00;
            font-weight: bold;
            font-family: Consolas;
            border: none;
        """)

    layout.addWidget(header)

    return card, layout