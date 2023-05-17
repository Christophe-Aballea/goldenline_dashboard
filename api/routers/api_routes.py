from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from db.database import get_db
from typing import List
from pydantic.json import pydantic_encoder

from api.models import Collecte, Achat, Categorie
from api.schemas import Depense, Depense2

router = APIRouter()


@router.get("/depense", response_model=List[Depense])
async def read_depenses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    results = db.query(
        Collecte.id_client,
        Collecte.date_passage,
        func.sum(Achat.montant).label('montant')
    ).join(
        Achat, Collecte.id_collecte == Achat.id_collecte
    ).group_by(
        Collecte.id_client,
        Collecte.date_passage
    ).offset(skip).limit(limit).all()

    depenses = [Depense(id_client=r.id_client, date_passage=r.date_passage, montant=r.montant) for r in results]
    return depenses


#@router.get("/depense2", response_model=List[Depense])
@router.get("/depense2", response_class=JSONResponse)
async def read_depenses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    results = db.query(
        Collecte.id_client,
        Collecte.date_passage,
        func.sum(Achat.montant).label('montant'),
        func.sum(case((Categorie.libelle == 'DPH', Achat.montant), else_=0)).label('dph'),
        func.sum(case((Categorie.libelle == 'Alimentaire', Achat.montant), else_=0)).label('alimentaire'),
        func.sum(case((Categorie.libelle == 'Textile', Achat.montant), else_=0)).label('textile'),
        func.sum(case((Categorie.libelle == 'Multimedia', Achat.montant), else_=0)).label('multimedia')
    ).join(
        Achat, Collecte.id_collecte == Achat.id_collecte
    ).join(
        Categorie, Achat.id_categorie == Categorie.id_categorie
    ).group_by(
        Collecte.id_client,
        Collecte.date_passage
    ).offset(skip).limit(limit).all()
    
    depenses = [Depense2(id_client=r[0],
                         date_passage=r[1].isoformat(),
                         montant=float(r[2]),
                         dph=float(r[3]),
                         alimentaire=float(r[4]),
                         textile=float(r[5]),
                         multimedia=float(r[6])) for r in results]

    return JSONResponse(content=[depense.dict() for depense in depenses])

