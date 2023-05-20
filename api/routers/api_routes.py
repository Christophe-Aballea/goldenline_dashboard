from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import Table, MetaData, select, func, case, distinct, and_, alias
from sqlalchemy.orm import Session
from pydantic import create_model
#import pandas as pd
from typing import List, Optional
from datetime import date

from db.database import get_db
from api.models import Collecte, Achat, Categorie, CSP, Client
#from api.schemas import Depense, Depense2

router = APIRouter()

#metadata = MetaData()



@router.get("/collecte", response_class=JSONResponse)
async def read_collectes(mode: Optional[str] = "D",
                         start_date: Optional[date] = None,
                         end_date: Optional[date] = None,
                         level: Optional[str] = None,
                         category: Optional[str] = None,
                         csp: Optional[str] = None,
                         number_of_children: Optional[int] = None,
                         skip: int =0,
                         limit: int =10000,
                         db: Session = Depends(get_db)):
    
    # TODO : vérifier validité des paramètres passés

    level = None if level is None else level.upper()
    if category is not None:
        category = 'DPH' if category.lower() == 'dph' else category.title()
    if csp is not None:
        csp = csp.upper()

    are_arguments_valid = True
    mode = mode.upper()
    if mode not in ('D', 'P', 'E'):
        are_arguments_valid = False
        message = "L'argument 'mode' doit être 'D', 'P', 'E' ou vide (= 'D')"
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

    
    CollecteTable = Collecte.__table__
    AchatTable = Achat.__table__
    CategorieTable = Categorie.__table__
    CSPTable = CSP.__table__
    ClientTable = Client.__table__

    # Construction dynamyque de la requête et du modèle Pydantic
    # SELECT FROM JOIN
    # Niveau de détail 

    attributes = {}
    group_by_elements = []
    order_by_key = []
    column_names = []

    def create_base_subquery(db):
        if level is None or level == 'C':
            attributes = {'Numéro de collecte': (int, ...), 'Date de collecte': (str, ...)}
            column_names = ["Numéro de collecte", "Date de collecte"]
            subquery = db.query(CollecteTable.c.id_collecte.label('Numéro de collecte'), CollecteTable.c.date_passage.label('Date de collecte'))
            group_by_elements = [CollecteTable.c.id_collecte.label('Numéro de collecte'), CollecteTable.c.date_passage.label('Date de collecte')]
            order_by_key = [CollecteTable.c.id_collecte]
        elif level == 'J':
            attributes = {'Date de collecte': (str, ...)}
            column_names = ["Date de collecte"]
            subquery = db.query(CollecteTable.c.date_passage.label('Date de collecte'))
            group_by_elements = [CollecteTable.c.date_passage.label('Date de collecte')]
            order_by_key = [CollecteTable.c.date_passage]
        elif level == 'M':
            attributes = {'Mois': (int, ...), 'Année': (int, ...)}
            column_names = ["Mois", "Année"]
            subquery = db.query(
                func.extract('month', CollecteTable.c.date_passage).label('Mois'),
                func.extract('year', CollecteTable.c.date_passage).label('Année')
            )
            group_by_elements = [func.extract('month', CollecteTable.c.date_passage).label('Mois'),
                                 func.extract('year', CollecteTable.c.date_passage).label('Année')]
            order_by_key = ['Année', 'Mois']
        elif level == 'T':
            attributes = {'Trimestre': (int, ...), 'Année': (int, ...)}
            column_names = ["Trimestre", "Année"]
            subquery = db.query(
                func.extract('quarter', CollecteTable.c.date_passage).label('Trimestre'),
                func.extract('year', CollecteTable.c.date_passage).label('Année')
            )
            group_by_elements = [func.extract('quarter', CollecteTable.c.date_passage).label('Trimestre'),
                                 func.extract('year', CollecteTable.c.date_passage).label('Année')]
            order_by_key = ['Année', 'Trimestre']
        elif level == 'A':
            column_names = ["Année"]
            attributes = {'Année': (int, ...)}
            subquery = db.query(func.extract('year', CollecteTable.c.date_passage).label('Année'))
            group_by_elements = [func.extract('year', CollecteTable.c.date_passage).label('Année')]
            order_by_key = ['Année']
        
        # CSP
        if csp is not None:
            attributes['CSP'] = (str, ...)
            column_names.append("CSP")
            subquery = subquery.add_columns(
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
                subquery = subquery.add_columns(
                    ClientTable.c.nb_enfants.label("Nombre d'enfants")
                    ).join(
                    ClientTable, CollecteTable.c.id_client == ClientTable.c.id_client
                    )
            else:
                subquery = subquery.add_columns(ClientTable.c.nb_enfants.label("Nombre d'enfants"))
            group_by_elements.append(ClientTable.c.nb_enfants.label("Nombre d'enfants"))

        # WHERE
        if start_date is not None:
            subquery = subquery.filter(CollecteTable.c.date_passage >= start_date)
        if end_date is not None:
            subquery = subquery.filter(CollecteTable.c.date_passage <= end_date)

        if csp is not None:
            subquery = subquery.filter(CSPTable.c.csp == csp)
        
        if number_of_children is not None:
            subquery = subquery.filter(ClientTable.c.nb_enfants == number_of_children)

        if category is not None:
            subquery = subquery.filter(CategorieTable.c.libelle == category)

        # GROUP BY
        subquery = subquery.group_by(*group_by_elements)

        # ORDER BY
        subquery = subquery.order_by(*order_by_key)

        return subquery, group_by_elements, column_names, attributes

    
    depenses_subquery, group_by_elements, column_names, attributes = create_base_subquery(db)

    # MODE = DEPENSES (D)
    if mode == 'D':
        # Montant des collecte (dépense)
        attributes["Dépense"] = (float, ...)
        column_names.append("Dépense")
        depenses_subquery = depenses_subquery.add_columns(
            func.sum(AchatTable.c.montant).label('Dépense')
            ).join(
            AchatTable, CollecteTable.c.id_collecte == AchatTable.c.id_collecte
            )        
        # Montant Categorie
        if category is None:
            attributes['Dépense DPH'] = (float, ...)
            attributes['Dépense Alimentaire'] = (float, ...)
            attributes['Dépense Textile'] = (float, ...)
            attributes['Dépense Multimedia'] = (float, ...)
            column_names.append("Dépense DPH")
            column_names.append("Dépense Alimentaire")
            column_names.append("Dépense Textile")
            column_names.append("Dépense Multimedia")
            depenses_subquery = depenses_subquery.add_columns(
                func.sum(case((CategorieTable.c.libelle == 'DPH', AchatTable.c.montant), else_=0)).label('Dépense DPH'),
                func.sum(case((CategorieTable.c.libelle == 'Alimentaire', AchatTable.c.montant), else_=0)).label('Dépense Alimentaire'),
                func.sum(case((CategorieTable.c.libelle == 'Textile', AchatTable.c.montant), else_=0)).label('Dépense Textile'),
                func.sum(case((CategorieTable.c.libelle == 'Multimedia', AchatTable.c.montant), else_=0)).label('Dépense Multimedia')            
                ).join(
                    CategorieTable, AchatTable.c.id_categorie == CategorieTable.c.id_categorie
                )
        else:
            label = f"Dépense {category}"
            attributes[label] = (float, ...)
            column_names.append(label)
            depenses_subquery = depenses_subquery.add_columns(
                func.sum(case((CategorieTable.c.libelle == category, AchatTable.c.montant), else_=0)).label(label)
                ).join(
                    CategorieTable, AchatTable.c.id_categorie == CategorieTable.c.id_categorie
                )
        
        results = depenses_subquery.offset(skip).limit(limit).all()
        
        DepensesModel = create_model("DepensesModel", **attributes)
        collectes = [DepensesModel(**{
                        key: value.isoformat() if isinstance(value, date) else value
                        for key, value in dict(zip(column_names, result)).items()
                        }) for result in results]

        return JSONResponse([model.dict() for model in collectes])        


    # MODE PANIER MOYEN (P)
    if mode == "P":
        # Calcul panier moyen des collectes
        attributes["Panier moyen"] = (float, ...)
        column_names.append("Panier moyen")
        depenses_subquery = depenses_subquery.add_columns(
            func.round((func.sum(AchatTable.c.montant) / func.count(distinct(CollecteTable.c.id_collecte))), 2).label('Panier moyen')
            ).join(
            AchatTable, CollecteTable.c.id_collecte == AchatTable.c.id_collecte
            )
        
        # Panier moyen par catégorie
        #     = (Total dépense de la catégorie) / (Nombre de collectes != 0 de la catégorie)
        if category is None:
            attributes['Panier moyen DPH'] = (float, ...)
            attributes['Panier moyen Alimentaire'] = (float, ...)
            attributes['Panier moyen Textile'] = (float, ...)
            attributes['Panier moyen Multimedia'] = (float, ...)
            column_names.append("Panier moyen DPH")
            column_names.append("Panier moyen Alimentaire")
            column_names.append("Panier moyen Textile")
            column_names.append("Panier moyen Multimedia")
            depenses_subquery = depenses_subquery.add_columns(
                func.round(
                    case(
                        (func.count(case((and_(CategorieTable.c.libelle == 'DPH', AchatTable.c.montant != 0), 1), else_=0)) != 0,
                        func.sum(case((CategorieTable.c.libelle == 'DPH', AchatTable.c.montant), else_=0)) / func.count(case((and_(CategorieTable.c.libelle == 'DPH', AchatTable.c.montant != 0), 1), else_=0))
                    ),
                    else_=None
                )).label('Panier moyen DPH'),
                func.round(
                    case(
                        (func.count(case((and_(CategorieTable.c.libelle == 'Alimentaire', AchatTable.c.montant != 0), 1), else_=0)) != 0,
                        func.sum(case((CategorieTable.c.libelle == 'Alimentaire', AchatTable.c.montant), else_=0)) / func.count(case((and_(CategorieTable.c.libelle == 'Alimentaire', AchatTable.c.montant != 0), 1), else_=0))
                    ),
                    else_=None
                )).label('Panier moyen Alimentaire'),
                func.round(
                    case(
                        (func.count(case((and_(CategorieTable.c.libelle == 'Textile', AchatTable.c.montant != 0), 1), else_=0)) != 0,
                        func.sum(case((CategorieTable.c.libelle == 'Textile', AchatTable.c.montant), else_=0)) / func.count(case((and_(CategorieTable.c.libelle == 'Textile', AchatTable.c.montant != 0), 1), else_=0))
                    ),
                    else_=None
                )).label('Panier moyen Textile'),
                func.round(
                    case(
                        (func.count(case((and_(CategorieTable.c.libelle == 'Multimedia', AchatTable.c.montant != 0), 1), else_=0)) != 0,
                        func.sum(case((CategorieTable.c.libelle == 'Multimedia', AchatTable.c.montant), else_=0)) / func.count(case((and_(CategorieTable.c.libelle == 'Multimedia', AchatTable.c.montant != 0), 1), else_=0))
                    ),
                    else_=None
                )).label('Panier moyen Multimedia'),
            ).join(
                CategorieTable, AchatTable.c.id_categorie == CategorieTable.c.id_categorie
            )
        else:
            label = f"Panier moyen {category}"
            attributes[label] = (float, ...)
            column_names.append(label)
            depenses_subquery = depenses_subquery.add_columns(
                func.round(func.sum(case((CategorieTable.c.libelle == category, AchatTable.c.montant), else_=0)) / func.count(case((and_(CategorieTable.c.libelle == category, AchatTable.c.montant != 0), 1), else_=None)), 2).label(label)
                ).join(
                CategorieTable, AchatTable.c.id_categorie == CategorieTable.c.id_categorie
                )

        results = depenses_subquery.offset(skip).limit(limit).all()
        
        DepensesModel = create_model("DepensesModel", **attributes)
        collectes = [DepensesModel(**{
                        key: value.isoformat() if isinstance(value, date) else value
                        for key, value in dict(zip(column_names, result)).items()
                        }) for result in results]

        return JSONResponse([model.dict() for model in collectes])        




    # MODE EXPORT (E)
    if mode == 'E':
        # Nombre de collectes
        attributes["Nombre de collectes"] = (int, ...)
        column_names.append("Nombre de collectes")
        depenses_subquery = depenses_subquery.add_columns(func.count(distinct(CollecteTable.c.id_collecte)).label('Nombre de collectes'))

        # Montant des (dépense)
        attributes["Dépense"] = (float, ...)
        column_names.append("Dépense")
        depenses_subquery = depenses_subquery.add_columns(
            func.sum(AchatTable.c.montant).label('Dépense')
            ).join(
            AchatTable, CollecteTable.c.id_collecte == AchatTable.c.id_collecte
            )

        # Panier moyen des collectes
        attributes["Panier moyen"] = (float, ...)
        column_names.append("Panier moyen")
        depenses_subquery = depenses_subquery.add_columns(
            func.round((func.sum(AchatTable.c.montant) / func.count(distinct(CollecteTable.c.id_collecte))), 2).label('Panier moyen')
            )

        # Nombre de collectes par Categorie
        if category is None:
            attributes['Nombre de collectes DPH'] = (float, ...)
            attributes['Nombre de collectes Alimentaire'] = (float, ...)
            attributes['Nombre de collectes Textile'] = (float, ...)
            attributes['Nombre de collectes Multimedia'] = (float, ...)
            column_names.append("Nombre de collectes DPH")
            column_names.append("Nombre de collectes Alimentaire")
            column_names.append("Nombre de collectes Textile")
            column_names.append("Nombre de collectes Multimedia")
            depenses_subquery = depenses_subquery.add_columns(
                func.count(case((and_(CategorieTable.c.libelle == 'DPH', AchatTable.c.montant != 0), 1), else_=None)).label('Nombre de collectes DPH'),
                func.count(case((and_(CategorieTable.c.libelle == 'Alimentaire', AchatTable.c.montant != 0), 1), else_=None)).label('Nombre de collectes Alimentaire'),
                func.count(case((and_(CategorieTable.c.libelle == 'Textile', AchatTable.c.montant != 0), 1), else_=None)).label('Nombre de collectes Textile'),
                func.count(case((and_(CategorieTable.c.libelle == 'Multimedia', AchatTable.c.montant != 0), 1), else_=None)).label('Nombre de collectes Multimedia')
                ).join(
                    CategorieTable, AchatTable.c.id_categorie == CategorieTable.c.id_categorie
                )
        else:
            label = f"Nombre collectes {category}"
            attributes[label] = (float, ...)
            column_names.append(label)
            depenses_subquery = depenses_subquery.add_columns(
                func.count(case((and_(CategorieTable.c.libelle == category, AchatTable.c.montant != 0), 1), else_=None)).label(label)
                ).join(
                    CategorieTable, AchatTable.c.id_categorie == CategorieTable.c.id_categorie
                )

        # Montant Categorie
        if category is None:
            attributes['Dépense DPH'] = (float, ...)
            attributes['Dépense Alimentaire'] = (float, ...)
            attributes['Dépense Textile'] = (float, ...)
            attributes['Dépense Multimedia'] = (float, ...)
            column_names.append("Dépense DPH")
            column_names.append("Dépense Alimentaire")
            column_names.append("Dépense Textile")
            column_names.append("Dépense Multimedia")
            depenses_subquery = depenses_subquery.add_columns(
                func.sum(case((CategorieTable.c.libelle == 'DPH', AchatTable.c.montant), else_=0)).label('Dépense DPH'),
                func.sum(case((CategorieTable.c.libelle == 'Alimentaire', AchatTable.c.montant), else_=0)).label('Dépense Alimentaire'),
                func.sum(case((CategorieTable.c.libelle == 'Textile', AchatTable.c.montant), else_=0)).label('Dépense Textile'),
                func.sum(case((CategorieTable.c.libelle == 'Multimedia', AchatTable.c.montant), else_=0)).label('Dépense Multimedia')            
                )
        else:
            label = f"Dépense {category}"
            attributes[label] = (float, ...)
            column_names.append(label)
            depenses_subquery = depenses_subquery.add_columns(
                func.sum(case((CategorieTable.c.libelle == category, AchatTable.c.montant), else_=0)).label(label)
                )
        
        # Panier moyen par catégorie
        #     = (Total dépense de la catégorie) / (Nombre de collectes != 0 de la catégorie)
        if category is None:
            attributes['Panier moyen DPH'] = (float, ...)
            attributes['Panier moyen Alimentaire'] = (float, ...)
            attributes['Panier moyen Textile'] = (float, ...)
            attributes['Panier moyen Multimedia'] = (float, ...)
            column_names.append("Panier moyen DPH")
            column_names.append("Panier moyen Alimentaire")
            column_names.append("Panier moyen Textile")
            column_names.append("Panier moyen Multimedia")
            depenses_subquery = depenses_subquery.add_columns(
                func.round(
                    case(
                        (func.count(case((and_(CategorieTable.c.libelle == 'DPH', AchatTable.c.montant != 0), 1), else_=0)) != 0,
                        func.sum(case((CategorieTable.c.libelle == 'DPH', AchatTable.c.montant), else_=0)) / func.count(case((and_(CategorieTable.c.libelle == 'DPH', AchatTable.c.montant != 0), 1), else_=0))
                    ),
                    else_=0
                )).label('Panier moyen DPH'),
                func.round(
                    case(
                        (func.count(case((and_(CategorieTable.c.libelle == 'Alimentaire', AchatTable.c.montant != 0), 1), else_=0)) != 0,
                        func.sum(case((CategorieTable.c.libelle == 'Alimentaire', AchatTable.c.montant), else_=0)) / func.count(case((and_(CategorieTable.c.libelle == 'Alimentaire', AchatTable.c.montant != 0), 1), else_=0))
                    ),
                    else_=0
                )).label('Panier moyen Alimentaire'),
                func.round(
                    case(
                        (func.count(case((and_(CategorieTable.c.libelle == 'Textile', AchatTable.c.montant != 0), 1), else_=0)) != 0,
                        func.sum(case((CategorieTable.c.libelle == 'Textile', AchatTable.c.montant), else_=0)) / func.count(case((and_(CategorieTable.c.libelle == 'Textile', AchatTable.c.montant != 0), 1), else_=0))
                    ),
                    else_=0
                )).label('Panier moyen Textile'),
                func.round(
                    case(
                        (func.count(case((and_(CategorieTable.c.libelle == 'Multimedia', AchatTable.c.montant != 0), 1), else_=0)) != 0,
                        func.sum(case((CategorieTable.c.libelle == 'Multimedia', AchatTable.c.montant), else_=0)) / func.count(case((and_(CategorieTable.c.libelle == 'Multimedia', AchatTable.c.montant != 0), 1), else_=0))
                    ),
                    else_=0
                )).label('Panier moyen Multimedia'),
            )
        else:
            label = f"Panier moyen {category}"
            attributes[label] = (float, ...)
            column_names.append(label)
            depenses_subquery = depenses_subquery.add_columns(
                func.round(func.sum(case((CategorieTable.c.libelle == category, AchatTable.c.montant), else_=0)) / func.count(case((and_(CategorieTable.c.libelle == category, AchatTable.c.montant != 0), 1), else_=0)), 2).label(label)
                )
        
        results = depenses_subquery.offset(skip).limit(limit).all()
        
        DepensesModel = create_model("DepensesModel", **attributes)
        collectes = [DepensesModel(**{
                        key: value.isoformat() if isinstance(value, date) else value
                        for key, value in dict(zip(column_names, result)).items()
                        }) for result in results]

        return JSONResponse([model.dict() for model in collectes])        



"""

    else:
        print(column_names)
        print(attributes)
        print(group_by_elements)

        depenses_subquery_alias = alias(depenses_subquery.subquery())
        paniers_subquery_alias = alias(depenses_subquery.subquery())

        onclause = and_(*[getattr(depenses_subquery_alias.c, column.name) == getattr(paniers_subquery_alias.c, column.name) for column in group_by_elements])

        # Création de la jointure
        join_obj = depenses_subquery_alias.join(paniers_subquery_alias, onclause)

        # Les noms de colonnes communs
        common_columns_names = list(set(depenses_subquery_alias.c.keys()).intersection(set(paniers_subquery_alias.c.keys())))

        # Les noms de colonnes calculées pour depenses et paniers
        calculated_columns_depenses_names = list(set(depenses_subquery_alias.c.keys()).difference(set(paniers_subquery_alias.c.keys())))
        calculated_columns_paniers_names = list(set(paniers_subquery_alias.c.keys()).difference(set(depenses_subquery_alias.c.keys())))

        # Créez les listes de colonnes en respectant l'ordre de column_names
        common_columns = [depenses_subquery_alias.c[name] for name in column_names if name in common_columns_names]
        calculated_columns_depenses = [depenses_subquery_alias.c[name] for name in column_names if name in calculated_columns_depenses_names]
        calculated_columns_paniers = [paniers_subquery_alias.c[name] for name in column_names if name in calculated_columns_paniers_names]
        # Construction de la requête SELECT
        query = select(*common_columns, *calculated_columns_depenses, *calculated_columns_paniers).select_from(join_obj)

        # Exécution de la requête
        results = db.execute(query)
              
        DepensesModel = create_model("DepensesModel", **attributes)

        collectes = [DepensesModel(**{
                        key: value.isoformat() if isinstance(value, date) else value
                        for key, value in dict(zip(column_names, result)).items()
                        }) for result in results]
        print(collectes)

        return JSONResponse([model.dict() for model in collectes])



@router.get("/collecte", response_class=JSONResponse)
async def read_collectes(mode: Optional[str] = "D",
                         start_date: Optional[date] = None,
                         end_date: Optional[date] = None,
                         level: Optional[str] = None,
                         category: Optional[str] = None,
                         csp: Optional[str] = None,
                         number_of_children: Optional[int] = None,
                         skip: int =0,
                         limit: int =10000,
                         db: Session = Depends(get_db)):
    
    # TODO : vérifier validité des paramètres passés
    are_arguments_valid = True
    mode = mode.upper()
    if mode not in ('D', 'P', 'E'):
        are_arguments_valid = False
        message = "L'argument 'mode' doit être 'D', 'P' ou 'E'"
    if level and level.upper() not in ('C', 'J', 'M', 'T', 'A'):
        are_arguments_valid = False
        message = "L'argument 'level' doit être 'C', 'J', 'M', 'T' ou 'A'"
    if category and category.lower() not in ('dph', 'alimentaire', 'textile', 'multimedia'):
        are_arguments_valid = False
        message = "L'argument 'category' doit être 'dph', 'alimentaire', 'textile' ou 'multimedia'"
    if csp and csp.upper() not in ('AE', 'AACD', 'CPIS', 'PI', 'E', 'O', 'R', 'SAP'):
        are_arguments_valid = False
        message = "L'argument 'csp' doit être 'AE', 'AACD', 'CPIS', 'PI', 'E', 'O', 'R' ou 'SAP'"
    if number_of_children and number_of_children < 0:
        are_arguments_valid = False
        message = "L'argument 'number_of_children' doit être >= 0"
    if are_arguments_valid == False:
        raise HTTPException(status_code=400, detail=message)


    # Construction dynamyque de la requête et du modèle Pydantic
    # SELECT FROM JOIN
    # Niveau de granularité
    level = None if level is None else level.upper()
    if level is None or level == 'C':
        attributes = {'id_collecte': (int, ...)}
        attributes.update({'Date de collecte': (str, ...)})
        column_names = ["id_collecte", "Date de collecte"]
        query = db.query(Collecte.id_collecte, Collecte.date_passage)
        group_by_elements = [Collecte.id_collecte, Collecte.date_passage]
        order_by_key = [Collecte.id_collecte]
    elif level == 'J':
        attributes = {'Date de collecte': (str, ...)}
        column_names = ["Date de collecte"]
        query = db.query(Collecte.date_passage)
        group_by_elements = [Collecte.date_passage]
        order_by_key = [Collecte.date_passage]
    elif level == 'M':
        attributes = {'Mois': (int, ...)}
        attributes.update({'Année': (int, ...)})
        column_names = ["Mois", "Année"]
        query = db.query(
            func.extract('month', Collecte.date_passage).label('Mois'),
            func.extract('year', Collecte.date_passage).label('Année')
        )
        group_by_elements = ['Mois', 'Année']
        order_by_key = ['Année', 'Mois']
    elif level == 'T':
        attributes = {'Trimestre': (int, ...)}
        attributes.update({'Année': (int, ...)})
        column_names = ["Trimestre", "Année"]
        query = db.query(
            func.extract('quarter', Collecte.date_passage).label('Trimestre'),
            func.extract('year', Collecte.date_passage).label('Année')
        )
        group_by_elements = ['Trimestre', 'Année']
        order_by_key = ['Année', 'Trimestre']
    elif level == 'A':
        column_names = ["Année"]
        attributes = {'Année': (int, ...)}
        query = db.query(func.extract('year', Collecte.date_passage).label('Année'))
        group_by_elements = ['Année']
        order_by_key = ['Année']
    
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
    if number_of_children is not None:
        attributes.update({"Nombre d'enfants": (int, ...)})
        column_names.append("Nombre d'enfants")
        if csp is None:
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
    
    if number_of_children is not None:
        query = query.filter(Client.nb_enfants == number_of_children)

    if category is not None:
        query = query.filter(Categorie.libelle == category)

    # GROUP BY
    query = query.group_by(*group_by_elements)

    # ORDER BY
    query = query.order_by(*order_by_key)




    if mode == 'E':
        # Nombre de collectes
        attributes.update({"Nombre de collectes": (int, ...)})
        column_names.append("Nombre de collectes")
        query = query.add_columns(func.count(distinct(Collecte.id_collecte)).label('Nombre de collectes'))
    
    if mode in ('D', 'E'):
        # Montant de la collecte (dépense)
        attributes.update({"Dépense": (float, ...)})
        column_names.append("Dépense")
        query = query.add_columns(
            func.sum(Achat.montant).label('montant')
            ).join(
            Achat, Collecte.id_collecte == Achat.id_collecte
            )

    if mode in ('P', 'E'):
        # Calcul panier moyen des collectes
        attributes.update({"Panier moyen": (float, ...)})
        column_names.append("Panier moyen")
        if mode == 'P':
            query = query.add_columns(
                func.round((func.sum(Achat.montant) / func.count(distinct(Collecte.id_collecte))), 2).label('Panier moyen')
                ).join(
                Achat, Collecte.id_collecte == Achat.id_collecte
                )
        else:
            query = query.add_columns(
                func.round((func.sum(Achat.montant) / func.count(distinct(Collecte.id_collecte))), 2).label('Panier moyen')
                )
        
    # Categorie
    if category is None:
        attributes.update({'Dépense DPH': (float, ...)})
        attributes.update({'Dépense Alimentaire': (float, ...)})
        attributes.update({'Dépense Textile': (float, ...)})
        attributes.update({'Dépense Multimedia': (float, ...)})
        column_names.append("Dépense DPH")
        column_names.append("Dépense Alimentaire")
        column_names.append("Dépense Textile")
        column_names.append("Dépense Multimedia")
        query = query.add_columns(
            func.sum(case((Categorie.libelle == 'DPH', Achat.montant), else_=0)).label('Dépense DPH'),
            func.sum(case((Categorie.libelle == 'Alimentaire', Achat.montant), else_=0)).label('Dépense Alimentaire'),
            func.sum(case((Categorie.libelle == 'Textile', Achat.montant), else_=0)).label('Dépense Textile'),
            func.sum(case((Categorie.libelle == 'Multimedia', Achat.montant), else_=0)).label('Dépense Multimedia')            
            ).join(
                Categorie, Achat.id_categorie == Categorie.id_categorie
            )
    else:
        category = 'DPH' if category.lower() == 'dph' else category.title()
        label = f"Dépense {category}"
        attributes.update({label: (float, ...)})
        column_names.append(label)
        query = query.add_columns(
            func.sum(case((Categorie.libelle == category, Achat.montant), else_=0)).label(label)
            ).join(
            Categorie, Achat.id_categorie == Categorie.id_categorie
            )


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

"""