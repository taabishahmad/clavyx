"""Promote a user to admin. Usage:  python make_admin.py you@email.com"""
import sys
from app.database import SessionLocal, init_db
from app.models import User

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python make_admin.py you@email.com"); raise SystemExit(1)
    init_db()
    db = SessionLocal()
    u = db.query(User).filter(User.email == sys.argv[1].lower()).first()
    if not u:
        print("No user with that email. Sign up in the app first."); raise SystemExit(1)
    u.role = "admin"; db.commit()
    print(f"{u.email} is now an admin.")
