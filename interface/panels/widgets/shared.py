# interface/panels/widgets/shared.py
import json
import os
from pathlib import Path
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

def write_json_atomic(path: Path, data: dict) -> None:
    """Safely serializes configuration dictionaries via an atomic file descriptor swap."""
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
        file.write("\n")
    os.replace(temporary_path, path)

def build_card(title: str) -> tuple[QWidget, QVBoxLayout]:
    """Generates a perfectly styled, dark-mode technical control container layout frame."""
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

    header = QLabel(title.upper())
    header.setStyleSheet("""
        color: #ffaa00;
        font-weight: bold;
        font-family: 'Consolas', monospace;
        border: none;
    """)
    layout.addWidget(header)

    return card, layout
