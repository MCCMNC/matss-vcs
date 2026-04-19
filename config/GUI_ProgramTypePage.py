from GUIFunctions import *
class ProgramTypePage(QWidget):
    def __init__(self, loginUser, program_choice_callback):
        super().__init__()
        self.loginUser = loginUser  # Store the user to pass back later
        self.program_choice_callback = program_choice_callback

        # Main layout handles the centering relative to the entire window
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Container is now flexible instead of fixed
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.setSpacing(20)

        # --- NEW BUTTON CODE ---
        self.dashboard_btn = QPushButton("Open Studio Management")
        self.dashboard_btn.setFixedSize(200, 50)
        self.dashboard_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
        """)
        self.alt_dashboard_btn = QPushButton("Open Code Management")
        self.alt_dashboard_btn.setFixedSize(200, 50)
        self.alt_dashboard_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #58a6ff;
                        color: #0d1117;
                        font-weight: bold;
                        border-radius: 5px;
                        border: 1px solid #30363d;
                        font-size: 14px;
                    }
                    QPushButton:hover { background-color: #79c0ff; }
                """)
        # Connect to the choice handler
        self.dashboard_btn.clicked.connect(self.handle_studioChoice)
        self.alt_dashboard_btn.clicked.connect(self.handle_codeChoice)

        container_layout.addWidget(self.dashboard_btn)
        container_layout.addWidget(self.alt_dashboard_btn)
        # -----------------------

        main_layout.addWidget(container)

    def handle_codeChoice(self):
        # Trigger the callback with the stored user object
        if self.program_choice_callback:
            self.program_choice_callback(self.loginUser,"Code")
    def handle_studioChoice(self):
        # Trigger the callback with the stored user object
        if self.program_choice_callback:
            self.program_choice_callback(self.loginUser)

    def showEvent(self, event):
        super().showEvent(event)