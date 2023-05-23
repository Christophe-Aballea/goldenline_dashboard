from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse, JSONResponse
from fastapi.security import HTTPBasicCredentials, HTTPBearer
from fastapi.templating import Jinja2Templates
from starlette.datastructures import FormData
from typing import Optional
import pandas as pd
import json

from marketing.modules.authentication import get_token_from_cookie, get_current_user, verify_credentials, verify_activation_code, get_user_initials
from back_office.modules.accounts import get_login_type_from_email, activate_user
from db.database import run_in_db_session
import api.routers.api_routes as api
from marketing.modules.graphs import generate_graph
from marketing.modules.data_utils import get_libelle_csp_from_initials


router       = APIRouter()
templates    = Jinja2Templates(directory="marketing/templates")
security     = HTTPBearer()

ACCESS_TOKEN_EXPIRE_SECONDS = 1_800


# Route principale "marketing/"
@router.get("/")
def read_marketing_html(request: Request):
    return RedirectResponse(url="login")
            

# marketing/login/
@router.get("/login", response_class=HTMLResponse)
def login(request: Request):
    print(f"get('/login')")
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    print('post("/login")')
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
            #return {"message": f"User {email} connected", "token": f"{token}"}
            response = RedirectResponse(url="/marketing/dashboard", status_code=303)
            response.set_cookie(key="access_token", value=token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_SECONDS)
            return response


# marketing/first-login/
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
                #return {"message": f"User {email} connected", "token": f"{token}"}
                response = RedirectResponse(url="/marketing/dashboard", status_code=303)
                response.set_cookie(key="access_token", value=token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_SECONDS)
                return response

# Déconnexion
@router.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    response = RedirectResponse(url="/marketing/login", status_code=303)  # redirige l'utilisateur vers la page d'accueil après la déconnexion
    response.delete_cookie("access_token")
    return response


# marketing/dashboard/
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_form(request: Request, token: str = Depends(get_token_from_cookie)):
    current_user = get_current_user(token)
    if current_user.id_role not in [1, 3]:  # 1 et 2 sont les identifiants de rôle de superadmin et admin
        raise HTTPException(status_code=403, detail="Forbidden")
    else:
        # Récupération des intitiales de l'utilisateur connecté
        user_initials = await get_user_initials(current_user.id_user)
        # Préparation du graphique par défaut
        form_data = {"mode": "CA",
                     "start_date": None,
                     "end_date": None,
                     "detail_level": "M",
                     "rayon": "Textile",
                     "csp": None,
                     "num_children": None}
        data = await run_in_db_session(api.read_collectes, form_data["mode"], form_data["start_date"], form_data["end_date"],
                                       form_data["detail_level"], form_data["rayon"], form_data["csp"], form_data["num_children"])


        # Récupération des données sous forme de dataframe
        response_body = data.body.decode()                    # decodage bytes -> string
        response_json = json.loads(response_body)             # string -> JSON
        #print(response_json)

        collectes = pd.DataFrame.from_records(response_json)  # JSON -> DataFrame

        plots = generate_graph(collectes, form_data)

        return templates.TemplateResponse("dashboard.html",
                                          {"request": request, "user_initials": user_initials, "form_data": form_data,
                                           "plots": plots})

@router.post("/dashboard")
async def process_dashboard(request: Request, action: Optional[str] = Form(None), mode: Optional[str] = Form(None), start_date: Optional[str] = Form(None),
                            end_date: Optional[str] = Form(None), detail_level: Optional[str] = Form(None), rayon: Optional[str] = Form(None), csp: Optional[str] = Form(None), 
                            num_children: Optional[int] = Form(None), num_rows: Optional[int] = Form(None), token: str = Depends(get_token_from_cookie)):
    current_user = get_current_user(token)
    user_initials = await get_user_initials(current_user.id_user)

    # Récupération des champs saisis pour retransmission
    form_data = await request.form()
    
    # Gestion des erreurs de saisie
    error = []
    if start_date and end_date:
        if start_date > end_date:
            error.append("Veuillez vérifier que la date de début est antérieure ou égale à la date de fin.")
    if num_children and num_children < 0:
        error.append("Veuillez saisir un nombre d'enfants supérieur ou égal à 0, ou laisser le champ vide.")

    if error:
        return templates.TemplateResponse("dashboard.html",
                                          {"request": request, "error": error, "user_initials": user_initials,
                                           "form_data": form_data})

    if action == 'telecharger':
        if num_rows and num_rows <= 0:
            error = "Veullez saisir un nombre de lignes supérieur à 0, ou laisser vide pour toutes les lignes."
            return templates.TemplateResponse("dashboard.html",
                                              {"request": request, "error": error, "user_initials": user_initials,
                                               "form_data": form_data})
        
        data = await run_in_db_session(api.read_collectes, 'E', start_date, end_date, detail_level, rayon, csp, num_children)
        response_body = data.body.decode()                    # decodage bytes -> string
        response_json = json.loads(response_body)             # string -> JSON
        if "error" in response_json:
            return templates.TemplateResponse("dashboard.html",
                                            {"request": request, "error": [response_json["error"]],
                                                "user_initials": user_initials,
                                                "form_data": form_data})
        collectes = pd.DataFrame.from_records(response_json)  # JSON -> DataFrame
        if 'Numéro de collecte' in collectes.columns:
            collectes = collectes.rename(columns={'Numéro de collecte': 'Numero de collecte'})

        if num_rows is not None:
            collectes = collectes.head(num_rows)
        collectes.to_csv("gl_data.csv", index=False, mode="w", sep=";", encoding='utf8')
        
        return FileResponse("gl_data.csv", media_type="text/csv", filename="gl_data.csv")

    # Récupération des données via l'api '/api/collecte'
    data = await run_in_db_session(api.read_collectes, mode, start_date, end_date, detail_level, rayon, csp, num_children)
    
    response_body = data.body.decode()                    # decodage bytes -> string
    response_json = json.loads(response_body)             # string -> JSON

    if "error" in response_json:
        return templates.TemplateResponse("dashboard.html",
                                          {"request": request, "error": [response_json["error"]],
                                            "user_initials": user_initials,
                                            "form_data": form_data})

    collectes = pd.DataFrame.from_records(response_json)  # JSON -> DataFrame

    plots = generate_graph(collectes, form_data)

    details = []
    if start_date:
        details.append(f"Date de début : {start_date}")
    if end_date:
        details.append(f"Date de fin : {end_date}")
    if rayon:
        details.append(f"Rayon : {rayon}")
    if csp:
        details.append(f"CSP : {get_libelle_csp_from_initials(csp)}")
    if num_children:
        details.append(f"Nombre d'enfants : {num_children}")

    return templates.TemplateResponse("dashboard.html",
                                        {"request": request, "plots": plots, "user_initials": user_initials,
                                        "form_data": form_data, "details": details})
