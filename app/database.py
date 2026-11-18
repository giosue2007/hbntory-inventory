#!/usr/bin/env python3
"""
Database connection: engine, session factory and declarative base.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///hbntory.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """
    SQLite ignores foreign keys unless this pragma is set.
    """
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Base(DeclarativeBase):
    """
    Base class of every model.
    """
