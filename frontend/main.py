import sys

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QMessageBox, QFormLayout, QComboBox, QTextEdit, QHeaderView,
    QInputDialog, QDateEdit, QAbstractItemView
)

import api
from api import ApiError
from session import UserSession


def umple_tabel(table, randuri):
    """Afiseaza o lista de randuri (liste de valori) intr-un QTableWidget."""
    table.setRowCount(len(randuri))
    for r, rand in enumerate(randuri):
        for c, val in enumerate(rand):
            table.setItem(r, c, QTableWidgetItem("" if val is None else str(val)))


def tabel_simplu(coloane):
    table = QTableWidget()
    table.setColumnCount(len(coloane))
    table.setHorizontalHeaderLabels(coloane)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    return table


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
    def __init__(self, on_logout):
        super().__init__()
        self.on_logout = on_logout
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

        # Tab-urile depind de rol (CNF1): ce nu ai voie sa faci nu apare.
        self.tabs = QTabWidget()
        rol = self.session.rol
        if rol == "OPERATOR":
            self.tabs.addTab(ClientiTab(), "Clienti & Vehicule")
            self.tabs.addTab(ComenziTab(), "Comenzi & Piese")
            self.tabs.addTab(AiTab(), "Diagnoza AI")
        elif rol == "INSPECTOR":
            self.tabs.addTab(ItpTab(), "Statie ITP")
        else:  # ADMINISTRATOR
            self.tabs.addTab(UtilizatoriTab(), "Utilizatori")
            self.tabs.addTab(AngajatiTab(), "Angajati & Statistici")

        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def logout(self):
        self.session.clear()
        # Deschidem login-ul INAINTE de a inchide aceasta fereastra, ca aplicatia
        # sa nu se opreasca (Qt iese cand se inchide ultima fereastra).
        self.on_logout()
        self.close()


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


STATUS_URMATOR = {"DESCHISA": "IN_LUCRU", "IN_LUCRU": "FINALIZATA", "FINALIZATA": "PREDATA"}


def lei(valoare):
    return f"{float(valoare or 0):.2f}"


class ComenziTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        # ---- comanda noua
        noua = QHBoxLayout()
        self.vehicul_in = QComboBox()
        self.vehicul_in.setEditable(True)
        self.vehicul_in.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.vehicul_in.setMinimumWidth(240)
        self.vehicul_in.lineEdit().setPlaceholderText("Vehicul (scrieti nr. inmatriculare)")
        self.km_in = QLineEdit()
        self.km_in.setPlaceholderText("Km intrare")
        self.reclamatie_in = QLineEdit()
        self.reclamatie_in.setPlaceholderText("Reclamatie")
        deschide_btn = QPushButton("Deschide comanda")
        deschide_btn.setStyleSheet("background-color: #2b5797; color: white; font-weight: bold;")
        deschide_btn.clicked.connect(self.creeaza_comanda)
        noua.addWidget(self.vehicul_in)
        noua.addWidget(self.km_in)
        noua.addWidget(self.reclamatie_in, 1)
        noua.addWidget(deschide_btn)
        layout.addLayout(noua)

        # ---- lista comenzilor
        filtru = QHBoxLayout()
        filtru.addWidget(QLabel("Status:"))
        self.filtru_in = QComboBox()
        self.filtru_in.addItems(["Toate", "DESCHISA", "IN_LUCRU", "FINALIZATA", "PREDATA"])
        self.filtru_in.currentTextChanged.connect(lambda _: self.incarca_comenzi())
        reincarca_btn = QPushButton("Reincarca")
        reincarca_btn.clicked.connect(self.reincarca_tot)
        filtru.addWidget(self.filtru_in)
        filtru.addWidget(reincarca_btn)
        filtru.addStretch()
        layout.addLayout(filtru)

        self.table = tabel_simplu(["ID", "Nr. inmatriculare", "Vehicul", "Client", "Status", "Data intrare", "Km"])
        self.table.itemSelectionChanged.connect(self.arata_detalii)
        layout.addWidget(self.table, 2)

        # ---- detalii comanda selectata
        self.detalii = QTextEdit()
        self.detalii.setReadOnly(True)
        layout.addWidget(self.detalii, 2)

        # ---- actiuni asupra comenzii selectate
        lucrare_rand = QHBoxLayout()
        self.mecanic_in = QComboBox()
        self.lucrare_in = QComboBox()
        self.ore_in = QLineEdit()
        self.ore_in.setPlaceholderText("Ore")
        self.ore_in.setMaximumWidth(70)
        lucrare_btn = QPushButton("Adauga lucrare")
        lucrare_btn.clicked.connect(self.adauga_lucrare)
        lucrare_rand.addWidget(self.mecanic_in)
        lucrare_rand.addWidget(self.lucrare_in, 1)
        lucrare_rand.addWidget(self.ore_in)
        lucrare_rand.addWidget(lucrare_btn)
        layout.addLayout(lucrare_rand)

        piesa_rand = QHBoxLayout()
        self.piesa_in = QComboBox()
        self.cant_in = QLineEdit()
        self.cant_in.setPlaceholderText("Cant.")
        self.cant_in.setMaximumWidth(70)
        piesa_btn = QPushButton("Adauga piesa")
        piesa_btn.clicked.connect(self.adauga_piesa)
        status_btn = QPushButton("Avanseaza status")
        status_btn.setStyleSheet("background-color: #008a00; color: white; font-weight: bold;")
        status_btn.clicked.connect(self.avanseaza_status)
        piesa_rand.addWidget(self.piesa_in, 1)
        piesa_rand.addWidget(self.cant_in)
        piesa_rand.addWidget(piesa_btn)
        piesa_rand.addSpacing(20)
        piesa_rand.addWidget(status_btn)
        layout.addLayout(piesa_rand)

        self.setLayout(layout)
        self.incarca_referinte()
        self.incarca_comenzi()

    # ------------------------------------------------------------ incarcari
    def incarca_referinte(self):
        try:
            vehicule = api.get("/vehicule")
            mecanici = api.get("/mecanici")
            lucrari = api.get("/lucrari-catalog")
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return

        self.vehicul_in.clear()
        for v in vehicule:
            self.vehicul_in.addItem(f"{v['nr_inmatriculare']} - {v['marca']} {v['model']}", v["id_vehicul"])
        self.vehicul_in.setCurrentIndex(-1)

        self.mecanic_in.clear()
        for m in mecanici:
            self.mecanic_in.addItem(m["nume"], m["id_angajat"])

        self.lucrare_in.clear()
        for l in lucrari:
            self.lucrare_in.addItem(f"{l['denumire']} ({l['durata_ore']} h)", l["id_lucrare_catalog"])

        self.incarca_piese()

    def incarca_piese(self):
        try:
            piese = api.get("/piese")
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return
        self.piesa_in.clear()
        for p in piese:
            self.piesa_in.addItem(
                f"{p['cod']} - {p['denumire']} (stoc: {p['stoc_curent']}, {lei(p['pret_vanzare'])} lei)",
                p["id_piesa"])

    def incarca_comenzi(self, pastreaza=None):
        filtru = self.filtru_in.currentText()
        params = {} if filtru == "Toate" else {"status": filtru}
        try:
            comenzi = api.get("/comenzi", params=params)
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return

        self.table.blockSignals(True)
        umple_tabel(self.table, [
            [c["id_comanda"], c["nr_inmatriculare"], c["marca_model"], c["client_nume"],
             c["status"], c["data_intrare"], c["km_intrare"]]
            for c in comenzi
        ])
        rand = None
        if pastreaza is not None:
            for r in range(self.table.rowCount()):
                if self.table.item(r, 0).text() == str(pastreaza):
                    rand = r
                    break
        if rand is None:
            self.table.clearSelection()
        else:
            self.table.selectRow(rand)
        self.table.blockSignals(False)
        self.arata_detalii()

    def reincarca_tot(self):
        self.incarca_referinte()
        self.incarca_comenzi(self._id_selectat())

    # -------------------------------------------------------------- detalii
    def _id_selectat(self):
        randuri = self.table.selectionModel().selectedRows()
        if not randuri:
            return None
        return int(self.table.item(randuri[0].row(), 0).text())

    def _status_selectat(self):
        randuri = self.table.selectionModel().selectedRows()
        return self.table.item(randuri[0].row(), 4).text() if randuri else None

    def arata_detalii(self):
        id_comanda = self._id_selectat()
        if id_comanda is None:
            self.detalii.clear()
            return
        try:
            d = api.get(f"/comenzi/{id_comanda}")
        except ApiError as e:
            self.detalii.setText(str(e))
            return

        c = d["comanda"]
        linii = [
            f"COMANDA #{c['id_comanda']} - {c['status']}",
            f"Vehicul: {c['nr_inmatriculare']} ({c['marca_model']})",
            f"Client: {c['client_nume']}, tel. {c['client_telefon']}",
            f"Intrare: {c['data_intrare']}, {c['km_intrare']} km, operator {c['operator_nume']}",
            f"Reclamatie: {c['reclamatie'] or '-'}",
            "",
            "LUCRARI",
        ]
        if d["lucrari"]:
            for l in d["lucrari"]:
                linii.append(f"  {l['lucrare']} - {l['mecanic']}: {l['ore_lucrate']} h x "
                             f"{lei(l['tarif_orar_aplicat'])} = {lei(l['valoare'])} lei")
        else:
            linii.append("  (nicio lucrare)")

        linii += ["", "PIESE"]
        if d["piese"]:
            for p in d["piese"]:
                linii.append(f"  {p['denumire']} ({p['cod']}): {p['cantitate']} x "
                             f"{lei(p['pret_unitar_aplicat'])} = {lei(p['valoare'])} lei")
        else:
            linii.append("  (nicio piesa)")

        dv = d["deviz"]
        linii += ["", "DEVIZ",
                  f"  Manopera: {lei(dv['manopera'])} lei",
                  f"  Piese:    {lei(dv['piese'])} lei",
                  f"  TOTAL:    {lei(dv['total'])} lei"]
        self.detalii.setText("\n".join(linii))

    # -------------------------------------------------------------- actiuni
    def creeaza_comanda(self):
        idx = self.vehicul_in.findText(self.vehicul_in.currentText(), Qt.MatchFlag.MatchFixedString)
        if idx < 0:
            QMessageBox.warning(self, "Atentie", "Alegeti un vehicul din lista")
            return
        try:
            km = int(self.km_in.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Atentie", "Kilometrajul trebuie sa fie un numar intreg")
            return

        payload = {
            "km_intrare": km,
            "reclamatie": self.reclamatie_in.text().strip() or None,
            "id_vehicul": self.vehicul_in.itemData(idx),
        }
        try:
            data = api.post("/comenzi", json=payload)
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return

        self.km_in.clear()
        self.reclamatie_in.clear()
        self.vehicul_in.setCurrentIndex(-1)
        self.incarca_comenzi(data["id_comanda"])

    def _comanda_sau_avertisment(self):
        id_comanda = self._id_selectat()
        if id_comanda is None:
            QMessageBox.warning(self, "Atentie", "Selectati o comanda din tabel")
        return id_comanda

    def adauga_lucrare(self):
        id_comanda = self._comanda_sau_avertisment()
        if id_comanda is None:
            return
        try:
            ore = float(self.ore_in.text().strip().replace(",", "."))
        except ValueError:
            QMessageBox.warning(self, "Atentie", "Orele trebuie sa fie un numar")
            return

        payload = {
            "post_lucru": None,
            "ore_lucrate": ore,
            "id_mecanic": self.mecanic_in.currentData(),
            "id_lucrare_catalog": self.lucrare_in.currentData(),
        }
        try:
            api.post(f"/comenzi/{id_comanda}/lucrari", json=payload)
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return
        self.ore_in.clear()
        self.arata_detalii()

    def adauga_piesa(self):
        id_comanda = self._comanda_sau_avertisment()
        if id_comanda is None:
            return
        try:
            cantitate = int(self.cant_in.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Atentie", "Cantitatea trebuie sa fie un numar intreg")
            return

        try:
            r = api.post(f"/comenzi/{id_comanda}/piese",
                         json={"id_piesa": self.piesa_in.currentData(), "cantitate": cantitate})
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return

        self.cant_in.clear()
        self.incarca_piese()      # stocul s-a schimbat
        self.arata_detalii()
        if r.get("mesaj"):
            QMessageBox.warning(self, "Stoc minim", r["mesaj"])

    def avanseaza_status(self):
        id_comanda = self._comanda_sau_avertisment()
        if id_comanda is None:
            return
        urmator = STATUS_URMATOR.get(self._status_selectat())
        if urmator is None:
            QMessageBox.information(self, "Info", "Comanda a fost deja predata")
            return
        try:
            api.put(f"/comenzi/{id_comanda}/status", json={"status": urmator})
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return
        self.incarca_comenzi(id_comanda)


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


class UtilizatoriTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        form = QHBoxLayout()
        self.nume_in = QLineEdit()
        self.nume_in.setPlaceholderText("Utilizator")
        self.parola_in = QLineEdit()
        self.parola_in.setPlaceholderText("Parola (min. 6)")
        self.parola_in.setEchoMode(QLineEdit.EchoMode.Password)
        self.rol_in = QComboBox()
        self.rol_in.addItems(["OPERATOR", "INSPECTOR", "ADMINISTRATOR"])
        self.angajat_in = QComboBox()
        self.rol_in.currentTextChanged.connect(self.incarca_angajati)
        add_btn = QPushButton("Creeaza cont")
        add_btn.clicked.connect(self.creeaza)

        for w in (self.nume_in, self.parola_in, self.rol_in, self.angajat_in, add_btn):
            form.addWidget(w)
        layout.addLayout(form)

        self.table = tabel_simplu(["ID", "Utilizator", "Rol", "Angajat", "Activ"])
        layout.addWidget(self.table)

        butoane = QHBoxLayout()
        toggle_btn = QPushButton("Activeaza / Dezactiveaza")
        toggle_btn.clicked.connect(self.schimba_activ)
        reset_btn = QPushButton("Reseteaza parola")
        reset_btn.clicked.connect(self.reseteaza_parola)
        butoane.addWidget(toggle_btn)
        butoane.addWidget(reset_btn)
        butoane.addStretch()
        layout.addLayout(butoane)

        self.setLayout(layout)
        self.incarca_angajati(self.rol_in.currentText())
        self.incarca_utilizatori()

    def incarca_angajati(self, rol):
        """Combo-ul arata doar angajatii cu functia potrivita si fara cont."""
        self.angajat_in.clear()
        if rol == "ADMINISTRATOR":
            self.angajat_in.addItem("- fara angajat -", None)
            self.angajat_in.setEnabled(False)
            return
        self.angajat_in.setEnabled(True)
        try:
            lista = api.get("/admin/angajati", params={"functie": rol, "fara_cont": "true"})
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return
        for a in lista:
            self.angajat_in.addItem(a["nume"], a["id_angajat"])

    def incarca_utilizatori(self):
        try:
            lista = api.get("/admin/utilizatori")
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return
        umple_tabel(self.table, [
            [u["id_utilizator"], u["nume_utilizator"], u["rol"],
             u["angajat_nume"] or "-", "Da" if u["activ"] else "Nu"]
            for u in lista
        ])

    def _selectat(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Atentie", "Selectati un utilizator din tabel")
            return None
        return int(self.table.item(row, 0).text()), self.table.item(row, 4).text() == "Da"

    def creeaza(self):
        payload = {
            "nume_utilizator": self.nume_in.text().strip(),
            "parola": self.parola_in.text(),
            "rol": self.rol_in.currentText(),
            "id_angajat": self.angajat_in.currentData(),
        }
        try:
            api.post("/admin/utilizatori", json=payload)
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return
        self.nume_in.clear()
        self.parola_in.clear()
        self.incarca_angajati(self.rol_in.currentText())
        self.incarca_utilizatori()

    def schimba_activ(self):
        sel = self._selectat()
        if not sel:
            return
        id_utilizator, activ = sel
        try:
            api.put(f"/admin/utilizatori/{id_utilizator}/activ", json={"activ": not activ})
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return
        self.incarca_utilizatori()

    def reseteaza_parola(self):
        sel = self._selectat()
        if not sel:
            return
        parola, ok = QInputDialog.getText(
            self, "Resetare parola", "Parola noua (min. 6 caractere):", QLineEdit.EchoMode.Password)
        if not ok:
            return
        try:
            api.put(f"/admin/utilizatori/{sel[0]}/parola", json={"parola": parola})
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return
        QMessageBox.information(self, "Succes", "Parola a fost schimbata")


class AngajatiTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        form = QHBoxLayout()
        self.nume_in = QLineEdit()
        self.nume_in.setPlaceholderText("Nume angajat")
        self.functie_in = QComboBox()
        self.functie_in.addItems(["MECANIC", "OPERATOR", "INSPECTOR"])
        self.tarif_in = QLineEdit()
        self.tarif_in.setPlaceholderText("Tarif orar (doar mecanici)")
        add_btn = QPushButton("Adauga angajat")
        add_btn.clicked.connect(self.adauga)
        for w in (self.nume_in, self.functie_in, self.tarif_in, add_btn):
            form.addWidget(w)
        layout.addLayout(form)

        self.table = tabel_simplu(["ID", "Nume", "Functie", "Tarif orar"])
        layout.addWidget(self.table)

        layout.addWidget(QLabel("<b>Statistici activitate</b>"))
        perioada = QHBoxLayout()
        self.start_in = QDateEdit(QDate.currentDate().addDays(-30))
        self.end_in = QDateEdit(QDate.currentDate())
        for d in (self.start_in, self.end_in):
            d.setCalendarPopup(True)
            d.setDisplayFormat("yyyy-MM-dd")
        stat_btn = QPushButton("Afiseaza statistici")
        stat_btn.clicked.connect(self.incarca_statistici)
        perioada.addWidget(QLabel("De la:"))
        perioada.addWidget(self.start_in)
        perioada.addWidget(QLabel("Pana la:"))
        perioada.addWidget(self.end_in)
        perioada.addWidget(stat_btn)
        perioada.addStretch()
        layout.addLayout(perioada)

        self.stat_table = tabel_simplu([
            "Nume", "Functie", "Comenzi deschise", "Comenzi lucrate",
            "Ore lucrate", "Venit manopera", "Inspectii", "Respinse"])
        layout.addWidget(self.stat_table)

        self.setLayout(layout)
        self.incarca_angajati()
        self.incarca_statistici()

    def incarca_angajati(self):
        try:
            lista = api.get("/admin/angajati")
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return
        umple_tabel(self.table, [[a["id_angajat"], a["nume"], a["functie"], a["tarif_orar"]] for a in lista])

    def adauga(self):
        tarif_text = self.tarif_in.text().strip()
        try:
            tarif = float(tarif_text) if tarif_text else None
        except ValueError:
            QMessageBox.warning(self, "Eroare", "Tariful trebuie sa fie un numar")
            return
        payload = {"nume": self.nume_in.text().strip(),
                   "functie": self.functie_in.currentText(),
                   "tarif_orar": tarif}
        try:
            api.post("/admin/angajati", json=payload)
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return
        self.nume_in.clear()
        self.tarif_in.clear()
        self.incarca_angajati()
        self.incarca_statistici()

    def incarca_statistici(self):
        params = {"start": self.start_in.date().toString(Qt.DateFormat.ISODate),
                  "end": self.end_in.date().toString(Qt.DateFormat.ISODate)}
        try:
            lista = api.get("/admin/statistici", params=params)
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return
        umple_tabel(self.stat_table, [
            [s["nume"], s["functie"], s["nr_comenzi_deschise"], s["nr_comenzi_lucrate"],
             s["ore_lucrate"], s["venit_manopera"], s["nr_inspectii"], s["nr_respinse"]]
            for s in lista
        ])


def main():
    app = QApplication(sys.argv)
    ferestre = {}  # pastram referintele, altfel Python le sterge din memorie

    def show_login():
        login = LoginWindow(show_main)
        ferestre["login"] = login
        login.show()

    def show_main():
        principala = MainWindow(on_logout=show_login)
        ferestre["principala"] = principala
        principala.show()
        ferestre["login"].close()

    show_login()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()