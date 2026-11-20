#!/usr/bin/env python3
"""
Authentication (who are you?) and authorization (what may you do?)
for the Backoffice. Every rule is checked here, on the server.
"""
from fastapi import Depends, HTTPException, Request, status

from app.database import SessionLocal
from app.models import ROLE_ADMIN, ROLE_STAFF, User
from app.security import verify_password


def get_db():
    """
    Open one database session per request and close it afterwards.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def authenticate(session, username, password):
    """
    Return the user if the credentials are valid, otherwise None.
    Unknown users, wrong passwords and soft-deleted users are refused.
    """
    user = session.query(User).filter_by(username=username).first()
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(request: Request, session=Depends(get_db)):
    """
    Return the logged-in user, or send the browser to /login.
    A user deleted after logging in is logged out at once.
    """
    user_id = request.session.get("user_id")
    user = session.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER,
                            headers={"Location": "/login"})
    return user


def require_admin(user=Depends(get_current_user)):
    """
    Only the admin may continue.
    """
    if user.role != ROLE_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Admin only.")
    return user


def require_staff(user=Depends(get_current_user)):
    """
    Only common (staff) users may continue: the admin cannot touch stock.
    """
    if user.role != ROLE_STAFF:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Staff only: admin cannot manage stock.")
    return user
