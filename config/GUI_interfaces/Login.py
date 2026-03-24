from PyQt6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout

class LoginUI(QWidget):
    def __init__(self):
        super().__init__()

        #logo here

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Username"))
        layout.addWidget(self.username_input)
        layout.addWidget(QLabel("Password"))
        layout.addWidget(self.password_input)

        self.setLayout(layout)