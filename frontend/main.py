import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QMessageBox, QFormLayout, QComboBox, QTextEdit, QHeaderView
)

import api
from api import ApiError
from session import UserSession


class LoginWindow(QWidget):
    def __init__(self, on_login_success):
        super().__init__()
        self.on_login_success = on_login_success
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Autentificare")
        self.resize(400, 250)

        layout = QVBoxLayout()

        title = QLabel("Autentificare Sistem")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px;")
        layout.addWidget(title)

        form_layout = QFormLayout()
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Introduceti utilizatorul")
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("Introduceti parola")
        self.pass_input.returnPressed.connect(self.handle_login)

        form_layout.addRow("Utilizator:", self.user_input)
        form_layout.addRow("Parola:", self.pass_input)
        layout.addLayout(form_layout)

        self.login_btn = QPushButton("Conectare")
        self.login_btn.setStyleSheet("background-color: #2b5797; color: white; font-weight: bold; padding: 8px;")
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)

        self.setLayout(layout)

    def handle_login(self):
        username = self.user_input.text().strip()
        password = self.pass_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Eroare", "Completati toate campurile")
            return

        try:
            data = api.post("/login", json={"nume_utilizator": username, "parola": password})
        except ApiError as e:
            QMessageBox.critical(self, "Acces esuat", str(e))
            return

        UserSession.get_instance().set_session(data)
        self.on_login_success()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.session = UserSession.get_instance()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Service Auto & ITP")
        self.resize(900, 650)

        central_widget = QWidget()
        main_layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        conex_info = f"Logat ca: <b>{self.session.nume_utilizator}</b> | Rol: <b>{self.session.rol}</b>"
        welcome_lbl = QLabel(conex_info)
        logout_btn = QPushButton("Deconectare")
        logout_btn.clicked.connect(self.logout)
        header_layout.addWidget(welcome_lbl)
        header_layout.addStretch()
        header_layout.addWidget(logout_btn)
        main_layout.addLayout(header_layout)
        
        self.tabs = QTabWidget()
        rol = self.session.rol
        if rol == "OPERATOR":
            self.tabs.addTab(ClientiTab(), "Clienti & Vehicule")
            self.tabs.addTab(ComenziTab(), "Comenzi & Piese")
            self.tabs.addTab(AiTab(), "Diagnoza AI")
        elif rol == "INSPECTOR":
            self.tabs.addTab(ItpTab(), "Statie ITP")
        else:  # ADMINISTRATOR
            placeholder = QLabel("Administrare utilizatori - urmeaza")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabs.addTab(placeholder, "Utilizatori")

        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def logout(self):
        self.session.clear()
        self.close()
        python = sys.executable
        os.execl(python, python, *sys.argv)


class ClientiTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_clienti()

    def init_ui(self):
        layout = QVBoxLayout()

        form_layout = QHBoxLayout()
        self.nume_in = QLineEdit()
        self.nume_in.setPlaceholderText("Nume")
        self.prenume_in = QLineEdit()
        self.prenume_in.setPlaceholderText("Prenume")
        self.tel_in = QLineEdit()
        self.tel_in.setPlaceholderText("Telefon")

        add_btn = QPushButton("Adauga Client")
        add_btn.clicked.connect(self.add_client)

        form_layout.addWidget(self.nume_in)
        form_layout.addWidget(self.prenume_in)
        form_layout.addWidget(self.tel_in)
        form_layout.addWidget(add_btn)
        layout.addLayout(form_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Nume", "Prenume", "Telefon"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load_clienti(self):
        try:
            clienti = api.get("/clienti")
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return

        self.table.setRowCount(len(clienti))
        for row, c in enumerate(clienti):
            self.table.setItem(row, 0, QTableWidgetItem(str(c["id_client"])))
            self.table.setItem(row, 1, QTableWidgetItem(c["nume"]))
            self.table.setItem(row, 2, QTableWidgetItem(c["prenume"]))
            self.table.setItem(row, 3, QTableWidgetItem(c["telefon"]))

    def add_client(self):
        nume = self.nume_in.text().strip()
        prenume = self.prenume_in.text().strip()
        tel = self.tel_in.text().strip()

        if not nume or not prenume or not tel:
            QMessageBox.warning(self, "Atentie", "Completati nume, prenume si telefon")
            return

        try:
            api.post("/clienti", json={"nume": nume, "prenume": prenume, "telefon": tel})
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return

        QMessageBox.information(self, "Succes", "Client adaugat cu succes")
        self.nume_in.clear()
        self.prenume_in.clear()
        self.tel_in.clear()
        self.load_clienti()


class ComenziTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Gestionare Comenzi & Piese</b><br>Se deschid comenzi si se adauga piese din stoc"))

        form = QFormLayout()
        self.vehicul_id_in = QLineEdit()
        self.vehicul_id_in.setPlaceholderText("ID Vehicul")
        self.km_in = QLineEdit()
        self.km_in.setPlaceholderText("Kilometraj")
        self.reclamatie_in = QTextEdit()
        self.reclamatie_in.setMaximumHeight(60)

        form.addRow("ID Vehicul:", self.vehicul_id_in)
        form.addRow("Km Intrare:", self.km_in)
        form.addRow("Reclamatie:", self.reclamatie_in)

        btn = QPushButton("Deschide comanda noua")
        btn.setStyleSheet("background-color: #2b5797; color: white; font-weight: bold;")
        btn.clicked.connect(self.creeaza_comanda)

        layout.addLayout(form)
        layout.addWidget(btn)
        layout.addStretch()
        self.setLayout(layout)

    def creeaza_comanda(self):
        try:
            payload = {
                "km_intrare": int(self.km_in.text().strip()),
                "reclamatie": self.reclamatie_in.toPlainText().strip() or None,
                "id_vehicul": int(self.vehicul_id_in.text().strip()),
            }
        except ValueError:
            QMessageBox.warning(self, "Eroare", "ID vehicul si km trebuie sa fie numere intregi")
            return

        try:
            data = api.post("/comenzi", json=payload)
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return

        QMessageBox.information(self, "Succes", f"Comanda deschisa cu ID-ul: {data['id_comanda']}")


class ItpTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Inspectie tehnica periodica</b>"))

        form = QFormLayout()
        self.vid_itp = QLineEdit()
        self.km_itp = QLineEdit()
        self.co_itp = QLineEdit()
        self.frane_itp = QLineEdit()
        self.conv_itp = QLineEdit()
        self.rezultat_itp = QComboBox()
        self.rezultat_itp.addItems(["ADMIS", "RESPINS"])

        form.addRow("ID Vehicul:", self.vid_itp)
        form.addRow("Kilometraj:", self.km_itp)
        form.addRow("Emisii CO (%):", self.co_itp)
        form.addRow("Eficienta franare (%):", self.frane_itp)
        form.addRow("Convergenta:", self.conv_itp)
        form.addRow("Decizie inspector:", self.rezultat_itp)

        btn = QPushButton("Inregistreaza inspectia")
        btn.setStyleSheet("background-color: #008a00; color: white; font-weight: bold;")
        btn.clicked.connect(self.inregistreaza_itp)

        layout.addLayout(form)
        layout.addWidget(btn)
        layout.addStretch()
        self.setLayout(layout)

    @staticmethod
    def _float_sau_none(text: str):
        text = text.strip()
        return float(text) if text else None

    def inregistreaza_itp(self):
        try:
            payload = {
                "km": int(self.km_itp.text().strip()),
                "emisii_co": self._float_sau_none(self.co_itp.text()),
                "eficienta_franare": self._float_sau_none(self.frane_itp.text()),
                "convergenta": self._float_sau_none(self.conv_itp.text()),
                "rezultat": self.rezultat_itp.currentText(),
                "id_vehicul": int(self.vid_itp.text().strip()),
            }
        except ValueError:
            QMessageBox.warning(self, "Eroare", "Verificati datele numerice introduse")
            return

        try:
            data = api.post("/itp", json=payload)
        except ApiError as e:
            QMessageBox.critical(self, "Inspectie refuzata", str(e))
            return

        exp = data.get("data_expirare") or "-"
        QMessageBox.information(
            self, "Inspectie inregistrata",
            f"Rezultat: {data['rezultat']}\nData expirare: {exp}"
        )


class AiTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Diagnoza & Predictie Mentenanta</b>"))

        form = QHBoxLayout()
        self.vid_ai = QLineEdit()
        self.vid_ai.setPlaceholderText("ID Vehicul")
        btn = QPushButton("Ruleaza Diagnoza AI")
        btn.setStyleSheet("background-color: #68217a; color: white; font-weight: bold;")
        btn.clicked.connect(self.ruleaza_ai)

        form.addWidget(self.vid_ai)
        form.addWidget(btn)
        layout.addLayout(form)

        self.rezultat_box = QTextEdit()
        self.rezultat_box.setReadOnly(True)
        layout.addWidget(self.rezultat_box)

        self.setLayout(layout)

    def ruleaza_ai(self):
        try:
            vid = int(self.vid_ai.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Eroare", "ID vehicul invalid")
            return

        try:
            data = api.post(f"/diagnoza/{vid}")
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return

        rec = data["recomandare"]
        self.rezultat_box.setText(
            f"RECOMANDARE\n"
            f"Categorie recomandata: {rec['categorie']}\n"
            f"Scor risc: {rec['scor_risc']:.2f}\n"
            f"Algoritm: {rec['algoritm']}\n"
            f"Data generare: {rec['data_generare']}\n"
        )


def main():
    app = QApplication(sys.argv)

    def show_main():
        global main_win
        main_win = MainWindow()
        main_win.show()
        login_win.close()

    login_win = LoginWindow(show_main)
    login_win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()