from PyQt6.QtWidgets import QWidget, QListWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

class ProjectListUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Project List")

        self.audit_log = QListWidget()

        self.audit_log.addItems([
            "placeholder",
            "placeholder",
            "placeholder"
        ])

        self.repo_container = QWidget()
        self.repo_layout = QVBoxLayout()

        self.repo_container.setLayout(self.repo_layout)

        self.repo_scroll = QScrollArea()
        self.repo_scroll.setWidgetResizable(True)
        self.repo_scroll.setWidget(self.repo_container)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.audit_log)
        main_layout.addWidget(self.repo_scroll)

        self.setLayout(main_layout)


    def add_repository(self, repo_name):
        button = QPushButton(repo_name)
        self.repo_layout.addWidget(button)
        self.repo_layout.addWidget(button)
        return button 