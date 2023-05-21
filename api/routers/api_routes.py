from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func, case, distinct, and_
from sqlalchemy.orm import Session
from pydantic import create_model
import pandas as pd
from typing import Optional
from datetime import date

from db.database import get_db, db_session_var
from api.models import Collecte, Achat, Categorie, CSP, Client

router = APIRouter()
category_names = ["DPH", "Alimentaire", "Textile", "Multimedia"]


@router.get("/collecte", response_class=JSONResponse)
async def read_collectes(mode: Optional[str] = "CA",
                         start_date: Optional[date] = None,
                         end_date: Optional[date] = None,
                         level: Optional[str] = None,
                         category: Optional[str] = None,
                         csp: Optional[str] = None,
                         number_of_children: Optional[int] = None,
                         skip: int =0,
                         limit: int =10000):
    global category_names
    db = next(get_db())
    db_session_var.set(db)

    # Mise au bon format des arguments
    level = None if level is None else level.upper()
    if category is not None:
        category = 'DPH' if category.lower() == 'dph' else category.title()
        category_names = [category]
    if csp is not None:
        csp = csp.upper()
    mode = mode.upper()
    
    # Vérification des erreurs de valeur des arguments
    # Levée d'une exception 400 en cas d'erreur
    are_arguments_valid = True
    
    if mode not in ('CA', 'PM', 'E'):
        are_arguments_valid = False
        message = "L'argument 'mode' doit être 'CA', 'PM', 'E' ou vide (= 'CA')"
    if level and level not in ('C', 'J', 'M', 'T', 'A'):
        are_arguments_valid = False
        message = "L'argument 'level' doit être 'C', 'J', 'M', 'T', 'A' ou vide (= 'C')"
    if category and category not in ('DPH', 'Alimentaire', 'Textile', 'Multimedia'):
        are_arguments_valid = False
        message = "L'argument 'category' doit être 'dph', 'alimentaire', 'textile', 'multimedia' ou vide (= tous)"
    if csp and csp not in ('AE', 'AACD', 'CPIS', 'PI', 'E', 'O', 'R', 'SAP'):
        are_arguments_valid = False
        message = "L'argument 'csp' doit être 'AE', 'AACD', 'CPIS', 'PI', 'E', 'O', 'R', 'SAP' ou vide (= toutes)"
    if number_of_children and number_of_children < 0:
        are_arguments_valid = False
        message = "L'argument 'number_of_children' doit être >= 0 ou vide (= pas de filtre sur l'âge)"
    if are_arguments_valid == False:
        raise HTTPException(status_code=400, detail=message)

    # Récupération du nom des tables (modèle SQLAchemy)
    CollecteTable = Collecte.__table__
    AchatTable = Achat.__table__
    CategorieTable = Categorie.__table__
    CSPTable = CSP.__table__
    ClientTable = Client.__table__

    # Construction dynamyque de la requête et du modèle Pydantic
    attributes = {}
    column_names = []

    # Requête de base (champs non calculés, GROUP BY et ORDER BY)
    def create_base_query(db):
        # Niveau de détail demandé (Collecte, Jour, Mois, Trimestre, Année) -> argument 'level'
        if level is None or level == 'C':
            attributes = {'Numéro de collecte': (int, ...), 'Date de collecte': (str, ...)}
            column_names = ["Numéro de collecte", "Date de collecte"]
            query = db.query(CollecteTable.c.id_collecte.label('Numéro de collecte'), CollecteTable.c.date_passage.label('Date de collecte'))
            group_by_elements = [CollecteTable.c.id_collecte.label('Numéro de collecte'), CollecteTable.c.date_passage.label('Date de collecte')]
            order_by_key = [CollecteTable.c.id_collecte.label("Numéro de collecte")]
        elif level == 'J':
            attributes = {'Date de collecte': (str, ...)}
            column_names = ["Date de collecte"]
            query = db.query(CollecteTable.c.date_passage.label('Date de collecte'))
            group_by_elements = [CollecteTable.c.date_passage.label('Date de collecte')]
            order_by_key = [CollecteTable.c.date_passage.label('Date de collecte')]
        elif level == 'M':
            attributes = {'Mois': (int, ...), 'Année': (int, ...)}
            column_names = ["Mois", "Année"]
            query = db.query(
                func.extract('month', CollecteTable.c.date_passage).label('Mois'),
                func.extract('year', CollecteTable.c.date_passage).label('Année')
            )
            group_by_elements = [func.extract('month', CollecteTable.c.date_passage).label('Mois'),
                                 func.extract('year', CollecteTable.c.date_passage).label('Année')]
            order_by_key = ['Année', 'Mois']
        elif level == 'T':
            attributes = {'Trimestre': (int, ...), 'Année': (int, ...)}
            column_names = ["Trimestre", "Année"]
            query = db.query(
                func.extract('quarter', CollecteTable.c.date_passage).label('Trimestre'),
                func.extract('year', CollecteTable.c.date_passage).label('Année')
            )
            group_by_elements = [func.extract('quarter', CollecteTable.c.date_passage).label('Trimestre'),
                                 func.extract('year', CollecteTable.c.date_passage).label('Année')]
            order_by_key = ['Année', 'Trimestre']
        elif level == 'A':
            column_names = ["Année"]
            attributes = {'Année': (int, ...)}
            query = db.query(func.extract('year', CollecteTable.c.date_passage).label('Année'))
            group_by_elements = [func.extract('year', CollecteTable.c.date_passage).label('Année')]
            order_by_key = ['Année']
        
        # CSP
        if csp is not None:
            attributes['CSP'] = (str, ...)
            column_names.append("CSP")
            query = query.add_columns(
                CSPTable.c.libelle.label('CSP')
                ).join(
                    ClientTable, CollecteTable.c.id_client == ClientTable.c.id_client 
                ).join(
                    CSPTable, ClientTable.c.id_csp == CSPTable.c.id_csp 
                )
            group_by_elements.append(CSPTable.c.libelle.label('CSP'))

        # Nb_enfants
        if number_of_children is not None:
            attributes["Nombre d'enfants"] = (int, ...)
            column_names.append("Nombre d'enfants")
            if csp is None:
                query = query.add_columns(
                    ClientTable.c.nb_enfants.label("Nombre d'enfants")
                    ).join(
                    ClientTable, CollecteTable.c.id_client == ClientTable.c.id_client
                    )
            else:
                query = query.add_columns(ClientTable.c.nb_enfants.label("Nombre d'enfants"))
            group_by_elements.append(ClientTable.c.nb_enfants.label("Nombre d'enfants"))

        # WHERE
        if start_date is not None:
            query = query.filter(CollecteTable.c.date_passage >= start_date)
        if end_date is not None:
            query = query.filter(CollecteTable.c.date_passage <= end_date)
        if csp is not None:
            query = query.filter(CSPTable.c.csp == csp)       
        if number_of_children is not None:
            query = query.filter(ClientTable.c.nb_enfants == number_of_children)
        if category is not None:
            query = query.filter(CategorieTable.c.libelle == category)

        # GROUP BY
        query = query.group_by(*group_by_elements)

        # ORDER BY
        query = query.order_by(*order_by_key)

        return query, group_by_elements, column_names, attributes


    # Création requête de base (champs non calculés)
    collecte_query, group_by_elements, column_names, attributes = create_base_query(db)
    
    # Nombre de collectes
    attributes["Nombre de collectes total"] = (int, ...)
    column_names.append("Nombre de collectes total")
    collecte_query = collecte_query.add_columns(func.count(distinct(CollecteTable.c.id_collecte)).label('Nombre de collectes total'))

    # Nombre de collectes par Categorie
    for category_name in category_names:
        label = f"Nombre de collectes {category_name}"
        attributes[label] = (float, ...)
        column_names.append(label)
        collecte_query = collecte_query.add_columns(
            func.count(case((and_(CategorieTable.c.libelle == category_name, AchatTable.c.montant != 0), 1), else_=None)).label(label)
        )
    collecte_query = collecte_query.join(
            AchatTable, CollecteTable.c.id_collecte == AchatTable.c.id_collecte
        ).join(
            CategorieTable, AchatTable.c.id_categorie == CategorieTable.c.id_categorie
        )

    # CA des collecte (dépense)
    attributes["CA total"] = (float, ...)
    column_names.append("CA total")
    collecte_query = collecte_query.add_columns(
        func.sum(AchatTable.c.montant).label('CA total')
        )
    
    # Montant Categorie
    for category_name in category_names:
        label = f"CA {category_name}"
        attributes[label] = (float, ...)
        column_names.append(label)
        collecte_query = collecte_query.add_columns(
            func.sum(case((CategorieTable.c.libelle == category_name, AchatTable.c.montant), else_=0)).label(label)
        )
        
    if mode in ('PM', 'E'):
        # Panier moyen des collectes
        attributes["Panier moyen global"] = (float, ...)
        column_names.append("Panier moyen global")
        collecte_query = collecte_query.add_columns(
            func.round((func.sum(AchatTable.c.montant) / func.count(distinct(CollecteTable.c.id_collecte))), 2).label('Panier moyen global')
            )

    # Résultats de la requête sous forme de dictionnaire
    results = collecte_query.offset(skip).limit(limit).all()
    
    DepensesModel = create_model("DepensesModel", **attributes)
    collectes = [DepensesModel(**{
                    key: value.isoformat() if isinstance(value, date) else value
                    for key, value in dict(zip(column_names, result)).items()
                    }) for result in results]
    
    # Réponse JSON si mode = CA
    if mode == 'CA':
        return JSONResponse([model.dict() for model in collectes])        

    # Calcul des peniers moyens par catégorie si mode = Panier ou Export
    else:
        # Transformation du dictionnaire en dataframe
        collectes = pd.DataFrame([collecte.dict() for collecte in collectes])
        
        # Ajout du panier moyen
        for category_name in category_names:
            collectes[f"Nombre de collectes {category_name}"].astype(int)
            collectes[f"Panier moyen {category_name}"] = round(collectes[f"CA {category_name}"] / collectes[f"Nombre de collectes {category_name}"], 2)

        collectes = collectes.fillna(0)

        if mode == 'PM':
            for col in collectes.columns:
                if 'CA' in col: del collectes[col]

        result = collectes.to_dict('records')

        return JSONResponse(content=result)
