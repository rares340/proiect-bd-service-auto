from pydantic import BaseModel, EmailStr, Field
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
    email: Optional[EmailStr] = None

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

class ComandaBase(BaseModel):
    km_intrare: int = Field(..., ge=0)
    reclamatie: Optional[str] = None
    id_vehicul: int
    id_operator: int

class ComandaCreate(ComandaBase):
    pass

class ComandaResponse(ComandaBase):
    id_comanda: int
    data_intrare: date
    data_predare: Optional[date]
    status: str

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
