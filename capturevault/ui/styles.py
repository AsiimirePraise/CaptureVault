"""Application stylesheet - grayscale with white color scheme."""

LIGHT_STYLE = """
QMainWindow, QDialog, QWidget {
    background-color: #FFFFFF;
    color: #2B2B2B;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background-color: #FAFAFA;
    border: 1px solid #D0D0D0;
    border-radius: 6px;
    padding: 8px 12px;
    color: #2B2B2B;
    selection-background-color: #B0B0B0;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #808080;
}

QPushButton {
    background-color: #F0F0F0;
    border: 1px solid #C8C8C8;
    border-radius: 6px;
    padding: 8px 16px;
    color: #2B2B2B;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #E4E4E4;
    border-color: #A8A8A8;
}

QPushButton:pressed {
    background-color: #D8D8D8;
}

QPushButton#primaryButton {
    background-color: #4A4A4A;
    color: #FFFFFF;
    border: 1px solid #3A3A3A;
}

QPushButton#primaryButton:hover {
    background-color: #5A5A5A;
}

QListWidget, QTreeWidget, QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    alternate-background-color: #F8F8F8;
    gridline-color: #E8E8E8;
    selection-background-color: #D4D4D4;
    selection-color: #1A1A1A;
    outline: none;
}

QTableWidget::item {
    padding: 6px 8px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #D4D4D4;
    color: #1A1A1A;
}

QTableWidget::item:hover {
    background-color: #ECECEC;
}

QTableWidget::item:focus {
    outline: none;
    border: none;
}

QListWidget::item, QTreeWidget::item {
    padding: 6px;
    border-radius: 4px;
}

QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #E0E0E0;
    color: #1A1A1A;
}

QListWidget::item:hover, QTreeWidget::item:hover {
    background-color: #F0F0F0;
}

QHeaderView::section {
    background-color: #F5F5F5;
    color: #4A4A4A;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #D8D8D8;
    font-weight: 600;
}

QScrollBar:vertical {
    background: #F5F5F5;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #C0C0C0;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #A0A0A0;
}

QMenu {
    background-color: #FFFFFF;
    border: 1px solid #D0D0D0;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #E8E8E8;
}

QStatusBar {
    background-color: #F5F5F5;
    color: #6A6A6A;
    border-top: 1px solid #E0E0E0;
}

QProgressBar {
    border: 1px solid #D0D0D0;
    border-radius: 4px;
    background: #F5F5F5;
    text-align: center;
    color: #4A4A4A;
}

QProgressBar::chunk {
    background-color: #808080;
    border-radius: 3px;
}

QLabel#titleLabel {
    font-size: 22px;
    font-weight: 600;
    color: #1A1A1A;
}

QLabel#subtitleLabel {
    font-size: 14px;
    color: #6A6A6A;
}

QLabel#statValue {
    font-size: 28px;
    font-weight: 700;
    color: #2B2B2B;
}

QLabel#statLabel {
    font-size: 12px;
    color: #8A8A8A;
    text-transform: uppercase;
}

QFrame#sidebar {
    background-color: #F7F7F7;
    border-right: 1px solid #E0E0E0;
}

QFrame#searchBarFrame {
    background-color: #FAFAFA;
    border-bottom: 1px solid #E0E0E0;
}

QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #E8E8E8;
    border-radius: 8px;
}

QLineEdit#searchInput {
    font-size: 16px;
    padding: 12px 16px;
    border-radius: 8px;
    background-color: #FFFFFF;
}
"""

DARK_STYLE = """
QMainWindow, QDialog, QWidget {
    background-color: #1E1E1E;
    color: #E8E8E8;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background-color: #2A2A2A;
    border: 1px solid #404040;
    border-radius: 6px;
    padding: 8px 12px;
    color: #E8E8E8;
}

QPushButton {
    background-color: #3A3A3A;
    border: 1px solid #505050;
    border-radius: 6px;
    padding: 8px 16px;
    color: #E8E8E8;
}

QPushButton:hover {
    background-color: #4A4A4A;
}

QPushButton#primaryButton {
    background-color: #D0D0D0;
    color: #1A1A1A;
}

QListWidget, QTreeWidget, QTableWidget {
    background-color: #252525;
    border: 1px solid #404040;
    color: #E8E8E8;
    alternate-background-color: #2A2A2A;
    selection-background-color: #404040;
    selection-color: #FFFFFF;
    outline: none;
}

QTableWidget::item {
    padding: 6px 8px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #404040;
    color: #FFFFFF;
}

QTableWidget::item:hover {
    background-color: #333333;
}

QTableWidget::item:focus {
    outline: none;
    border: none;
}

QHeaderView::section {
    background-color: #2A2A2A;
    color: #C0C0C0;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #404040;
    font-weight: 600;
}

QFrame#sidebar {
    background-color: #252525;
    border-right: 1px solid #404040;
}

QFrame#searchBarFrame {
    background-color: #2A2A2A;
    border-bottom: 1px solid #404040;
}

QLineEdit#searchInput {
    font-size: 16px;
    padding: 12px 16px;
    background-color: #1E1E1E;
    color: #E8E8E8;
}
"""


def get_stylesheet(theme: str) -> str:
    from capturevault.constants import THEME_DARK
    return DARK_STYLE if theme == THEME_DARK else LIGHT_STYLE
