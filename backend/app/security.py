"""Autenticação: hash de senha (pbkdf2) + tokens JWT + dependências do FastAPI."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app import models

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
_ALGO = "HS256"


def hash_password(p: str) -> str:
    return pwd_context.hash(p)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        return False


def create_token(seller: models.Seller) -> str:
    exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.access_token_minutes)
    payload = {
        "sub": str(seller.id), "email": seller.email, "role": seller.role,
        "owner_id": seller.ploomes_owner_id, "name": seller.name, "exp": exp,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGO)


def current_user(token: Optional[str] = Depends(oauth2_scheme),
                 db: Session = Depends(get_session)) -> models.Seller:
    cred_exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autenticado",
                            headers={"WWW-Authenticate": "Bearer"})
    if not token:
        raise cred_exc
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGO])
        sub = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise cred_exc
    user = db.get(models.Seller, sub)
    if user is None or not user.active:
        raise cred_exc
    return user


def require_admin(user: models.Seller = Depends(current_user)) -> models.Seller:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Requer perfil admin")
    return user


def resolve_owner_id(user: models.Seller, owner_id: Optional[int]) -> int:
    """Vendedor só vê a própria carteira; admin escolhe via owner_id."""
    if user.role == "admin":
        if owner_id is None:
            raise HTTPException(400, "owner_id é obrigatório para admin")
        return int(owner_id)
    if user.ploomes_owner_id is None:
        raise HTTPException(409, "Seu usuário não está vinculado a um vendedor do Ploomes")
    return int(user.ploomes_owner_id)


def seed_admin() -> None:
    """Cria o admin inicial a partir do .env, se ainda não existir."""
    from app.db import session_scope
    with session_scope() as s:
        exists = s.query(models.Seller).filter_by(email=settings.portal_admin_email).first()
        if exists:
            return
        s.add(models.Seller(
            email=settings.portal_admin_email,
            name="Administrador",
            password_hash=hash_password(settings.portal_admin_password),
            role="admin", active=True,
        ))
