from GUIFunctions import *


class LoginPage(QWidget):
    def __init__(self, login_success_callback):
        super().__init__()
        self.login_success_callback = login_success_callback

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.setSpacing(20)

        # --- LOGO ---
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(BASE_DIR, "Assets", "MAT Software Solutions Logo.png")
        self.logo = QLabel()
        self.logo.setFixedSize(320, 320)
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            self.logo.setPixmap(pixmap.scaled(self.logo.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation))

        # --- INPUTS ---
        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.username.setFixedSize(350, 40)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setFixedSize(350, 40)

        # --- BUTTONS ---
        self.login_btn = QPushButton("Login")
        self.login_btn.setFixedSize(200, 40)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Register Link Style
        self.register_btn = QPushButton("Register New Account")
        self.register_btn.setFixedSize(200, 40)  # Matched size with Login for symmetry
        self.register_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # --- SIGNALS ---
        self.login_btn.clicked.connect(self.handleLogin)
        self.register_btn.clicked.connect(self.handleRegister)
        self.username.returnPressed.connect(self.password.setFocus)
        self.password.returnPressed.connect(self.handleLogin)

        # --- LAYOUT ASSEMBLY ---
        container_layout.addWidget(self.logo, alignment=Qt.AlignmentFlag.AlignCenter)
        container_layout.addSpacing(10)
        container_layout.addWidget(self.username, alignment=Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.password, alignment=Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.login_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.register_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(container)

    def handleLogin(self):
        # Existing login logic
        user = guiUserLogin(self.username.text(), self.password.text())
        if user is not None:
            self.username.clear()
            self.password.clear()
            self.login_success_callback(user)
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid Credentials")
            self.password.clear()

    def handleRegister(self):
        # 1. Gather Info via Dialogs
        user, ok1 = QInputDialog.getText(self, "Register", "Enter new Username:")
        if not ok1 or not user: return

        email, ok2 = QInputDialog.getText(self, "Register", "Enter Email (Optional):")
        if not ok2: return  # User cancelled

        pwd, ok3 = QInputDialog.getText(self, "Register", "Enter Password:", QLineEdit.EchoMode.Password)
        if not ok3 or not pwd: return

        # 2. API Call
        import client_api  # Ensure this is imported
        response = client_api.register_request(user, email, pwd)

        # 3. Handle Response
        if response and 'error' not in response:
            QMessageBox.information(self, "Success", f"User {user} registered successfully! You can now login.")
        else:
            err = response.get('error', 'Server unreachable') if response else "Connection Error"
            QMessageBox.critical(self, "Error", f"Registration Failed: {err}")