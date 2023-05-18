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
            return {"message": f"User {email} connected", "token": f"{token}"}
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
                return {"message": f"User {email} connected", "token": f"{token}"}
                response = RedirectResponse(url="/marketing/dashboard", status_code=303)
                response.set_cookie(key="access_token", value=token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_SECONDS)
                return response

