from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.security import HTTPBasicCredentials, HTTPBearer
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import uuid
import asyncio

import config
from config import is_in_production, config_completed_stage

from back_office.modules.prerequisites import check_prerequisites
from back_office.modules.accounts import list_of_existing_accounts, can_be_put_into_production, create_superadmin_account, create_user_account, get_users_by_roles, get_login_type_from_email, activate_user
from back_office.modules.data import create_database, generate_data
from back_office.modules.authentication import get_token_from_cookie, get_current_user, verify_credentials, get_verification_code, verify_activation_code, get_user_initials

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
        next_stage = config_completed_stage()
        if next_stage is not None:
            if next_stage["need_authentication"]:
                return RedirectResponse(url="login")
            else:
                return RedirectResponse(url=next_stage["url"])
        else:
            return {"message": "All stages are completed."}


# back-office/login/
@router.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    email_found, first_login = await get_login_type_from_email(email)
    if email_found == False:
        error_message = first_login
        return templates.TemplateResponse("login.html", {"request": request, "error": error_message, "email": email})
    elif first_login:
        is_activation_code_correct, message = await verify_activation_code(email, password)
        if is_activation_code_correct:
            url = "first_login.html"
            key = "success_message"
        else:
            url = "login.html"
            key = "error"
        return templates.TemplateResponse(url, {"request": request, key: message, "email": email})
    else:
        # email trouvé, 'first_login' == False
        credentials = HTTPBasicCredentials(username=email, password=password)
        success, message = await verify_credentials(credentials)
        if success == False:
            error_message = message
            return templates.TemplateResponse("login.html", {"request": request, "error": error_message, "email": email})
        else:
            token = message
            url = "/back-office/users-management" if is_in_production() else "/back-office/redirect-to-next-stage"
            response = RedirectResponse(url=url, status_code=303)
            response.set_cookie(key="access_token", value=token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_SECONDS)
            return response


