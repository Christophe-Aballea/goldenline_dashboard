from datetime import date
from pydantic import BaseModel
from typing import List, Optional


class Achat(BaseModel):
    id_achat: int
    id_collecte: int
    id_categorie: int
    montant: float

class Collecte(BaseModel):
    id_collecte: int
    date_passage: str
    id_client: str
    achats: List[Achat]

class Client(BaseModel):
    id_client: str
    nb_enfants: int
    id_csp: int

class Categorie(BaseModel):
    id_categorie: int
    libelle: str

class CSP(BaseModel):
    id_csp: int
    libelle: str
    csp: str

class Depense(BaseModel):
    id_client: str
    date_passage: date
    montant: float

    class Config:
        orm_mode = True

class Depense2(BaseModel):
    id_client: str
    date_passage: str
    montant: float
    dph: Optional[float] = None
    alimentaire: Optional[float] = None
    textile: Optional[float] = None
    multimedia: Optional[float] = None
