from contextvars import ContextVar
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import get_connection_db


host, port, user, password, db_name = get_connection_db()

DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Création d'un ContextVar pour stocker une session de base de données
db_session_var = ContextVar("db_session", default=None)


# Dépendance pour routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Lance la fonction asynchrone 'function' dans un contextvar
# et renvoie le résultat à la fonction appelante
# Permet d'appeler depuis le front une fonction asynchrone faisant appel à la base de données
# sans avoir à créer de session dans le front
async def run_in_db_session(function, *args, **kwargs):
    db = SessionLocal()
    print(f"SessionLocal() returned {db}")  # add this for debugging
    try:
        db_session_var.set(db)
        print(f"db_session_var is now {db_session_var.get()}")  # add this for debugging
        result = await function(*args, **kwargs)
        return result
    except Exception as error:
        import traceback
        print(f"Erreur : {type(error)}")
        print(f"Message d'erreur : {str(error)}")
        traceback.print_exc()
    finally:
        db.close()

