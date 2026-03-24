from GUI_interfaces.Login import *
from GUIFunctions import *

class LoginController:
    def __init__(self):
        self.ui = LoginUI()

        self.ui.username_input.returnPressed.connect(
            self.ui.password_input.setFocus
        )

        self.ui.password_input.returnPressed.connect(self.handle_login)

        self.ui.show()
    
    def handle_login(self):
        username = self.ui.username_input.text()
        password = self.ui.password_input.text()

        if not username or not password:
            print("Missing a field")
            return
        
        UserLogin(username, password)