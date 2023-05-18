from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from pydantic import create_model
import pandas as pd
from typing import List, Optional
from datetime import date

from db.database import get_db
from api.models import Collecte, Achat, Categorie, CSP, Client
from api.schemas import Depense, Depense2

router = APIRouter()


@router.get("/collecte", response_class=JSONResponse)
async def read_collectes(start_date: Optional[date] = None,
                         end_date: Optional[date] = None,
                         level: Optional[str] = None,
                         category: Optional[str] = None,
                         csp: Optional[str] = None,
                         child_number: Optional[int] = None,
                         skip: int =0,
                         limit: int =10000,
                         db: Session = Depends(get_db)):
    
    # TODO : vérifier validité des paramètres passés
    are_arguments_valid = True
    if level and level.upper() not in ('C', 'J', 'M', 'T', 'A'):
        are_arguments_valid = False
        message = "L'argument 'level' doit être 'C', 'J', 'M', 'T' ou 'A'"
    if category and category.lower() not in ('dph', 'alimentaire', 'textile', 'multimedia'):
        are_arguments_valid = False
        message = "L'argument 'category' doit être 'dph', 'alimentaire', 'textile' ou 'multimedia'"
    if csp and csp.upper() not in ('AE', 'AACD', 'CPIS', 'PI', 'E', 'O', 'R', 'SAP'):
        are_arguments_valid = False
        message = "L'argument 'csp' doit être 'AE', 'AACD', 'CPIS', 'PI', 'E', 'O', 'R' ou 'SAP'"
    if child_number and child_number < 0:
        are_arguments_valid = False
        message = "L'argument 'child_number' doit être >= 0"
    if are_arguments_valid == False:
        return JSONResponse(content=[{"message": message}])

    # Construction dynamyque de la requête et du modèle Pydantic
    # SELECT FROM JOIN
    # Niveau de granularité
    level = None if level is None else level.upper()
    if level is None or level == 'C':
        attributes = {'id_collecte': (int, ...)}
        attributes.update({'date_passage': (str, ...)})
        column_names = ["id_collecte", "date_passage"]
        query = db.query(Collecte.id_collecte, Collecte.date_passage)
        group_by_elements = [Collecte.id_collecte, Collecte.date_passage]
        order_by_key = [Collecte.date_passage]
    elif level == 'J':
        attributes = {'date_passage': (str, ...)}
        column_names = ["date_passage"]
        query = db.query(Collecte.date_passage)
        group_by_elements = [Collecte.date_passage]
        order_by_key = [Collecte.date_passage]
    elif level == 'M':
        attributes = {'mois': (int, ...)}
        attributes.update({'annee': (int, ...)})
        column_names = ["mois", "annee"]
        query = db.query(
            func.extract('month', Collecte.date_passage).label('mois'),
            func.extract('year', Collecte.date_passage).label('annee')
        )
        group_by_elements = ['mois', 'annee']
        order_by_key = ['annee', 'mois']
    elif level == 'T':
        attributes = {'trimestre': (int, ...)}
        attributes.update({'annee': (int, ...)})
        column_names = ["trimestre", "annee"]
        query = db.query(
            func.extract('quarter', Collecte.date_passage).label('trimestre'),
            func.extract('year', Collecte.date_passage).label('annee')
        )
        group_by_elements = ['trimestre', 'annee']
        order_by_key = ['annee', 'trimestre']
    elif level == 'A':
        column_names = ["annee"]
        attributes = {'annee': (int, ...)}
        query = db.query(func.extract('year', Collecte.date_passage).label('annee'))
        group_by_elements = ['annee']
        order_by_key = ['annee']
    
    # Montant de la collecte
    attributes.update({"montant": (float, ...)})
    column_names.append("montant")
    query = query.add_columns(
        func.sum(Achat.montant).label('montant')
        ).join(
        Achat, Collecte.id_collecte == Achat.id_collecte
        )

    # Categorie
    if category is None:
        attributes.update({'DPH': (str, ...)})
        attributes.update({'Alimentaire': (str, ...)})
        attributes.update({'Textile': (str, ...)})
        attributes.update({'Multimedia': (str, ...)})
        column_names.append("DPH")
        column_names.append("Alimentaire")
        column_names.append("Textile")
        column_names.append("Multimedia")
        query = query.add_columns(
            func.sum(case((Categorie.libelle == 'DPH', Achat.montant), else_=0)).label('DPH'),
            func.sum(case((Categorie.libelle == 'Alimentaire', Achat.montant), else_=0)).label('Alimentaire'),
            func.sum(case((Categorie.libelle == 'Textile', Achat.montant), else_=0)).label('Textile'),
            func.sum(case((Categorie.libelle == 'Multimedia', Achat.montant), else_=0)).label('Multimedia')            
            ).join(
                Categorie, Achat.id_categorie == Categorie.id_categorie
            )
    else:
        category = 'DPH' if category.lower() == 'dph' else category.title()
        attributes.update({category: (str, ...)})
        column_names.append(category)
        query = query.add_columns(
            func.sum(case((Categorie.libelle == category, Achat.montant), else_=0)).label(category)
            ).join(
            Categorie, Achat.id_categorie == Categorie.id_categorie
            )
    
    # CSP
    if csp is not None:
        attributes.update({'CSP': (str, ...)})
        column_names.append("CSP")
        query = query.add_columns(
            CSP.libelle
            ).join(
            Client, Collecte.id_client == Client.id_client 
            ).join(
                CSP, Client.id_csp == CSP.id_csp 
            )
        group_by_elements.append(CSP.libelle)

    # Nb_enfants
    if child_number is not None:
        attributes.update({'Nb_enfants': (int, ...)})
        column_names.append("Nb_enfants")
        if csp is not None:
            query = query.add_columns(
                Client.nb_enfants
                ).join(
                Client, Collecte.id_client == Client.id_client
                )
        else:
            query = query.add_columns(Client.nb_enfants)
        group_by_elements.append(Client.nb_enfants)

    # WHERE
    if start_date is not None:
        query = query.filter(Collecte.date_passage >= start_date)
    if end_date is not None:
        query = query.filter(Collecte.date_passage <= end_date)

    if csp is not None:
        query = query.filter(CSP.csp == csp.upper())
    
    if child_number is not None:
        query = query.filter(Client.nb_enfants == child_number)

    if category is not None:
        query = query.filter(Categorie.libelle == category)

    # GROUP BY
    query = query.group_by(*group_by_elements)

    # ORDER BY
    query = query.order_by(*order_by_key)

    results = query.offset(skip).limit(limit).all()
    
    CollectesModel = create_model("CollectesModel", **attributes)
    collectes = [CollectesModel(**{
                    key: value.isoformat() if isinstance(value, date) else value
                    for key, value in dict(zip(column_names, result)).items()
                    }) for result in results]
    print(collectes)
    
    return JSONResponse([model.dict() for model in collectes])



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

