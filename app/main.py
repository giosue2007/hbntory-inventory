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
from app.models import ROLE_ADMIN, Stock, User
from app.product_api import ProductAPIError
from app.stock_service import StockError, add_stock, remove_stock

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


@app.get("/admin/users")
def admin_users(request: Request, admin=Depends(require_admin),
                session=Depends(get_db)):
    """
    Admin page: list every user with their role, branch and status.
    """
    users = session.query(User).order_by(User.id).all()
    return templates.TemplateResponse(
        request, "users.html", {"user": admin, "users": users})


def stock_page(request, user, session, error=None, status_code=200):
    """
    Render the stock of the user's own branch.
    """
    lines = session.query(Stock).filter_by(
        branch_id=user.branch_id).order_by(Stock.product_id).all()
    return templates.TemplateResponse(
        request, "stock.html",
        {"user": user, "lines": lines, "error": error},
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
    return RedirectResponse("/stock", status_code=303)


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
    return RedirectResponse("/stock", status_code=303)
