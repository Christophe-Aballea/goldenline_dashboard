from fastapi import Depends, Cookie, HTTPException
from pydantic import BaseModel
from back_office.modules.accounts import decode_access_token

class TokenData(BaseModel):
    id_user: int
    email: str
    id_role: int

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