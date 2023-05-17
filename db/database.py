from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import get_connection_db


host, port, user, password, db_name = get_connection_db()

DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dépendance pour routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()