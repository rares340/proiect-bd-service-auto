from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class UserLogin(BaseModel):
    nume_utilizator: str
    parola: str

class UserResponse(BaseModel):
    id_utilizator: int
    nume_utilizator: str
    rol: str
    id_angajat: Optional[int] = None

class LoginResponse(UserResponse):
    token: str

class ClientBase(BaseModel):
    nume: str
    prenume: str
    telefon: str
    email: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientResponse(ClientBase):
    id_client: int

class VehiculBase(BaseModel):
    serie_sasiu: str = Field(..., min_length=17, max_length=17)
    nr_inmatriculare: str
    marca: str
    model: str
    motorizare: Optional[str] = None
    combustibil: str
    an_fabricatie: int = Field(..., ge=1950, le=2100)
    norma_poluare: Optional[str] = None

class VehiculCreate(VehiculBase):
    id_client: int

class VehiculResponse(VehiculBase):
    id_vehicul: int
    id_client: int

class PiesaResponse(BaseModel):
    id_piesa: int
    cod: str
    denumire: str
    categorie: str
    pret_vanzare: float
    stoc_curent: int
    prag_minim: int
    id_furnizor: int

class PiesaComandaCreate(BaseModel):
    # pretul si stocul sunt tratate de baza de date (triggere)
    id_piesa: int
    cantitate: int = Field(..., gt=0)

class PiesaComandaResponse(BaseModel):
    id_comanda: int
    id_piesa: int
    denumire: Optional[str] = None
    stoc_ramas: int
    alerta_stoc_minim: bool
    mesaj: Optional[str] = None

class ComandaCreate(BaseModel):
    # id_operator NU mai vine din client: se ia din token
    km_intrare: int = Field(..., ge=0)
    reclamatie: Optional[str] = None
    id_vehicul: int

class ComandaStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(DESCHISA|IN_LUCRU|FINALIZATA|PREDATA)$")
    data_predare: Optional[date] = None

class ComandaResponse(BaseModel):
    id_comanda: int
    data_intrare: date
    data_predare: Optional[date] = None
    km_intrare: int
    status: str
    reclamatie: Optional[str] = None
    id_vehicul: int
    id_operator: int
    nr_inmatriculare: Optional[str] = None
    marca_model: Optional[str] = None
    client_nume: Optional[str] = None

class LucrareEfectuataCreate(BaseModel):
    # tariful orar il pune triggerul din baza de date
    post_lucru: Optional[str] = None
    ore_lucrate: float = Field(..., ge=0)
    id_mecanic: int
    id_lucrare_catalog: int

class LucrareEfectuataResponse(LucrareEfectuataCreate):
    id_lucrare_efectuata: int
    id_comanda: int
    tarif_orar_aplicat: float
    denumire_lucrare: Optional[str] = None
    mecanic_nume: Optional[str] = None

class InspectieITPCreate(BaseModel):
    # id_inspector vine din token; data_expirare o calculeaza baza de date
    km: int = Field(..., ge=0)
    emisii_co: Optional[float] = Field(None, ge=0)
    eficienta_franare: Optional[float] = Field(None, ge=0, le=100)
    convergenta: Optional[float] = None
    rezultat: str = Field(..., pattern="^(ADMIS|RESPINS)$")
    id_vehicul: int

class InspectieITPResponse(BaseModel):
    id_inspectie: int
    data_inspectie: date
    km: int
    emisii_co: Optional[float] = None
    eficienta_franare: Optional[float] = None
    convergenta: Optional[float] = None
    rezultat: str
    data_expirare: Optional[date] = None
    id_vehicul: int
    id_inspector: int

from datetime import datetime  


class UtilizatorCreate(BaseModel):
    nume_utilizator: str = Field(..., min_length=3, max_length=50)
    parola: str = Field(..., min_length=6, max_length=72)
    rol: str = Field(..., pattern="^(ADMINISTRATOR|OPERATOR|INSPECTOR)$")
    id_angajat: Optional[int] = None


class UtilizatorAdminResponse(BaseModel):
    id_utilizator: int
    nume_utilizator: str
    rol: str
    activ: bool
    data_creare: datetime
    id_angajat: Optional[int] = None
    angajat_nume: Optional[str] = None


class ActivUpdate(BaseModel):
    activ: bool


class ParolaUpdate(BaseModel):
    parola: str = Field(..., min_length=6, max_length=72)


class AngajatCreate(BaseModel):
    nume: str = Field(..., min_length=2, max_length=100)
    functie: str = Field(..., pattern="^(MECANIC|OPERATOR|INSPECTOR)$")
    tarif_orar: Optional[float] = Field(None, ge=0)


class AngajatResponse(BaseModel):
    id_angajat: int
    nume: str
    functie: str
    tarif_orar: Optional[float] = None


class StatisticaAngajat(BaseModel):
    id_angajat: int
    nume: str
    functie: str
    nr_comenzi_deschise: int      # operatori
    nr_comenzi_lucrate: int       # mecanici
    ore_lucrate: float            # mecanici
    venit_manopera: float         # mecanici
    nr_inspectii: int             # inspectori
    nr_respinse: int              # inspectori