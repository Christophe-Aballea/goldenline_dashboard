from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from db.database import SessionLocal
from typing import List

from api.models import Collecte, Achat
from api.schemas import Depense

router = APIRouter()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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