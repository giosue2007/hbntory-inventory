#!/usr/bin/env python3
"""
Backoffice web app (server-side rendered with Jinja2).

Run it with:
    uvicorn app.main:app --reload
"""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.auth import (authenticate, get_current_user, get_db, require_admin,
                      require_staff)
from app.models import ROLE_ADMIN, Branch, Stock, User
from app.product_api import ProductAPIError, get_product
from app.stock_service import StockError, add_stock, remove_stock
from app.user_service import (UserError, change_branch, change_password,
                              create_staff, delete_staff)

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)

app = FastAPI(title="HBntory Backoffice")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY,
                   same_site="lax", max_age=8 * 3600)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@app.get("/")
def home(user=Depends(get_current_user)):
    """
    Send each user to the page of their role.
    """
    target = "/admin/users" if user.role == ROLE_ADMIN else "/stock"
    return RedirectResponse(target, status_code=303)


@app.get("/login")
def login_form(request: Request):
    """
    Show the login form.
    """
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
def login(request: Request, username: str = Form(...),
          password: str = Form(...), session=Depends(get_db)):
    """
    Check the credentials; on success, remember the user in the session.
    """
    user = authenticate(session, username, password)
    if user is None:
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "Invalid username or password."}, status_code=401)
    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    """
    Forget the user and go back to the login page.
    """
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


def users_page(request, admin, session, error=None, status_code=200):
    """
    Render the admin page: every user, and the forms to manage them.
    """
    users = session.query(User).order_by(User.id).all()
    branches = session.query(Branch).order_by(Branch.name).all()
    return templates.TemplateResponse(
        request, "users.html",
        {"user": admin, "users": users, "branches": branches,
         "error": error},
        status_code=status_code)


def run_user_action(request, admin, session, action, *args):
    """
    Run a user_service action; show its error on the page if it fails.
    """
    try:
        action(session, *args)
    except UserError as error:
        session.rollback()
        return users_page(request, admin, session, str(error), 400)
    return RedirectResponse("/admin/users?done=saved", status_code=303)


@app.get("/admin/users")
def admin_users(request: Request, admin=Depends(require_admin),
                session=Depends(get_db)):
    """
    Admin page: list every user with their role, branch and status.
    """
    return users_page(request, admin, session)


@app.post("/admin/users")
def admin_create_user(request: Request, username: str = Form(...),
                      password: str = Form(...), branch_id: int = Form(...),
                      admin=Depends(require_admin), session=Depends(get_db)):
    """
    Create a common user assigned to one branch.
    """
    return run_user_action(request, admin, session, create_staff,
                           username, password, branch_id)


@app.post("/admin/users/{user_id}/password")
def admin_change_password(request: Request, user_id: int,
                          password: str = Form(...),
                          admin=Depends(require_admin),
                          session=Depends(get_db)):
    """
    Give a common user a new password.
    """
    return run_user_action(request, admin, session, change_password,
                           user_id, password)


@app.post("/admin/users/{user_id}/branch")
def admin_change_branch(request: Request, user_id: int,
                        branch_id: int = Form(...),
                        admin=Depends(require_admin),
                        session=Depends(get_db)):
    """
    Move a common user to another branch.
    """
    return run_user_action(request, admin, session, change_branch,
                           user_id, branch_id)


@app.post("/admin/users/{user_id}/delete")
def admin_delete_user(request: Request, user_id: int,
                      admin=Depends(require_admin), session=Depends(get_db)):
    """
    Soft-delete a common user.
    """
    return run_user_action(request, admin, session, delete_staff, user_id)


def product_name(product_id):
    """
    Read the product name from the Product API (never stored locally).
    """
    try:
        product = get_product(product_id)
    except ProductAPIError:
        return "(Product API unavailable)"
    if product is None:
        return "(unknown product)"
    return product.get("name") or product.get("title") or "-"


def stock_page(request, user, session, error=None, status_code=200):
    """
    Render the stock of the user's own branch, with product names
    read live from the Product API.
    """
    lines = session.query(Stock).filter_by(
        branch_id=user.branch_id).order_by(Stock.product_id).all()
    rows = [{"product_id": line.product_id, "quantity": line.quantity,
             "name": product_name(line.product_id)} for line in lines]
    return templates.TemplateResponse(
        request, "stock.html",
        {"user": user, "rows": rows, "error": error},
        status_code=status_code)


@app.get("/stock")
def stock(request: Request, user=Depends(require_staff),
          session=Depends(get_db)):
    """
    Staff page: the stock of their branch.
    """
    return stock_page(request, user, session)


@app.post("/stock/add")
def stock_add(request: Request, product_id: str = Form(...),
              quantity: int = Form(...), user=Depends(require_staff),
              session=Depends(get_db)):
    """
    Add stock to the user's own branch (never one chosen by the browser).
    """
    try:
        add_stock(session, user.branch_id, product_id, quantity)
    except (StockError, ProductAPIError) as error:
        session.rollback()
        return stock_page(request, user, session, str(error), 400)
    return RedirectResponse("/stock?done=added", status_code=303)


@app.post("/stock/remove")
def stock_remove(request: Request, product_id: str = Form(...),
                 quantity: int = Form(...), user=Depends(require_staff),
                 session=Depends(get_db)):
    """
    Remove stock from the user's own branch.
    """
    try:
        remove_stock(session, user.branch_id, product_id, quantity)
    except StockError as error:
        session.rollback()
        return stock_page(request, user, session, str(error), 400)
    return RedirectResponse("/stock?done=removed", status_code=303)


@app.exception_handler(403)
@app.exception_handler(404)
def error_page(request: Request, exc):
    """
    Show a clean error page instead of raw JSON.
    """
    if exc.status_code == 403:
        message = exc.detail
    else:
        message = "This page does not exist."
    return templates.TemplateResponse(
        request, "error.html",
        {"code": exc.status_code, "message": message},
        status_code=exc.status_code)
