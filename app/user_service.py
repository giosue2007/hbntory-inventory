#!/usr/bin/env python3
"""
User management by the admin: create, modify and soft-delete
common (staff) users. Every rule is checked here, on the server.
"""
from app.models import ROLE_STAFF, Branch, User
from app.security import hash_password

MIN_PASSWORD_LENGTH = 8


class UserError(ValueError):
    """
    Raised when a user operation breaks a rule.
    """


def check_password(password):
    """
    A password must have at least MIN_PASSWORD_LENGTH characters.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise UserError(f"Password must have at least "
                        f"{MIN_PASSWORD_LENGTH} characters.")


def get_branch(session, branch_id):
    """
    Return the branch or raise UserError if it does not exist.
    """
    branch = session.get(Branch, branch_id)
    if branch is None:
        raise UserError(f"Branch {branch_id} does not exist.")
    return branch


def get_staff(session, user_id):
    """
    Return an active common user, or raise UserError.
    The admin account can never be modified or deleted here.
    """
    user = session.get(User, user_id)
    if user is None or user.role != ROLE_STAFF:
        raise UserError("Only common users can be managed.")
    if not user.is_active:
        raise UserError(f"User {user.username} is deleted.")
    return user


def create_staff(session, username, password, branch_id):
    """
    Create a common user assigned to exactly one branch.
    """
    username = username.strip()
    if not username:
        raise UserError("Username is required.")
    if session.query(User).filter_by(username=username).first():
        raise UserError(f"Username {username} is already taken.")
    check_password(password)
    branch = get_branch(session, branch_id)
    user = User(username=username, role=ROLE_STAFF, branch=branch,
                password_hash=hash_password(password))
    session.add(user)
    session.commit()
    return user


def change_password(session, user_id, password):
    """
    Give a common user a new password (stored hashed).
    """
    user = get_staff(session, user_id)
    check_password(password)
    user.password_hash = hash_password(password)
    session.commit()
    return user


def change_branch(session, user_id, branch_id):
    """
    Move a common user to another branch.
    """
    user = get_staff(session, user_id)
    user.branch = get_branch(session, branch_id)
    session.commit()
    return user


def delete_staff(session, user_id):
    """
    Soft-delete a common user: the row stays, the login is refused.
    """
    user = get_staff(session, user_id)
    user.soft_delete()
    session.commit()
    return user
