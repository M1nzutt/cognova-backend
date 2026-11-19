"""Safe, interactive account maintenance commands."""

import argparse
import sys
from getpass import getpass

from sqlalchemy import func, select

from app.core.settings import Settings
from app.database.database import Database
from app.models.user import User
from app.schemas.register_request import RegisterRequest
from app.services.password_service import PasswordService

DEMO_EMAIL = "demo.software@example.com"


def set_demo_password() -> int:
    """Set/reset the fixed demo account password without argv or env exposure."""
    password = getpass("Nueva contraseña demo (8-12 caracteres): ")
    confirmation = getpass("Confirma la contraseña demo: ")
    if password != confirmation:
        print("Las contraseñas no coinciden.", file=sys.stderr)
        return 2
    try:
        request = RegisterRequest(
            name="Cuenta demo",
            email=DEMO_EMAIL,
            password=password,
        )
    except Exception:
        print(
            "La contraseña debe cumplir las reglas de Cognova (8-12 caracteres).",
            file=sys.stderr,
        )
        return 2

    database = Database(Settings())
    try:
        with database.session() as session:
            user = session.scalar(
                select(User)
                .where(func.lower(User.email) == DEMO_EMAIL)
                .with_for_update()
            )
            if user is None:
                print("La cuenta de demostración no existe.", file=sys.stderr)
                return 1
            user.password_hash = PasswordService().hash(
                request.password.get_secret_value()
            )
            session.commit()
    finally:
        database.dispose()

    print(f"Credencial actualizada para {DEMO_EMAIL}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cognova account maintenance")
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("set-demo-password")
    args = parser.parse_args(argv)
    if args.action == "set-demo-password":
        return set_demo_password()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
