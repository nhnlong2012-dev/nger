from PyQt6.QWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6 import uic
import sys
import os

class Login(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("Login.ui", self)
        self.createAccount.clicked.connect(self.show_register)
        self.btnLogin.clicked.connect(self.check_login)
        self.msg_box = QMessageBox()

    def check_login(self):
        email = self.Email.text()
        password = self.Password.text()
        if email == "admin" and password == "admin":
            main.show()
            self.close()

class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("Main.ui", self)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = Login()
    register = Register()
    main = Main()
    login.show()
    app.exec()

class Register(QMainWindow):
    def __init(self):
        super().__init__()
        uic.loadUi("Register.ui", self)
        self.btnRegister.clicked.connect(self.register_user)
        self.loginAccount.clicked.connect(self.back_to_login)
        self.msg_box = QMessageBox()

    def back_to_login(self):
        login.show()
        self.close()

    def show_register(self):
        register.show()
        self.close()