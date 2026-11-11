import sys
import httpx
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QMessageBox, QFormLayout, QComboBox, QTextEdit, QHeaderView
)
from PyQt6.QtCore import Qt
from session import UserSession

API_BASE_URL = "http://127.0.0.1:8000/api"

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
            response = httpx.post(f"{API_BASE_URL}/login", json={"nume_utilizator": username, "parola": password})
            if response.status_code == 200:
                data = response.json()
                UserSession.get_instance().set_session(data)
                self.on_login_success()
            else:
                detail = response.json().get("detail", "Eroare de autentificare")
                QMessageBox.critical(self, "Acces esuat", detail)
        except httpx.ConnectError:
            QMessageBox.critical(self, "Eroare Conexiune", "Nu sa putut conecta la serverul backend")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.session = UserSession.get_instance()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Service Auto & ITP")
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
        self.tabs.addTab(ClientiTab(), "Clienti & Vehicule")
        self.tabs.addTab(ComenziTab(), "Comenzi & Piese")
        self.tabs.addTab(ItpTab(), "Statie ITP")
        self.tabs.addTab(AiTab(), "Diagnoza AI")
        
        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def logout(self):
        self.session.clear()
        self.close()
        python = sys.executable
        import os
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
            res = httpx.get(f"{API_BASE_URL}/clienti")
            if res.status_code == 200:
                clienti = res.json()
                self.table.setRowCount(len(clienti))
                for row, c in enumerate(clienti):
                    self.table.setItem(row, 0, QTableWidgetItem(str(c["id_client"])))
                    self.table.setItem(row, 1, QTableWidgetItem(c["nume"]))
                    self.table.setItem(row, 2, QTableWidgetItem(c["prenume"]))
                    self.table.setItem(row, 3, QTableWidgetItem(c["telefon"]))
        except Exception as e:
            print("Eroare incarcare clienti:", e)

    def add_client(self):
        nume = self.nume_in.text().strip()
        prenume = self.prenume_in.text().strip()
        tel = self.tel_in.text().strip()
        
        if not nume or not prenume or not tel:
            QMessageBox.warning(self, "Atentie", "completati nume, prenume si telefon")
            return
            
        try:
            res = httpx.post(f"{API_BASE_URL}/clienti", json={"nume": nume, "prenume": prenume, "telefon": tel})
            if res.status_code == 201:
                QMessageBox.information(self, "Succes", "Client adaugat cu succes")
                self.nume_in.clear()
                self.prenume_in.clear()
                self.tel_in.clear()
                self.load_clienti()
            else:
                QMessageBox.critical(self, "Eroare", res.text)
        except Exception as e:
            QMessageBox.critical(self, "Eroare", str(e))


class ComenziTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Gestionare Comenzi & Piese</b><br>Se deschid comenzi si se adaugă piese din stoc"))
        
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
        session = UserSession.get_instance()
        try:
            vid = int(self.vehicul_id_in.text().strip())
            km = int(self.km_in.text().strip())
            reclamatie = self.reclamatie_in.toPlainText().strip()
            
            payload = {
                "km_intrare": km,
                "reclamatie": reclamatie,
                "id_vehicul": vid,
                "id_operator": session.id_angajat if session.id_angajat else 1
            }
            
            res = httpx.post(f"{API_BASE_URL}/comenzi", json=payload)
            if res.status_code == 201:
                data = res.json()
                QMessageBox.information(self, "Succes", f"Comanda deschisa cu ID-ul: {data['id_comanda']}")
            else:
                QMessageBox.critical(self, "Eroare", res.text)
        except ValueError:
            QMessageBox.warning(self, "Eroare", "ID vehicul si km trebuie sa fie numere intregi")
        except Exception as e:
            QMessageBox.critical(self, "Eroare", str(e))


class ItpTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>ITP</b>"))
        
        form = QFormLayout()
        self.vid_itp = QLineEdit()
        self.km_itp = QLineEdit()
        self.noxe_itp = QLineEdit()
        self.frane_itp = QLineEdit()
        
        form.addRow("ID Vehicul:", self.vid_itp)
        form.addRow("Kilometraj:", self.km_itp)
        form.addRow("Emisii CO (%):", self.noxe_itp)
        form.addRow("Eficienta Franare (%):", self.frane_itp)
        
        btn = QPushButton("Inregistreaza ITP & Verifica")
        btn.setStyleSheet("background-color: #008a00; color: white; font-weight: bold;")
        btn.clicked.connect(self.inregistreaza_itp)
        
        layout.addLayout(form)
        layout.addWidget(btn)
        layout.addStretch()
        self.setLayout(layout)

    def inregistreaza_itp(self):
        session = UserSession.get_instance()
        try:
            payload = {
                "km": int(self.km_itp.text().strip()),
                "emisii_co": float(self.noxe_itp.text().strip()) if self.noxe_itp.text() else None,
                "eficienta_franare": float(self.frane_itp.text().strip()) if self.frane_itp.text() else None,
                "convergenta": 0.0,
                "id_vehicul": int(self.vid_itp.text().strip()),
                "id_inspector": session.id_angajat if session.id_angajat else 1
            }
            
            res = httpx.post(f"{API_BASE_URL}/itp", json=payload)
            if res.status_code == 201:
                data = res.json()
                rez = data["rezultat"]
                exp = data.get("data_expirare", "N/A")
                color = "green" if rez == "ADMIS" else "red"
                QMessageBox.information(self, "Rezultat ITP", f"Rezultat: <b style='color:{color};'>{rez}</b>\nData Expirare: {exp}")
            else:
                QMessageBox.critical(self, "Eroare", res.text)
        except ValueError:
            QMessageBox.warning(self, "Eroare", "Verificati datele numerice introduse")
        except Exception as e:
            QMessageBox.critical(self, "Eroare", str(e))


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
            res = httpx.post(f"{API_BASE_URL}/diagnoza/{vid}")
            if res.status_code == 200:
                data = res.json()
                rec = data["recomandare"]
                text = (
                    f"RECOMANDARE\n"
                    f"Categorie recomandata: {rec['categorie']}\n"
                    f"Scor risc: {rec['scor_risc']:.2f}\n"
                    f"Algoritm: {rec['algoritm']}\n"
                    f"Data generare: {rec['data_generare']}\n"
                )
                self.rezultat_box.setText(text)
            else:
                QMessageBox.critical(self, "Eroare", res.text)
        except ValueError:
            QMessageBox.warning(self, "Eroare", "ID vehicul invalid")
        except Exception as e:
            QMessageBox.critical(self, "Eroare", str(e))


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
