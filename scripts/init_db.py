#!/usr/bin/env python3
"""
Create the tables and insert the initial data:
one admin, two branches, one staff user per branch and sample stock.

The admin password comes from the ADMIN_PASSWORD environment variable
(or .env). If it is missing, a random one is generated and printed once.
Running the script again does not duplicate data: it only adds what is
missing (for example new sample stock lines) and never changes existing
quantities or passwords.

Usage:
    python3 scripts/init_db.py
"""
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import (ROLE_ADMIN, ROLE_STAFF, Branch, Stock,  # noqa: E402
                        User)
from app.security import hash_password  # noqa: E402

BRANCHES = ["Paris", "Lyon", "Marseille", "Toulouse", "Bordeaux", "Lille"]
STAFF = {"paris_staff": "Paris", "lyon_staff": "Lyon",
         "marseille_staff": "Marseille", "toulouse_staff": "Toulouse",
         "bordeaux_staff": "Bordeaux", "lille_staff": "Lille"}
# product_id from the external Product API -> quantity per branch
# (ids 1 to 16 are served by scripts/mock_product_api.py). Some lines are
# at 0 or under 10 on purpose, to show "Rupture" and "Stock bas".
SAMPLE_STOCK = {
    "Paris": {"1": 25, "2": 10, "3": 0, "4": 18, "5": 4, "6": 32, "7": 7,
              "8": 15, "10": 0, "12": 22, "13": 40, "16": 3},
    "Lyon": {"1": 5, "2": 40, "4": 12, "6": 14, "8": 0, "9": 27, "11": 6,
             "14": 9, "15": 11, "16": 20},
    "Marseille": {"1": 12, "3": 8, "6": 21, "7": 0, "9": 35, "10": 6,
                  "13": 18, "14": 4},
    "Toulouse": {"2": 22, "4": 9, "5": 14, "6": 0, "8": 11, "12": 30,
                 "15": 7, "16": 16},
    "Bordeaux": {"1": 3, "2": 17, "6": 26, "8": 5, "9": 0, "11": 13,
                 "13": 24, "16": 9},
    "Lille": {"3": 15, "4": 20, "6": 8, "7": 12, "10": 0, "12": 6,
              "14": 11, "15": 19},
}


def get_password(variable):
    """
    Read a password from the environment, or generate and print one.
    """
    password = os.getenv(variable)
    if not password:
        password = secrets.token_urlsafe(12)
        print(f"{variable} not set, generated password: {password}")
    return password


def main():
    """
    Create the schema and insert the initial data once.
    """
    Base.metadata.create_all(engine)
    session = SessionLocal()

    branches = {}
    for name in BRANCHES:
        branch = session.query(Branch).filter_by(name=name).first()
        if branch is None:
            branch = Branch(name=name)
            session.add(branch)
        branches[name] = branch
    session.flush()

    # Only create the admin if there is none yet (it may have been renamed).
    if not session.query(User).filter_by(role=ROLE_ADMIN).first():
        session.add(User(username="admin", role=ROLE_ADMIN,
                         password_hash=hash_password(
                             get_password("ADMIN_PASSWORD"))))

    staff_password = None
    for username, branch_name in STAFF.items():
        if not session.query(User).filter_by(username=username).first():
            staff_password = staff_password or get_password(
                "STAFF_PASSWORD")
            session.add(User(username=username, role=ROLE_STAFF,
                             branch=branches[branch_name],
                             password_hash=hash_password(staff_password)))

    for branch_name, products in SAMPLE_STOCK.items():
        branch = branches[branch_name]
        for product_id, quantity in products.items():
            exists = session.query(Stock).filter_by(
                branch_id=branch.id, product_id=product_id).first()
            if not exists:
                session.add(Stock(branch=branch, product_id=product_id,
                                  quantity=quantity))

    session.commit()
    print(f"Branches: {session.query(Branch).count()}, "
          f"users: {session.query(User).count()}, "
          f"stock lines: {session.query(Stock).count()}")
    session.close()


if __name__ == "__main__":
    main()
