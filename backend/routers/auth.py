"""Router autentificare: login, users, schimbare parola."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from backend.auth import create_access_token, hash_password, verify_password
from backend.database import (
    create_user as db_create_user,
    delete_user_by_id,
    get_all_users,
    get_user_by_username,
    update_user_password,
)
from backend.deps import _is_admin, get_current_user

router = APIRouter()


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str


@router.get("/login")
async def login_redirect():
    """Redirect GET /login -> / (formularul de login e pe pagina principala)."""
    return RedirectResponse(url="/", status_code=302)


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login cu username si parola. Returneaza JWT token.
    Form: username, password (application/x-www-form-urlencoded)
    """
    user = get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Username sau parola incorecte.")
    token = create_access_token(data={"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer", "username": user["username"]}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    """Returneaza utilizatorul curent (pentru verificare token)."""
    return current_user


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    """Schimba parola utilizatorului curent."""
    user = get_user_by_username(current_user["username"])
    if not user or not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Parola curenta incorecta.")
    if len(body.new_password.strip()) < 8:
        raise HTTPException(status_code=400, detail="Parola noua trebuie sa aiba minim 8 caractere.")
    ok = update_user_password(current_user["username"], hash_password(body.new_password))
    if not ok:
        raise HTTPException(status_code=500, detail="Nu s-a putut actualiza parola.")
    return {"message": "Parola a fost actualizata."}


@router.get("/users")
async def list_users(current_user: dict = Depends(get_current_user)):
    """Lista utilizatori (doar admin)."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Doar admin poate vedea utilizatorii.")
    return get_all_users()


@router.post("/users")
async def create_user(
    body: CreateUserRequest,
    current_user: dict = Depends(get_current_user),
):
    """Adauga utilizator nou (doar admin)."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Doar admin poate adauga utilizatori.")
    username = (body.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username gol.")
    if len((body.password or "").strip()) < 8:
        raise HTTPException(status_code=400, detail="Parola trebuie sa aiba minim 8 caractere.")
    user = db_create_user(username, hash_password(body.password))
    if user is None:
        raise HTTPException(status_code=409, detail=f"Utilizatorul '{username}' exista deja.")
    return {"message": "Utilizator creat.", "user": {"id": user["id"], "username": user["username"]}}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Sterge utilizator (doar admin). Nu se poate sterge contul propriu."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Doar admin poate sterge utilizatori.")
    me_user = get_user_by_username(current_user["username"])
    if me_user and me_user.get("id") == user_id:
        raise HTTPException(status_code=400, detail="Nu poti sterge contul tau.")
    if not delete_user_by_id(user_id):
        raise HTTPException(status_code=404, detail="Utilizatorul nu a fost gasit sau nu s-a putut sterge.")
    return {"message": "Utilizator sters."}
