import sys

from PyQt6.QtCore import Qt, QDate, QDateTime, QTime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QMessageBox, QFormLayout, QComboBox, QTextEdit, QHeaderView,
    QInputDialog, QDateEdit, QDateTimeEdit, QAbstractItemView, QCheckBox
)
from PyQt6.QtGui import QColor

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
            self.tabs.addTab(ProgramariTab(), "Programari")
            self.tabs.addTab(ComenziTab(), "Comenzi")
            self.tabs.addTab(PieseTab(), "Piese & Stoc")
            self.tabs.addTab(AiTab(), "Diagnoza AI")
        elif rol == "INSPECTOR":
            self.tabs.addTab(ItpTab(), "Statie ITP")
        else:  # ADMINISTRATOR
            self.tabs.addTab(UtilizatoriTab(), "Utilizatori")
            self.tabs.addTab(AngajatiTab(), "Angajati & Statistici")
            self.tabs.addTab(CatalogTab(), "Catalog lucrari")

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
        layout = QVBoxLayout()

        # ---- cautare client
        cautare = QHBoxLayout()
        self.cauta_in = QLineEdit()
        self.cauta_in.setPlaceholderText("Cauta client (nume, prenume sau telefon)")
        self.cauta_in.returnPressed.connect(lambda: self.load_clienti())
        cauta_btn = QPushButton("Cauta")
        cauta_btn.clicked.connect(lambda: self.load_clienti())
        cautare.addWidget(self.cauta_in, 1)
        cautare.addWidget(cauta_btn)
        layout.addLayout(cautare)

        # ---- client nou
        form_client = QHBoxLayout()
        self.nume_in = QLineEdit()
        self.nume_in.setPlaceholderText("Nume")
        self.prenume_in = QLineEdit()
        self.prenume_in.setPlaceholderText("Prenume")
        self.tel_in = QLineEdit()
        self.tel_in.setPlaceholderText("Telefon")
        self.email_in = QLineEdit()
        self.email_in.setPlaceholderText("Email (optional)")
        add_client_btn = QPushButton("Adauga client")
        add_client_btn.clicked.connect(self.add_client)
        for w in (self.nume_in, self.prenume_in, self.tel_in, self.email_in, add_client_btn):
            form_client.addWidget(w)
        layout.addLayout(form_client)

        # ---- lista clienti
        self.table = tabel_simplu(["ID", "Nume", "Prenume", "Telefon", "Email"])
        self.table.itemSelectionChanged.connect(self.load_vehicule)
        layout.addWidget(self.table, 1)

        # ---- vehiculele clientului selectat
        self.titlu_vehicule = QLabel("<b>Vehicule</b> - selectati un client")
        layout.addWidget(self.titlu_vehicule)

        self.table_vehicule = tabel_simplu(["ID", "Nr. inmatriculare", "Marca", "Model", "Motorizare",
                                            "Combustibil", "An", "Norma poluare", "Serie sasiu"])
        layout.addWidget(self.table_vehicule, 1)

        # ---- vehicul nou
        rand1 = QHBoxLayout()
        self.serie_in = QLineEdit()
        self.serie_in.setPlaceholderText("Serie sasiu (17 caractere)")
        self.serie_in.setMaxLength(17)
        self.nr_in = QLineEdit()
        self.nr_in.setPlaceholderText("Nr. inmatriculare")
        self.marca_in = QLineEdit()
        self.marca_in.setPlaceholderText("Marca")
        self.model_in = QLineEdit()
        self.model_in.setPlaceholderText("Model")
        for w in (self.serie_in, self.nr_in, self.marca_in, self.model_in):
            rand1.addWidget(w)
        layout.addLayout(rand1)

        rand2 = QHBoxLayout()
        self.motor_in = QLineEdit()
        self.motor_in.setPlaceholderText("Motorizare (optional)")
        self.combustibil_in = QComboBox()
        self.combustibil_in.addItems(["BENZINA", "MOTORINA", "GPL", "HIBRID", "ELECTRIC"])
        self.an_in = QLineEdit()
        self.an_in.setPlaceholderText("An fabricatie")
        self.an_in.setMaximumWidth(110)
        self.norma_in = QComboBox()
        self.norma_in.addItems(["", "Euro 1", "Euro 2", "Euro 3", "Euro 4", "Euro 5", "Euro 6"])
        add_vehicul_btn = QPushButton("Adauga vehicul la clientul selectat")
        add_vehicul_btn.clicked.connect(self.add_vehicul)
        rand2.addWidget(self.motor_in, 1)
        rand2.addWidget(self.combustibil_in)
        rand2.addWidget(self.an_in)
        rand2.addWidget(QLabel("Norma:"))
        rand2.addWidget(self.norma_in)
        rand2.addWidget(add_vehicul_btn)
        layout.addLayout(rand2)

        self.setLayout(layout)
        self.load_clienti()

    # ------------------------------------------------------------- clienti
    def _client_selectat(self):
        randuri = self.table.selectionModel().selectedRows()
        if not randuri:
            return None
        r = randuri[0].row()
        return int(self.table.item(r, 0).text()), f"{self.table.item(r, 1).text()} {self.table.item(r, 2).text()}"

    def load_clienti(self, selecteaza=None):
        text = self.cauta_in.text().strip()
        try:
            clienti = api.get("/clienti", params={"search": text} if text else None)
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return

        self.table.blockSignals(True)
        umple_tabel(self.table, [[c["id_client"], c["nume"], c["prenume"], c["telefon"], c["email"]]
                                 for c in clienti])
        self.table.clearSelection()
        if selecteaza is not None:
            for r in range(self.table.rowCount()):
                if self.table.item(r, 0).text() == str(selecteaza):
                    self.table.selectRow(r)
                    break
        self.table.blockSignals(False)
        self.load_vehicule()

    def add_client(self):
        nume = self.nume_in.text().strip()
        prenume = self.prenume_in.text().strip()
        tel = self.tel_in.text().strip()
        if not nume or not prenume or not tel:
            QMessageBox.warning(self, "Atentie", "Completati nume, prenume si telefon")
            return

        payload = {"nume": nume, "prenume": prenume, "telefon": tel,
                   "email": self.email_in.text().strip() or None}
        try:
            nou = api.post("/clienti", json=payload)
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return

        for w in (self.nume_in, self.prenume_in, self.tel_in, self.email_in, self.cauta_in):
            w.clear()
        self.load_clienti(selecteaza=nou["id_client"])   # il selectam, ca sa-i putem adauga vehicule

    # ------------------------------------------------------------ vehicule
    def load_vehicule(self):
        sel = self._client_selectat()
        if sel is None:
            self.titlu_vehicule.setText("<b>Vehicule</b> - selectati un client")
            self.table_vehicule.setRowCount(0)
            return

        self.titlu_vehicule.setText(f"<b>Vehiculele clientului:</b> {sel[1]}")
        try:
            vehicule = api.get("/vehicule", params={"id_client": sel[0]})
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return
        umple_tabel(self.table_vehicule, [
            [v["id_vehicul"], v["nr_inmatriculare"], v["marca"], v["model"], v["motorizare"],
             v["combustibil"], v["an_fabricatie"], v["norma_poluare"], v["serie_sasiu"]]
            for v in vehicule
        ])

    def add_vehicul(self):
        sel = self._client_selectat()
        if sel is None:
            QMessageBox.warning(self, "Atentie", "Selectati mai intai clientul din tabel")
            return

        serie = self.serie_in.text().strip().upper()
        nr = self.nr_in.text().strip().upper()
        marca = self.marca_in.text().strip()
        model = self.model_in.text().strip()
        if len(serie) != 17:
            QMessageBox.warning(self, "Atentie", "Seria de sasiu trebuie sa aiba exact 17 caractere")
            return
        if not nr or not marca or not model:
            QMessageBox.warning(self, "Atentie", "Completati nr. de inmatriculare, marca si modelul")
            return
        try:
            an = int(self.an_in.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Atentie", "Anul de fabricatie trebuie sa fie un numar")
            return

        payload = {
            "serie_sasiu": serie,
            "nr_inmatriculare": nr,
            "marca": marca,
            "model": model,
            "motorizare": self.motor_in.text().strip() or None,
            "combustibil": self.combustibil_in.currentText(),
            "an_fabricatie": an,
            "norma_poluare": self.norma_in.currentText() or None,
            "id_client": sel[0],
        }
        try:
            api.post("/vehicule", json=payload)
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return

        for w in (self.serie_in, self.nr_in, self.marca_in, self.model_in, self.motor_in, self.an_in):
            w.clear()
        self.norma_in.setCurrentIndex(0)
        self.load_vehicule()


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


class ProgramariTab(QWidget):
    def __init__(self):
        super().__init__()
        self._durate = {}   # id lucrare -> durata standard (pentru completare automata)
        layout = QVBoxLayout()

        # ---- programare noua
        rand1 = QHBoxLayout()
        self.vehicul_in = QComboBox()
        self.vehicul_in.setEditable(True)
        self.vehicul_in.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.vehicul_in.setMinimumWidth(240)
        self.vehicul_in.lineEdit().setPlaceholderText("Vehicul (scrieti nr. inmatriculare)")
        self.lucrare_in = QComboBox()
        self.lucrare_in.currentIndexChanged.connect(self.completeaza_durata)
        rand1.addWidget(self.vehicul_in)
        rand1.addWidget(self.lucrare_in, 1)
        layout.addLayout(rand1)

        rand2 = QHBoxLayout()
        maine_la_9 = QDateTime(QDate.currentDate().addDays(1), QTime(9, 0))
        self.dt_in = QDateTimeEdit(maine_la_9)
        self.dt_in.setCalendarPopup(True)
        self.dt_in.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.durata_in = QLineEdit()
        self.durata_in.setPlaceholderText("Durata (ore)")
        self.durata_in.setMaximumWidth(100)
        self.problema_in = QLineEdit()
        self.problema_in.setPlaceholderText("Problema")
        adauga_btn = QPushButton("Adauga programare")
        adauga_btn.setStyleSheet("background-color: #2b5797; color: white; font-weight: bold;")
        adauga_btn.clicked.connect(self.adauga)
        rand2.addWidget(self.dt_in)
        rand2.addWidget(self.durata_in)
        rand2.addWidget(self.problema_in, 1)
        rand2.addWidget(adauga_btn)
        layout.addLayout(rand2)

        # ---- filtru pe zi + ocupare
        filtru = QHBoxLayout()
        filtru.addWidget(QLabel("Ziua:"))
        self.zi_in = QDateEdit(QDate.currentDate())
        self.zi_in.setCalendarPopup(True)
        self.zi_in.setDisplayFormat("yyyy-MM-dd")
        zi_btn = QPushButton("Arata ziua")
        zi_btn.clicked.connect(lambda: self.incarca())
        toate_btn = QPushButton("Toate")
        toate_btn.clicked.connect(lambda: self.incarca(toate=True))
        reincarca_btn = QPushButton("Reincarca liste")
        reincarca_btn.clicked.connect(self.incarca_referinte)
        for w in (self.zi_in, zi_btn, toate_btn, reincarca_btn):
            filtru.addWidget(w)
        filtru.addStretch()
        layout.addLayout(filtru)

        self.ocupare_lbl = QLabel("")
        self.ocupare_lbl.setWordWrap(True)
        layout.addWidget(self.ocupare_lbl)

        self.table = tabel_simplu(["ID", "Data si ora", "Vehicul", "Client", "Lucrare",
                                   "Durata (h)", "Status", "Comanda"])
        layout.addWidget(self.table)

        # ---- actiuni pe programarea selectata
        butoane = QHBoxLayout()
        anuleaza_btn = QPushButton("Anuleaza")
        anuleaza_btn.clicked.connect(lambda: self.schimba_status("ANULATA"))
        neprezentat_btn = QPushButton("Neprezentat")
        neprezentat_btn.clicked.connect(lambda: self.schimba_status("NEPREZENTAT"))
        comanda_btn = QPushButton("Deschide comanda")
        comanda_btn.setStyleSheet("background-color: #008a00; color: white; font-weight: bold;")
        comanda_btn.clicked.connect(self.deschide_comanda)
        butoane.addWidget(anuleaza_btn)
        butoane.addWidget(neprezentat_btn)
        butoane.addStretch()
        butoane.addWidget(comanda_btn)
        layout.addLayout(butoane)

        self.setLayout(layout)
        self.incarca_referinte()
        self.incarca()

    # ------------------------------------------------------------ incarcari
    def incarca_referinte(self):
        try:
            vehicule = api.get("/vehicule")
            lucrari = api.get("/lucrari-catalog")
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return

        self.vehicul_in.clear()
        for v in vehicule:
            self.vehicul_in.addItem(f"{v['nr_inmatriculare']} - {v['marca']} {v['model']}", v["id_vehicul"])
        self.vehicul_in.setCurrentIndex(-1)

        self._durate = {l["id_lucrare_catalog"]: l["durata_ore"] for l in lucrari}
        self.lucrare_in.clear()
        for l in lucrari:
            self.lucrare_in.addItem(l["denumire"], l["id_lucrare_catalog"])

    def completeaza_durata(self):
        durata = self._durate.get(self.lucrare_in.currentData())
        if durata is not None:
            self.durata_in.setText(str(durata))

    def incarca(self, toate=False):
        zi = self.zi_in.date().toString(Qt.DateFormat.ISODate)
        try:
            programari = api.get("/programari", params=None if toate else {"data": zi})
            ocupare = [] if toate else api.get("/programari/ocupare", params={"data": zi})
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return

        umple_tabel(self.table, [
            [p["id_programare"], p["data_programare"].replace("T", " ")[:16], p["nr_inmatriculare"],
             p["client_nume"], p["lucrare"], p["durata_estimata_ore"], p["status"], p["id_comanda"] or "-"]
            for p in programari
        ])
        if ocupare:
            self.ocupare_lbl.setText(
                "Elevatoare libere pe ore:  " +
                "   ".join(f"{o['ora']} -> {o['elevatoare_libere']}" for o in ocupare))
        else:
            self.ocupare_lbl.setText("")

    # -------------------------------------------------------------- actiuni
    def adauga(self):
        idx = self.vehicul_in.findText(self.vehicul_in.currentText(), Qt.MatchFlag.MatchFixedString)
        if idx < 0:
            QMessageBox.warning(self, "Atentie", "Alegeti un vehicul din lista")
            return
        try:
            durata = float(self.durata_in.text().strip().replace(",", "."))
        except ValueError:
            QMessageBox.warning(self, "Atentie", "Durata trebuie sa fie un numar")
            return

        payload = {
            "data_programare": self.dt_in.dateTime().toString(Qt.DateFormat.ISODate),
            "durata_estimata_ore": durata,
            "descriere_problema": self.problema_in.text().strip() or None,
            "id_vehicul": self.vehicul_in.itemData(idx),
            "id_lucrare_catalog": self.lucrare_in.currentData(),
        }
        try:
            api.post("/programari", json=payload)
        except ApiError as e:
            QMessageBox.critical(self, "Programare refuzata", str(e))
            return

        self.problema_in.clear()
        self.vehicul_in.setCurrentIndex(-1)
        self.zi_in.setDate(self.dt_in.date())   # arata ziua programarii nou create
        self.incarca()

    def _selectata(self):
        randuri = self.table.selectionModel().selectedRows()
        if not randuri:
            QMessageBox.warning(self, "Atentie", "Selectati o programare din tabel")
            return None
        r = randuri[0].row()
        return int(self.table.item(r, 0).text()), self.table.item(r, 6).text()

    def schimba_status(self, nou):
        sel = self._selectata()
        if not sel:
            return
        try:
            api.put(f"/programari/{sel[0]}/status", json={"status": nou})
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return
        self.incarca()

    def deschide_comanda(self):
        sel = self._selectata()
        if not sel:
            return
        if sel[1] != "PROGRAMATA":
            QMessageBox.information(self, "Info", "Doar o programare activa poate deschide o comanda")
            return
        km, ok = QInputDialog.getInt(self, "Deschide comanda", "Kilometraj la intrare:", 0, 0, 2000000)
        if not ok:
            return
        try:
            r = api.post(f"/programari/{sel[0]}/comanda", json={"km_intrare": km})
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return
        QMessageBox.information(self, "Succes",
                                f"Comanda #{r['id_comanda']} a fost deschisa. O gasiti in tab-ul Comenzi.")
        self.incarca()


class PieseTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.alerta_lbl = QLabel("")
        self.alerta_lbl.setWordWrap(True)
        layout.addWidget(self.alerta_lbl)

        # ---- filtre
        filtru = QHBoxLayout()
        filtru.addWidget(QLabel("Categorie:"))
        self.categorie_filtru = QComboBox()
        self.categorie_filtru.currentTextChanged.connect(lambda _: self.incarca_piese())
        self.sub_prag_chk = QCheckBox("Doar sub prag")
        self.sub_prag_chk.stateChanged.connect(lambda _: self.incarca_piese())
        aproviziona_btn = QPushButton("Aproviziona piesa selectata")
        aproviziona_btn.setStyleSheet("background-color: #008a00; color: white; font-weight: bold;")
        aproviziona_btn.clicked.connect(self.aproviziona)
        filtru.addWidget(self.categorie_filtru)
        filtru.addWidget(self.sub_prag_chk)
        filtru.addStretch()
        filtru.addWidget(aproviziona_btn)
        layout.addLayout(filtru)

        self.table = tabel_simplu(["ID", "Cod", "Denumire", "Categorie", "Pret", "Stoc", "Prag minim", "Furnizor"])
        layout.addWidget(self.table, 1)

        # ---- piesa noua
        layout.addWidget(QLabel("<b>Piesa noua</b>"))
        rand1 = QHBoxLayout()
        self.cod_in = QLineEdit()
        self.cod_in.setPlaceholderText("Cod")
        self.den_in = QLineEdit()
        self.den_in.setPlaceholderText("Denumire")
        self.categ_in = QComboBox()
        self.categ_in.setEditable(True)
        self.categ_in.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.furnizor_in = QComboBox()
        rand1.addWidget(self.cod_in)
        rand1.addWidget(self.den_in, 1)
        rand1.addWidget(self.categ_in)
        rand1.addWidget(self.furnizor_in)
        layout.addLayout(rand1)

        rand2 = QHBoxLayout()
        self.pret_in = QLineEdit()
        self.pret_in.setPlaceholderText("Pret vanzare")
        self.stoc_in = QLineEdit()
        self.stoc_in.setPlaceholderText("Stoc initial")
        self.prag_in = QLineEdit()
        self.prag_in.setPlaceholderText("Prag minim")
        adauga_btn = QPushButton("Adauga piesa")
        adauga_btn.clicked.connect(self.adauga_piesa)
        for w in (self.pret_in, self.stoc_in, self.prag_in):
            rand2.addWidget(w)
        rand2.addWidget(adauga_btn)
        layout.addLayout(rand2)

        # ---- furnizor nou
        layout.addWidget(QLabel("<b>Furnizor nou</b>"))
        rand3 = QHBoxLayout()
        self.fden_in = QLineEdit()
        self.fden_in.setPlaceholderText("Denumire furnizor")
        self.cui_in = QLineEdit()
        self.cui_in.setPlaceholderText("CUI")
        self.ftel_in = QLineEdit()
        self.ftel_in.setPlaceholderText("Telefon (optional)")
        furnizor_btn = QPushButton("Adauga furnizor")
        furnizor_btn.clicked.connect(self.adauga_furnizor)
        rand3.addWidget(self.fden_in, 1)
        rand3.addWidget(self.cui_in)
        rand3.addWidget(self.ftel_in)
        rand3.addWidget(furnizor_btn)
        layout.addLayout(rand3)

        self.setLayout(layout)
        self.incarca_furnizori()
        self.incarca_categorii()
        self.incarca_piese()
        self.incarca_alerta()

    # ------------------------------------------------------------ incarcari
    def incarca_furnizori(self):
        try:
            furnizori = api.get("/furnizori")
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return
        self.furnizor_in.clear()
        for f in furnizori:
            self.furnizor_in.addItem(f["denumire"], f["id_furnizor"])

    def incarca_categorii(self):
        try:
            categorii = api.get("/piese/categorii")
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return
        curent = self.categorie_filtru.currentText()
        self.categorie_filtru.blockSignals(True)
        self.categorie_filtru.clear()
        self.categorie_filtru.addItem("Toate")
        self.categorie_filtru.addItems(categorii)
        idx = self.categorie_filtru.findText(curent)
        self.categorie_filtru.setCurrentIndex(max(idx, 0))
        self.categorie_filtru.blockSignals(False)

        self.categ_in.clear()
        self.categ_in.addItems(categorii)
        self.categ_in.setCurrentIndex(-1)

    def incarca_piese(self):
        params = {}
        if self.categorie_filtru.currentText() not in ("", "Toate"):
            params["categorie"] = self.categorie_filtru.currentText()
        if self.sub_prag_chk.isChecked():
            params["doar_sub_prag"] = "true"
        try:
            piese = api.get("/piese", params=params)
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return

        umple_tabel(self.table, [
            [p["id_piesa"], p["cod"], p["denumire"], p["categorie"], lei(p["pret_vanzare"]),
             p["stoc_curent"], p["prag_minim"], p["furnizor"]]
            for p in piese
        ])
        for r, p in enumerate(piese):          # piesele sub prag apar in rosu
            if p["sub_prag"]:
                for c in range(self.table.columnCount()):
                    item = self.table.item(r, c)
                    item.setBackground(QColor("#f8c8c8"))
                    item.setForeground(QColor("#600000"))

    def incarca_alerta(self):
        try:
            sub_prag = api.get("/piese/sub-prag")
        except ApiError:
            return
        if not sub_prag:
            self.alerta_lbl.setText("Toate stocurile sunt peste pragul minim.")
            self.alerta_lbl.setStyleSheet("color: green;")
            return
        primele = ", ".join(f"{p['denumire']} ({p['stoc_curent']}/{p['prag_minim']})" for p in sub_prag[:5])
        rest = f" si inca {len(sub_prag) - 5}" if len(sub_prag) > 5 else ""
        self.alerta_lbl.setText(f"ATENTIE: {len(sub_prag)} piese sub pragul minim: {primele}{rest}")
        self.alerta_lbl.setStyleSheet("color: #c00000; font-weight: bold;")

    def reincarca_tot(self):
        self.incarca_categorii()
        self.incarca_piese()
        self.incarca_alerta()

    # -------------------------------------------------------------- actiuni
    def aproviziona(self):
        randuri = self.table.selectionModel().selectedRows()
        if not randuri:
            QMessageBox.warning(self, "Atentie", "Selectati o piesa din tabel")
            return
        r = randuri[0].row()
        id_piesa = int(self.table.item(r, 0).text())
        denumire = self.table.item(r, 2).text()

        cantitate, ok = QInputDialog.getInt(
            self, "Aprovizionare", f"Cantitate primita pentru \"{denumire}\":", 1, 1, 100000)
        if not ok:
            return
        try:
            api.put(f"/piese/{id_piesa}/stoc", json={"cantitate": cantitate})
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return
        self.reincarca_tot()

    def adauga_piesa(self):
        try:
            payload = {
                "cod": self.cod_in.text().strip(),
                "denumire": self.den_in.text().strip(),
                "categorie": self.categ_in.currentText().strip().upper(),
                "pret_vanzare": float(self.pret_in.text().strip().replace(",", ".")),
                "stoc_curent": int(self.stoc_in.text().strip() or 0),
                "prag_minim": int(self.prag_in.text().strip() or 0),
                "id_furnizor": self.furnizor_in.currentData(),
            }
        except ValueError:
            QMessageBox.warning(self, "Atentie", "Pretul, stocul si pragul trebuie sa fie numere")
            return
        if payload["id_furnizor"] is None:
            QMessageBox.warning(self, "Atentie", "Adaugati mai intai un furnizor")
            return

        try:
            api.post("/piese", json=payload)
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return
        for w in (self.cod_in, self.den_in, self.pret_in, self.stoc_in, self.prag_in):
            w.clear()
        self.reincarca_tot()

    def adauga_furnizor(self):
        payload = {
            "denumire": self.fden_in.text().strip(),
            "cui": self.cui_in.text().strip(),
            "telefon": self.ftel_in.text().strip() or None,
        }
        try:
            api.post("/furnizori", json=payload)
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return
        for w in (self.fden_in, self.cui_in, self.ftel_in):
            w.clear()
        self.incarca_furnizori()


class CatalogTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Lucrarile din catalog sunt folosite la programari si la comenzi."))

        form = QHBoxLayout()
        self.den_in = QLineEdit()
        self.den_in.setPlaceholderText("Denumire lucrare")
        self.durata_in = QLineEdit()
        self.durata_in.setPlaceholderText("Durata standard (ore)")
        self.durata_in.setMaximumWidth(170)
        adauga_btn = QPushButton("Adauga lucrare")
        adauga_btn.clicked.connect(self.adauga)
        form.addWidget(self.den_in, 1)
        form.addWidget(self.durata_in)
        form.addWidget(adauga_btn)
        layout.addLayout(form)

        self.table = tabel_simplu(["ID", "Denumire", "Durata standard (h)"])
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.incarca()

    def incarca(self):
        try:
            lista = api.get("/admin/catalog")
        except ApiError as e:
            QMessageBox.warning(self, "Eroare", str(e))
            return
        umple_tabel(self.table, [[l["id_lucrare_catalog"], l["denumire"], l["durata_ore"]] for l in lista])

    def adauga(self):
        try:
            durata = float(self.durata_in.text().strip().replace(",", "."))
        except ValueError:
            QMessageBox.warning(self, "Atentie", "Durata trebuie sa fie un numar")
            return
        try:
            api.post("/admin/catalog", json={"denumire": self.den_in.text().strip(), "durata_ore": durata})
        except ApiError as e:
            QMessageBox.critical(self, "Eroare", str(e))
            return
        self.den_in.clear()
        self.durata_in.clear()
        self.incarca()


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