#!/usr/bin/env python3
"""
Backoffice web app (server-side rendered with Jinja2).

Run it with:
    uvicorn app.main:app --reload
"""
import os
import secrets
from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.auth import (authenticate, get_current_user, get_db, require_admin,
                      require_staff)
from app.models import ROLE_ADMIN, Branch, Stock, User
from app.product_api import ProductAPIError, get_product
from app.stock_service import StockError, add_stock, remove_stock
from app.user_service import (UserError, change_branch, change_password,
                              create_staff, delete_staff, get_staff)

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
LOW_STOCK = 10
try:
    LOCAL_TZ = ZoneInfo(os.getenv("TIMEZONE", "Europe/Paris"))
except ZoneInfoNotFoundError:
    LOCAL_TZ = timezone.utc

app = FastAPI(title="HBntory Backoffice")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY,
                   same_site="lax", max_age=8 * 3600)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def render(request, name, context, status_code=200):
    """
    Render a template with the request and the low-stock threshold.
    """
    context.setdefault("low", LOW_STOCK)
    return templates.TemplateResponse(request, name, context,
                                      status_code=status_code)


def done(path, what):
    """
    Redirect after a successful action, with a message key for the page.
    """
    return RedirectResponse(f"{path}?done={what}", status_code=303)


# ---------- Login ----------

@app.get("/")
def home(user=Depends(get_current_user)):
    """
    The home page is the dashboard (login first if needed).
    """
    return RedirectResponse("/dashboard", status_code=303)


@app.get("/login")
def login_form(request: Request):
    """
    Show the login form.
    """
    return render(request, "login.html", {"error": None})


@app.post("/login")
def login(request: Request, username: str = Form(...),
          password: str = Form(...), session=Depends(get_db)):
    """
    Check the credentials; on success, remember the user in the session.
    """
    user = authenticate(session, username, password)
    if user is None:
        return render(request, "login.html",
                      {"error": "Identifiant ou mot de passe incorrect."},
                      status_code=401)
    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)


@app.post("/logout")
def logout(request: Request):
    """
    Forget the user and go back to the login page.
    """
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ---------- Shared helpers ----------

def product_name(product_id):
    """
    Read the product name from the Product API (never stored locally).
    """
    try:
        product = get_product(product_id)
    except ProductAPIError:
        return "(API Produits indisponible)"
    if product is None:
        return "(produit inconnu)"
    return product.get("name") or product.get("title") or "-"


def local_time(value):
    """
    Show a date saved in UTC as local time, e.g. "21/11/2026 01:22".
    """
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(LOCAL_TZ).strftime("%d/%m/%Y %H:%M")


def branch_rows(session, branch_id):
    """
    Stock lines of a branch, with product names from the Product API,
    the date the product arrived in stock and its last movement.
    """
    lines = session.query(Stock).filter_by(
        branch_id=branch_id).order_by(Stock.product_id).all()
    return [{"product_id": line.product_id, "quantity": line.quantity,
             "name": product_name(line.product_id),
             "arrived": local_time(line.created_at),
             "updated": local_time(line.updated_at)} for line in lines]


def branch_summary(session):
    """
    One line per branch: active staff, products and units (read only).
    """
    summary = []
    for branch in session.query(Branch).order_by(Branch.name).all():
        staff = [u for u in branch.users if u.is_active]
        summary.append({"name": branch.name, "staff": len(staff),
                        "products": len(branch.stock),
                        "units": sum(s.quantity for s in branch.stock)})
    return summary


# ---------- Dashboard ----------

@app.get("/dashboard")
def dashboard(request: Request, user=Depends(get_current_user),
              session=Depends(get_db)):
    """
    Home page after login: key figures for the admin or for the branch.
    """
    if user.role == ROLE_ADMIN:
        users = session.query(User).all()
        return render(request, "dashboard_admin.html",
                      {"user": user, "users": users,
                       "branches": branch_summary(session)})
    rows = branch_rows(session, user.branch_id)
    alerts = [row for row in rows if row["quantity"] < LOW_STOCK]
    return render(request, "dashboard_staff.html",
                  {"user": user, "rows": rows, "alerts": alerts})


# ---------- Stock (common users only) ----------

@app.get("/stock")
def stock(request: Request, user=Depends(require_staff),
          session=Depends(get_db)):
    """
    The stock of the user's own branch.
    """
    return render(request, "stock.html",
                  {"user": user, "rows": branch_rows(session, user.branch_id)})


def stock_form(request, user, session, mode, error=None, values=None,
               status_code=200):
    """
    Render the add or remove page of the user's branch.
    """
    return render(request, "stock_form.html",
                  {"user": user, "mode": mode, "error": error,
                   "values": values or {},
                   "rows": branch_rows(session, user.branch_id)},
                  status_code=status_code)


@app.get("/stock/add")
def stock_add_form(request: Request, user=Depends(require_staff),
                   session=Depends(get_db)):
    """
    Page to add stock.
    """
    return stock_form(request, user, session, "add")


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
        return stock_form(request, user, session, "add", str(error),
                          {"product_id": product_id, "quantity": quantity},
                          400)
    return done("/stock", "added")


