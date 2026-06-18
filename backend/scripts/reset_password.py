"""Reset de senha (break-glass) — para quando alguém (inclusive o admin) esquece a senha.

Uso (a partir da pasta backend, com o venv ativo):
    python -m scripts.reset_password email@empresa.com novaSenha123

No Railway:
    railway run python -m scripts.reset_password email@empresa.com novaSenha123
"""
from __future__ import annotations

import sys

from app.db import session_scope
from app import models
from app.security import hash_password


def main() -> None:
    if len(sys.argv) < 3:
        print("uso: python -m scripts.reset_password <email> <nova_senha>")
        sys.exit(1)
    email = sys.argv[1].strip().lower()
    new_pw = sys.argv[2]
    if len(new_pw) < 4:
        print("erro: a senha precisa ter ao menos 4 caracteres")
        sys.exit(1)
    with session_scope() as s:
        u = s.query(models.Seller).filter(
            models.Seller.email == email).first()
        if u is None:
            print(f"usuário '{email}' não encontrado")
            sys.exit(1)
        u.password_hash = hash_password(new_pw)
        print(f"✓ senha de {email} ({u.role}) alterada com sucesso")


if __name__ == "__main__":
    main()
