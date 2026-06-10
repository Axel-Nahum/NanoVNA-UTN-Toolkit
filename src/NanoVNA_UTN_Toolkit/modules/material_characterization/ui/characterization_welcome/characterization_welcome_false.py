import sys
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class CharacterizationFalse(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Material Characterization")
        self.resize(900, 500)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("WORKING IN PROGRESS")
        font = QFont()
        font.setPointSize(28)
        font.setBold(True)
        label.setFont(font)
        label.setAlignment(Qt.AlignCenter)

        layout.addWidget(label)
        self.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec())