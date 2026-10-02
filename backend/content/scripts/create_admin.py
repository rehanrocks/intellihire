"""Create (or promote) a platform administrator.

There is deliberately no public endpoint for this: the first admin is created
by whoever operates the server, from the command line.

    python -m scripts.create_admin --email admin@intellihire.com --password "Admin@12345" --name "Platform Admin"

Note: use a real-looking domain; the login schema validates emails and rejects
reserved domains such as .local or .test.
"""
import argparse

from app.core.permissions import Role
from app.core.security import hash_password
from app.database.models import User, UserStatus
from app.database.session import SessionLocal
from app.services.auth_service import get_user_by_email


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", default="Platform Administrator")
    args = parser.parse_args()

    with SessionLocal() as db:
        user = get_user_by_email(db, args.email)
        if user is None:
            user = User(email=args.email.lower(), full_name=args.name, password_hash=hash_password(args.password), role=Role.PLATFORM_ADMIN, status=UserStatus.ACTIVE)
            db.add(user)
            action = "created"
        else:
            user.role = Role.PLATFORM_ADMIN
            user.status = UserStatus.ACTIVE
            user.password_hash = hash_password(args.password)
            action = "updated"
        db.commit()
        print(f"Platform admin {action}: {user.email}")


if __name__ == "__main__":
    main()
