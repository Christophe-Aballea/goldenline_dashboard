from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.routers import api_routes
from back_office.routers import back_office_routes
#from marketing_frontend.routers import marketing_routes

app = FastAPI()

# Configure Jinja2 templates
templates = Jinja2Templates(directory="back_office/templates")

# Montage des routeurs pour l'API
#app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
#app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
#app.include_router(collectes.router, prefix="/api/collectes", tags=["collectes"])
#app.include_router(achats.router, prefix="/api/achats", tags=["achats"])
#app.include_router(csp.router, prefix="/api/csp", tags=["csp"])

# Montage des routeurs api, back-office et le marketing_frontend
app.include_router(back_office_routes.router, prefix="/back-office", tags=["back-office"])
app.include_router(api_routes.router, prefix="/api", tags=["api"])

# Montage des dossiers statiques pour le back-office et le marketing_frontend
app.mount("/back-office/static", StaticFiles(directory="back_office/static"), name="back-office-static")
#app.mount("/marketing/static", StaticFiles(directory="marketing_frontend/static"), name="marketing-static")

@app.get("/")
def read_root():
    return {"Hello": "World"}
