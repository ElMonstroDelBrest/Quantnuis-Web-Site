#!/usr/bin/env python3
"""
Script to promote a user to admin.
Run on EC2: python3 scripts/make_admin.py spectro-test@test.com
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, User

def make_admin(email: str):
    """Promote a user to admin by email."""
    db = next(get_db())

    user = db.query(User).filter(User.email == email).first()

    if not user:
        print(f"Utilisateur non trouve: {email}")
        print("\nUtilisateurs existants:")
        for u in db.query(User).all():
            admin_status = " (ADMIN)" if u.is_admin else ""
            print(f"  - {u.email}{admin_status}")
        return False

    if user.is_admin:
        print(f"{email} est deja administrateur")
        return True

    user.is_admin = True
    db.commit()
    print(f"Succes! {email} est maintenant administrateur")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/make_admin.py <email>")
        print("Example: python3 scripts/make_admin.py spectro-test@test.com")
        sys.exit(1)

    email = sys.argv[1]
    success = make_admin(email)
    sys.exit(0 if success else 1)
