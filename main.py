from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse

from api.routers import api_routes
from back_office.routers import back_office_routes
from marketing.routers import marketing_routes

app = FastAPI()


# Montage des routeurs api, back-office et le marketing_frontend
app.include_router(back_office_routes.router, prefix="/back-office", tags=["back-office"])
app.include_router(api_routes.router, prefix="/api", tags=["api"])
app.include_router(marketing_routes.router, prefix="/marketing", tags=["marketing"])

# Montage des dossiers statiques pour le back-office et le marketing_frontend
app.mount("/back-office/static", StaticFiles(directory="back_office/static"), name="back-office-static")
app.mount("/marketing/static", StaticFiles(directory="marketing/static"), name="marketing-static")

@app.get("/", response_class=RedirectResponse)
def read_root():
    return RedirectResponse(url="/marketing/login")