# back-office/first-login/
@router.get("/first-login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse("first_login.html", {"request": request})

@router.post("/first-login")
async def first_login_form(request: Request, email: str = Form(...), password: str = Form(...), password_check: str = Form(...)):
    if password != password_check :
        error_message = ["Veuillez saisir deux fois le même mot de passe"]
        return templates.TemplateResponse("first_login.html", {"request": request, "error": error_message, "email": email})
    else:
        success, message = await activate_user(email, password)
        if success == False:
            return templates.TemplateResponse("login.html", {"request": request, "error": message, "email": email})
        else:
            credentials = HTTPBasicCredentials(username=email, password=password)
            success, message = await verify_credentials(credentials)
            if success == False:
                error_message = message
                return templates.TemplateResponse("login.html", {"request": request, "error": error_message, "email": email})
            else:
                token = message
                url = "/back-office/users-management" if is_in_production() else "/back-office/redirect-to-next-stage"
                response = RedirectResponse(url=url, status_code=303)
                response.set_cookie(key="access_token", value=token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_SECONDS)
                return response


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


# back-office/create-superadmin-account/
@router.get("/create-superadmin-account", response_class=HTMLResponse)
def create_superadmin_account_form(request: Request):
    return templates.TemplateResponse("create_superadmin_account.html", {"request": request})

@router.post("/create-superadmin-account")
def process_create_superadmin_account(request: Request, prenom: str = Form(...), nom: str = Form(...), email: str = Form(...), password: str = Form(...)):
    success, message = create_superadmin_account(prenom, nom, email, password)
    if success:
        # Mise à jour du statut de l'étape (terminée) et l'état d'avancement
        # config.update_super_user_info(prenom, nom, email, password)
        config.set_stage_completed("create_superadmin_account")
        config.increment_stage()
        return RedirectResponse(url="/back-office/redirect-to-next-stage", status_code=303)        
    else:
        return templates.TemplateResponse("create_superadmin_account.html", {"request": request, "error": message})


# back-office/create-database/
@router.get("/create-database", response_class=HTMLResponse)
def create_database_form(request: Request):
    return templates.TemplateResponse("create_database.html", {"request": request})

@router.post("/create-database")
def process_create_database(request: Request, db_name: str = Form(...), source_schema: str = Form(...), marketing_schema: str = Form(...), users_schema: str = Form(...)):
    success, message = create_database(db_name, source_schema, marketing_schema, users_schema)
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


# back-office/move-to-production/
@router.get("/move-to-production", response_class=HTMLResponse)
async def move_to_production_form(request: Request, token: str = Depends(get_token_from_cookie)):
    current_user = get_current_user(token)
    if current_user.id_role != 1 :  # Accès autorisé uniquement au superdamin
        raise HTTPException(status_code=403, detail="Forbidden")
    else:
        # Récupération de la liste des comptes existants
        list_accounts_success, accounts = await list_of_existing_accounts()
        if list_accounts_success:
            key = "accounts"
            production_success = can_be_put_into_production(accounts)
        else:
            key = "existing_accounts_error"
            production_success = False
        verification_code = get_verification_code()

    return templates.TemplateResponse("move_to_production.html",
                                      {"request": request, key: accounts, "verification_code": verification_code,
                                       "can_be_put_into_production": production_success, "form_data": {}})


@router.post("/move-to-production")
async def process_move_to_production(request: Request, name: str = Form(...), surname: str = Form(...), email: str = Form(...),
                                      role: str = Form(...), verification_code: str = Form(...)):
    # Récupération du contenu des champs, à retransmettre
    form_data = await request.form()

    # Tentative de création d'un compte
    creation_user_success, creation_message = await create_user_account(prenom=surname, nom=name, email=email, role=role,
                                                                        verification_code=verification_code)
    if creation_user_success:
        key_user = "creation_success"
        form_data = {"name": "", "surname": "", "email": "", "role": ""}
    else:
        key_user = "user_creation_error"

    # Récupération de la liste des comptes existants
    list_accounts_success, accounts = await list_of_existing_accounts()
    if list_accounts_success:
        key_accounts = "accounts"
        production_success = can_be_put_into_production(accounts)
    else:
        key_accounts = "existing_accounts_error"
        production_success = False
    # Génération d'un nouveau code de vérification
    verification_code = get_verification_code()

    return templates.TemplateResponse("move_to_production.html",
                                      {"request": request, key_user: creation_message, "form_data": form_data, key_accounts: accounts,
                                      "verification_code": verification_code, "can_be_put_into_production": production_success})


# back-office/users-management/
@router.get("/users-management", response_class=HTMLResponse)
async def filtered_accounts_list(request: Request, token: str = Depends(get_token_from_cookie)):
    current_user = get_current_user(token)
    if current_user.id_role not in [1, 2]:  # 1 et 2 sont les identifiants de rôle de superadmin et admin
        raise HTTPException(status_code=403, detail="Forbidden")
    else:
        if not is_in_production():
            # Mise à jour du statut de l'étape (terminée) et l'état d'avancement
            config.update_config("production", True)
            config.set_stage_completed("move_to_production")
            config.increment_stage()

        # Récupération des intitailes de l'utilisateur connecté
        user_initials = await get_user_initials(current_user.id_user)

        # Récupération des comptes de niveau(x) inférieur(s)
        success, value = await get_users_by_roles(1) #current_user.id_role)
        key = "accounts" if success else "error"
        for record in value:
            print(record["nom"], record["prenom"], record["email"], record["role"], record["verification_code"])

        return templates.TemplateResponse("users_management.html",
                                          {"request": request, key:value, "user_initials": user_initials, "id_user": current_user.id_user,
                                           "active_page": "users_management"})


# back-office/create-user/
@router.get("/create-user", response_class=HTMLResponse)
async def create_user_form(request: Request, token: str = Depends(get_token_from_cookie)):
    current_user = get_current_user(token)
    if current_user.id_role not in [1, 2]:  # 1 et 2 sont les identifiants de rôle de superadmin et admin
        raise HTTPException(status_code=403, detail="Forbidden")
    else:
        # Récupération des intitiales de l'utilisateur connecté
        user_initials = await get_user_initials(current_user.id_user)
        # Récupération d'un code d'activation
        verification_code = get_verification_code()
        return templates.TemplateResponse("create_user.html",
                                          {"request": request, "verification_code": verification_code,
                                           "user_initials": user_initials, "form_data": {},
                                           "active_page": "create_user"})

@router.post("/create-user")
async def process_create_user(request: Request, name: str = Form(...), surname: str = Form(...), email: str = Form(...),
                              role: str = Form(...), verification_code: str = Form(...), token: str = Depends(get_token_from_cookie)):
    current_user = get_current_user(token)
    user_initials = await get_user_initials(current_user.id_user)
    # Récupération du contenu des champs, à retransmettre
    form_data = await request.form()

    # Tentative de création d'un compte
    creation_user_success, creation_message = await create_user_account(prenom=surname, nom=name, email=email, role=role,
                                                                        verification_code=verification_code)
    if creation_user_success:
        key_user = "creation_success"
        form_data = {"name": "", "surname": "", "email": "", "role": ""}
    else:
        key_user = "user_creation_error"
    return templates.TemplateResponse("create_user.html",
                                      {"request": request, "verification_code": verification_code, key_user: creation_message,
                                       "user_initials": user_initials, "form_data": form_data,
                                       "active_page": "create_user"})


# Déconnexion
@router.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    response = RedirectResponse(url="/back-office/login", status_code=303)  # redirige l'utilisateur vers la page d'accueil après la déconnexion
    response.delete_cookie("access_token")
    return response


# Route de gestion des tâches
@router.get("/generate-data-status/{task_id}")
async def generate_data_status(task_id: str):
    status = tasks_status.get(task_id)
    if status is None:
        return {"status": "not_found"}
    return {"status": status}


# Utilisteur déconnecté
@router.get("/disconected", response_class=HTMLResponse)
async def logout(request: Request):
    return templates.TemplateResponse("disconected.html", {"request": request, "error": ["Veuillez vous identifer"]})


# Détail compte
@router.get("/detail", response_class=HTMLResponse)
async def detail(request: Request):
    return templates.TemplateResponse("not_found.html", {"request": request})


# Modification compte
@router.get("/edit", response_class=HTMLResponse)
async def edit(request: Request):
    return templates.TemplateResponse("not_found.html", {"request": request})


# Suppression compte
@router.get("/delete", response_class=HTMLResponse)
async def delete(request: Request):
    return templates.TemplateResponse("not_found.html", {"request": request})


# Edit compte current user
@router.get("/edit-account/{id_user}", response_class=HTMLResponse)
async def edit(request: Request):
    return templates.TemplateResponse("not_found.html", {"request": request})



