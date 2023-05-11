from datetime import datetime, timedelta
from random import choice
from fastapi import HTTPException, Depends, Cookie
from fastapi.security import HTTPBasicCredentials
import jwt
import bcrypt
import secrets
from pydantic import BaseModel

from back_office.modules.db_utils import create_connection, users_schema


SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class TokenData(BaseModel):
    id_user: int
    email: str
    id_role: int


# Création d'un token JWT
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)
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


async def verify_credentials(credentials: HTTPBasicCredentials):
    conn = await create_connection()
    query = f"""
    SELECT id_user, email, password_hash, id_role FROM {users_schema}.users WHERE email = '{credentials.username}';"""
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


async def get_token_from_cookie(access_token: str = Cookie(None)):
    if access_token:
        return access_token
    else:
        raise HTTPException(status_code=401, detail="Not authenticated")

def get_current_user(token: str = Depends(get_token_from_cookie)) -> TokenData:
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    decoded_token = decode_access_token(token)
    return TokenData(**decoded_token)


# Génération d'un code de vérification aléatoire
# Entier de 4 chiffres différents, ne commençant pas par 0
def get_verification_code():
    verification_code = [str(choice(range(1, 10)))]

    while len(verification_code) != 4:
        digit = str(choice(range(10)))
        if digit not in verification_code:
            verification_code.append(digit)
    return verification_code