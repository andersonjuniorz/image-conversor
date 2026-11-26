from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QLabel, QPushButton, QTextEdit, QVBoxLayout,
)


# Creates a card frame with its vertical layout. Used by every section.
def make_card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(24, 22, 24, 22)
    layout.setSpacing(14)
    return frame, layout


# Creates a bold title label for a section.
def section(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("sectionTitle")
    return label


# Creates a small gray label for hints and secondary text.
def muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("muted")
    label.setWordWrap(True)
    return label


# Box that shows a big number with a caption below it, used in the summary.
class StatBox(QFrame):
    # Build the box with its value label and caption.
    def __init__(self, caption: str):
        super().__init__()
        self.setObjectName("statBox")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)
        self.value = QLabel("0")          # the big number
        self.value.setObjectName("statValue")
        layout.addWidget(self.value)
        layout.addWidget(muted(caption))  # text below the number

    # Update the number and, optionally, its color.
    def set_value(self, text: str, color: str | None = None):
        self.value.setText(text)
        # Apply the color only when one is given; otherwise keep the theme color.
        self.value.setStyleSheet(f"color: {color};" if color else "")


# Read-only window that shows the conversion report.
class ReportDialog(QDialog):
    # Build the dialog with the report text and a close button.
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Relatório")
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        view = QTextEdit()          # text area for the report
        view.setReadOnly(True)      # the user can read but not edit it
        view.setPlainText(text)
        layout.addWidget(view)
        close = QPushButton("Fechar")
        close.setObjectName("secondary")
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.accept)  # closes the dialog
        layout.addWidget(close, 0, Qt.AlignRight)


# Button used for formats and for Confirmar. Shows hover feedback on its own.
class FormatButton(QPushButton):
    """Button with hover handled by the widget itself. Can be selectable."""

    # Set up the button style, cursor and hover support.
    def __init__(self, text: str, parent=None, checkable: bool = True):
        super().__init__(text, parent)
        self.setObjectName("format")          # style rule name in the theme
        self.setCursor(Qt.PointingHandCursor) # hand cursor on hover
        self.setAttribute(Qt.WA_Hover, True)  # enable hover events
        self.setCheckable(checkable)          # allow the button to stay selected

    # Forces Qt to apply the QSS again after a dynamic property changes.
    def _repolish(self):
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    # Called when the mouse enters the button. Sets the hover property.
    def enterEvent(self, event):
        self.setProperty("hovered", True)
        self._repolish()
        super().enterEvent(event)

    # Called when the mouse leaves the button. Clears the hover property.
    def leaveEvent(self, event):
        self.setProperty("hovered", False)
        self._repolish()
        super().leaveEvent(event)