@app.get("/stock/remove")
def stock_remove_form(request: Request, user=Depends(require_staff),
                      session=Depends(get_db)):
    """
    Page to remove stock.
    """
    return stock_form(request, user, session, "remove")


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
        return stock_form(request, user, session, "remove", str(error),
                          {"product_id": product_id, "quantity": quantity},
                          400)
    return done("/stock", "removed")


# ---------- Users and branches (admin only) ----------

def branches_of(session):
    """
    Every branch, sorted by name, for the select menus.
    """
    return session.query(Branch).order_by(Branch.name).all()


@app.get("/admin/users")
def admin_users(request: Request, admin=Depends(require_admin),
                session=Depends(get_db)):
    """
    List every user with their role, branch and status, grouped by
    branch: the admin first, then Bordeaux, Lille, Lyon... (by name).
    """
    users = sorted(session.query(User).all(),
                   key=lambda u: (u.role != ROLE_ADMIN,
                                  u.branch.name if u.branch else "",
                                  not u.is_active, u.username))
    return render(request, "users.html", {"user": admin, "users": users})


@app.get("/admin/users/new")
def admin_new_user_form(request: Request, admin=Depends(require_admin),
                        session=Depends(get_db)):
    """
    Page to create a common user.
    """
    return render(request, "user_new.html",
                  {"user": admin, "branches": branches_of(session),
                   "values": {}})


@app.post("/admin/users")
def admin_create_user(request: Request, username: str = Form(...),
                      password: str = Form(...), branch_id: int = Form(...),
                      admin=Depends(require_admin), session=Depends(get_db)):
    """
    Create a common user assigned to one branch.
    """
    try:
        create_staff(session, username, password, branch_id)
    except UserError as error:
        session.rollback()
        return render(request, "user_new.html",
                      {"user": admin, "branches": branches_of(session),
                       "error": str(error),
                       "values": {"username": username,
                                  "branch_id": branch_id}},
                      status_code=400)
    return done("/admin/users", "created")


def edit_page(request, admin, session, user_id, error=None, status_code=200):
    """
    Render the edit page of an active common user, or a 404 page.
    """
    try:
        staff = get_staff(session, user_id)
    except UserError:
        raise HTTPException(status_code=404)
    return render(request, "user_edit.html",
                  {"user": admin, "staff": staff,
                   "branches": branches_of(session), "error": error},
                  status_code=status_code)


@app.get("/admin/users/{user_id}")
def admin_edit_user(request: Request, user_id: int,
                    admin=Depends(require_admin), session=Depends(get_db)):
    """
    Page to modify or delete one common user.
    """
    return edit_page(request, admin, session, user_id)


def run_user_action(request, admin, session, user_id, what, action, *args):
    """
    Run a user_service action; show its error on the edit page.
    """
    try:
        action(session, user_id, *args)
    except UserError as error:
        session.rollback()
        return edit_page(request, admin, session, user_id, str(error), 400)
    return done("/admin/users", what)


@app.post("/admin/users/{user_id}/password")
def admin_change_password(request: Request, user_id: int,
                          password: str = Form(...),
                          admin=Depends(require_admin),
                          session=Depends(get_db)):
    """
    Give a common user a new password.
    """
    return run_user_action(request, admin, session, user_id, "saved",
                           change_password, password)


@app.post("/admin/users/{user_id}/branch")
def admin_change_branch(request: Request, user_id: int,
                        branch_id: int = Form(...),
                        admin=Depends(require_admin),
                        session=Depends(get_db)):
    """
    Move a common user to another branch.
    """
    return run_user_action(request, admin, session, user_id, "saved",
                           change_branch, branch_id)


@app.post("/admin/users/{user_id}/delete")
def admin_delete_user(request: Request, user_id: int,
                      admin=Depends(require_admin), session=Depends(get_db)):
    """
    Soft-delete a common user.
    """
    return run_user_action(request, admin, session, user_id, "deleted",
                           delete_staff)


@app.get("/admin/branches")
def admin_branches(request: Request, admin=Depends(require_admin),
                   session=Depends(get_db)):
    """
    Read-only overview of every branch.
    """
    return render(request, "branches.html",
                  {"user": admin, "branches": branch_summary(session)})


@app.get("/admin/api/summary")
def admin_summary(admin=Depends(require_admin), session=Depends(get_db)):
    """
    Live figures for the admin dashboard, as JSON. The page asks for
    them every few seconds, so the numbers and the 3D view follow the
    stock changes made by staff without reloading the page.
    """
    branches = branch_summary(session)
    return {"branches": branches,
            "units": sum(branch["units"] for branch in branches)}


# ---------- Error pages ----------

@app.exception_handler(403)
@app.exception_handler(404)
def error_page(request: Request, exc):
    """
    Show a clean error page instead of raw JSON.
    """
    if exc.status_code == 403:
        message = exc.detail
    else:
        message = "Cette page n'existe pas."
    return render(request, "error.html",
                  {"code": exc.status_code, "message": message},
                  status_code=exc.status_code)
