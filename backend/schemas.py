from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

class UserLogin(BaseModel):
    nume_utilizator: str
    parola: str

class UserResponse(BaseModel):
    id_utilizator: int
    nume_utilizator: str
    rol: str
    id_angajat: Optional[int]

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
    sub_prag: Optional[bool] = False

class PiesaComandaCreate(BaseModel):
    id_piesa: int
    cantitate: int = Field(..., gt=0)
    pret_unitar_aplicat: Optional[float] = None

class PiesaComandaResponse(BaseModel):
    id_comanda: int
    id_piesa: int
    denumire: Optional[str] = None
    cantitate: int
    pret_unitar_aplicat: float
    stoc_ramas: int
    alerta_stoc_minim: bool

class ComandaBase(BaseModel):
    km_intrare: int = Field(..., ge=0)
    reclamatie: Optional[str] = None
    id_vehicul: int
    id_operator: int

class ComandaCreate(ComandaBase):
    pass

class ComandaStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(DESCHISA|IN_LUCRU|FINALIZATA|PREDATA)$")
    data_predare: Optional[date] = None

class ComandaResponse(ComandaBase):
    id_comanda: int
    data_intrare: date
    data_predare: Optional[date]
    status: str
    nr_inmatriculare: Optional[str] = None
    marca_model: Optional[str] = None
    client_nume: Optional[str] = None

class LucrareEfectuataCreate(BaseModel):
    post_lucru: Optional[str] = None
    ore_lucrate: float = Field(..., ge=0)
    tarif_orar_aplicat: float = Field(..., ge=0)
    id_mecanic: int
    id_lucrare_catalog: int

class LucrareEfectuataResponse(LucrareEfectuataCreate):
    id_lucrare_efectuata: int
    id_comanda: int
    denumire_lucrare: Optional[str] = None
    mecanic_nume: Optional[str] = None

class InspectieITPCreate(BaseModel):
    km: int = Field(..., ge=0)
    emisii_co: Optional[float] = Field(None, ge=0)
    eficienta_franare: Optional[float] = Field(None, ge=0, le=100)
    convergenta: Optional[float] = None
    id_vehicul: int
    id_inspector: int

class InspectieITPResponse(InspectieITPCreate):
    id_inspectie: int
    data_inspectie: date
    rezultat: str
    data_expirare: Optional[date]
    mesaj: Optional[str] = None
