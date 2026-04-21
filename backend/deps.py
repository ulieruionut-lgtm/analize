"""Dependente FastAPI partajate: autentificare, autorizare, conexiune DB."""
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.auth import decode_token

_HTTP_BEARER = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_HTTP_BEARER),
) -> dict:
    """Verifica JWT si returneaza user dict. Ridica 401 daca nu e autentificat."""
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Nu esti autentificat. Logheaza-te.")
    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Token invalid sau expirat.")
    return {"username": payload["sub"]}


def _is_admin(current_user: dict) -> bool:
    return (current_user or {}).get("username", "").lower() == "admin"


def postgresql_connect(url: str):
    """PostgreSQL cu timeout fix — fara connect implicit care poate bloca in thread-ul de startup."""
    import psycopg2
    return psycopg2.connect(url, connect_timeout=25)
