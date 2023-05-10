#import jwt
#from datetime import datetime, timedelta
import bcrypt
#from fastapi import HTTPException
#from fastapi.security import HTTPBasicCredentials
import asyncpg
#import secrets

from config import config as cfg
config = cfg["database"]

"""
SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# Création d'un token JWT
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Vérification d'un token
def decode_access_token(token: str):
    try:
        token_bytes = token.encode("utf-8")
        payload = jwt.decode(token_bytes, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError as error:
        print(str(error))
        raise HTTPException(status_code=401, detail="Invalid token")
"""

def verify_accounts():
    pass


def create_super_admin_account(prenom, nom, email, password):
    # Génération du hash du mot de passe
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Requêtes SQL pour insérer les données
    insert_roles = """
INSERT INTO roles (libelle) VALUES
    ('super-admin'),
    ('admin'),
    ('user');
"""

    insert_super_admin = f"""
INSERT INTO users (prenom, nom, email, password_hash, id_role, first_login)
VALUES ('{prenom}', '{nom}', '{email}', '{password_hash}', (SELECT id_role FROM roles WHERE libelle = 'super-admin'), FALSE);
"""

    # Création du fichier 'users_data.sql'
    try:
        with open("back_office/static/sql/create_super_admin_user.sql", "w") as sql_file:
            sql_file.write(insert_roles)
            sql_file.write(insert_super_admin)
        
        return True, []
    except Exception as e:
        return False, [str(e)]



def create_user_account():
    pass


'''
async def verify_credentials(credentials: HTTPBasicCredentials):
    conn = await asyncpg.connect(database=config["db_name"], host=config["host"], port=config["port"], user=config["user"], password=config["password"])
    query = f"""
    SELECT id_user, email, password_hash, id_role FROM {config['users_schema']}.users WHERE email = '{credentials.username}';"""
    results = await conn.fetch(query)
    await conn.close()

    # Parcourir les résultats et vérifier les informations d'identification
    user_found = False
    for result in results:
        id_user = result["id_user"]
        email = result["email"]
        password_hash = result["password_hash"]
        id_role = result["id_role"]
        
        # Vérifiez si le mot de passe est correct
        if bcrypt.checkpw(credentials.password.encode("utf-8"), password_hash.encode("utf-8")):
            user_found = True
            break

    if user_found:
        if id_role in (1, 2):
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(data={"id_user": id_user, "email": email, "id_role": id_role},
                                               expires_delta=access_token_expires,)
            return True, access_token
    return user_found, None
'''