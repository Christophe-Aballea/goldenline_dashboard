from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.security import HTTPBasicCredentials, HTTPBearer
from fastapi.templating import Jinja2Templates

from marketing.modules.authentication import get_token_from_cookie, get_current_user, verify_credentials, get_verification_code, verify_activation_code, get_user_initials
from back_office.modules.accounts import get_login_type_from_email, activate_user


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
        return templates.TemplateResponse("dashboard.html",
                                          {"request": request, "user_initials": user_initials, "form_data": {},
                                           "active_page": "dashboard"})

@router.post("/dashboard")
async def process_dashboard(request: Request, mode: str = Form(...), start_date: str = Form(...), end_date: str = Form(...),
                            token: str = Depends(get_token_from_cookie)):
    current_user = get_current_user(token)
    user_initials = await get_user_initials(current_user.id_user)
    # Récupération du contenu des champs, à retransmettre
    form_data = await request.form()

    # Création du graphique
    return {"msg": f'{mode} - {start_date} - {end_date}'}
    """
    creation_user_success, creation_message = await dashboard_account(prenom=surname, nom=name, email=email, role=role,
                                                                        verification_code=verification_code)
    if creation_user_success:
        key_user = "creation_success"
        form_data = {"name": "", "surname": "", "email": "", "role": ""}
    else:
        key_user = "user_creation_error"
    return templates.TemplateResponse("dashboard.html",
                                      {"request": request, "verification_code": verification_code, key_user: creation_message,
                                       "user_initials": user_initials, "verification_code": verification_code, "form_data": form_data,
                                       "active_page": "dashboard"})
    """

