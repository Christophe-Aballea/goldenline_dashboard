from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.security import HTTPBasicCredentials, HTTPBearer
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import uuid
import asyncio

import config
from config import is_in_production, config_completed_stage

from back_office.modules.prerequisites import check_prerequisites
from back_office.modules.accounts import verify_accounts, create_super_admin_account, create_user_account
from back_office.modules.data import create_database, generate_data
from back_office.modules.authentication import get_token_from_cookie, get_current_user, verify_credentials

router       = APIRouter()
templates    = Jinja2Templates(directory="back_office/templates")
security     = HTTPBearer()
tasks_status = {}

ACCESS_TOKEN_EXPIRE_SECONDS = 1_800

# Mise à jour status des tâches
def update_task_status(task_id: str, status: str):
    tasks_status[task_id] = status


# Route principale "back-office/"
@router.get("/")
def read_back_office_html(request: Request):
    # Redirection vers "back-office/login/" si le projet est en production
    if is_in_production():
        return RedirectResponse(url="/back-office/login")
    # Redirection vers la prochaine étape de mise en production
    else:
        print('@router.get("/") - Not in production')
        next_stage = config_completed_stage()
        print(next_stage)
        if next_stage is not None:
            return RedirectResponse(url=next_stage["url"])
        else:
            return {"message": "All stages are completed."}


# back-office/login/
@router.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    credentials = HTTPBasicCredentials(username=email, password=password)
    
    user_found, token = await verify_credentials(credentials)
    if user_found and token:
        if not is_in_production():
            print(config_completed_stage())
            response = RedirectResponse(url="/back-office/proute", status_code=303)
            response.set_cookie(key="access_token", value=token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_SECONDS)
            return response
        else:
            return {"message": "utilisateur reconnu, aller à l'accueil Back-office"}
    elif user_found:
        error_message = "Autorisation refusée."
    else:
        error_message = "Identifiant ou mot de passe incorrect."
    return templates.TemplateResponse("login.html", {"request": request, "error": error_message})


##########################################
# ETAPES DE MISE EN PRODUCTION DU PROJET #
##########################################

# Redirection vers l'étape suivante, appel après chaque étape réussie
@router.get("/redirect-to-next-stage")
def redirect_to_next_stage(request: Request):
    next_stage = config_completed_stage()
    if next_stage is not None:
        return RedirectResponse(url=next_stage["url"])
    else:
        return {"message": "All stages are completed."}
    

# back-office/check-prerequisites/
# Verification de la connexion au serveur PostgreSQL
# et de l'utilisateur d'application
@router.get("/check-prerequisites", response_class=HTMLResponse)
def check_prerequisites_form(request: Request):
    return templates.TemplateResponse("check_prerequisites.html", {"request": request})

@router.post("/check-prerequisites")
def process_check_prerequisites(request: Request, host: str = Form(...), port: str = Form(...), user: str = Form(...), password: str = Form(...)):
    success, message = check_prerequisites(host, port, user, password)
    if success:
        # Mise à jour du fichier de configuration, du statut de l'étape (terminée) et l'état d'avancement
        config.update_prerequisites_info(host, port, user, password)
        config.set_stage_completed("check_prerequisites")
        config.increment_stage()
        return RedirectResponse(url="/back-office/redirect-to-next-stage", status_code=303)        

    else:
        return templates.TemplateResponse("check_prerequisites.html", {"request": request, "error": message})


# back-office/create-super-admin-account/
@router.get("/create-super-admin-account", response_class=HTMLResponse)
def create_super_admin_account_form(request: Request):
    return templates.TemplateResponse("create_super_admin_account.html", {"request": request})

@router.post("/create-super-admin-account")
def process_create_super_admin_account(request: Request, prenom: str = Form(...), nom: str = Form(...), email: str = Form(...), password: str = Form(...)):
    success, message = create_super_admin_account(prenom, nom, email, password)
    if success:
        # Mise à jour du statut de l'étape (terminée) et l'état d'avancement
        # config.update_super_user_info(prenom, nom, email, password)
        config.set_stage_completed("create_super_admin_account")
        config.increment_stage()
        return RedirectResponse(url="/back-office/redirect-to-next-stage", status_code=303)        
    else:
        return templates.TemplateResponse("create_super_admin_account.html", {"request": request, "error": message})


# back-office/create-database/
@router.get("/create-database", response_class=HTMLResponse)
def create_database_form(request: Request):
    return templates.TemplateResponse("create_database.html", {"request": request})

@router.post("/create-database")
def process_create_database(request: Request, db_name: str = Form(...), source_schema: str = Form(...), marketing_schema: str = Form(...), users_schema: str = Form(...)):
    success, message = create_database(db_name, source_schema, marketing_schema, users_schema)
    #return templates.TemplateResponse("create_database.html", {"request": request, "error": message})
    #return {"message": [{"success": success, "message": message}]}
    if success:
        # Mise à jour du statut de l'étape (terminée) et l'état d'avancement
        config.update_database_info(db_name, source_schema, marketing_schema, users_schema)
        config.set_stage_completed("create_database")
        config.increment_stage()
        return RedirectResponse(url="/back-office/redirect-to-next-stage", status_code=303)        
    else:
        message = ["Un problème est survenu", "Log :"] + message + ["lien"]
        return templates.TemplateResponse("create_database.html", {"request": request, "error": message})


# back-office/generate_data/
@router.get("/generate-data", response_class=HTMLResponse)
def create_database_form(request: Request):
    return templates.TemplateResponse("generate_data.html", {"request": request})

@router.post("/generate-data")
async def process_generate_data(request: Request, customers_number: str = Form(...), collections_number: str = Form(...), start_date: str = Form(...)):
    task_id = str(uuid.uuid4())
    tasks_status[task_id] = "queued"
    customers_number = int(customers_number.replace(' ',''))
    collections_number = int(collections_number.replace(' ',''))
    asyncio.create_task(generate_data(task_id, customers_number, collections_number, start_date, update_task_status))
    return {"task_id": task_id}


# Route de gestion des tâches
@router.get("/generate-data-status/{task_id}")
async def generate_data_status(task_id: str):
    status = tasks_status.get(task_id)
    if status is None:
        return {"status": "not_found"}
    return {"status": status}

# Route test authentification
@router.get("/proute")
async def proute(token: str = Depends(get_token_from_cookie)):
    current_user = get_current_user(token)
    if current_user.id_role not in [1, 2]:  # 1 et 2 sont les identifiants de rôle de super-admin et admin
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"message": "Authorized"}