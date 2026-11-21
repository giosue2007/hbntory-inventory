# HBntory - Backoffice features

Server-side rendered pages (FastAPI + Jinja2), in French. Every rule is
checked in the backend (`app/auth.py`, `app/stock_service.py`,
`app/user_service.py`), not only in the HTML.

## Navigation

Opening the site without a session leads to the login page. After login,
every user lands on a dashboard. The sidebar shows only the sections of
the user's role.

| Role | Menu |
|------|------|
| Admin | Tableau de bord, Utilisateurs, Magasins |
| Common user (staff) | Tableau de bord, Stock, Ajouter du stock, Retirer du stock |

## Common users (staff)

| Page | Route | Rule |
|------|-------|------|
| Dashboard | `GET /dashboard` | key figures and the products in low stock or out of stock |
| Consult stock | `GET /stock` | only the stock of their own branch |
| Add stock | `GET`/`POST /stock/add` | positive integer, product must exist in the Product API |
| Remove stock | `GET`/`POST /stock/remove` | positive integer, stock never negative |

The branch is always `user.branch_id`. A `branch_id` sent by the browser
is ignored, so a common user cannot operate on another branch.

## Admin

| Page | Route | Rule |
|------|-------|------|
| Dashboard | `GET /dashboard` | users, active staff, branches, deleted accounts |
| List users | `GET /admin/users` | role, branch, active or deleted |
| Create a common user | `GET /admin/users/new`, `POST /admin/users` | unique username, password of 8+ characters (stored hashed), existing branch |
| Edit a common user | `GET /admin/users/{id}` | one page per user |
| Change a branch | `POST /admin/users/{id}/branch` | branch must exist |
| Change a password | `POST /admin/users/{id}/password` | 8+ characters, stored hashed |
| Soft-delete a user | `POST /admin/users/{id}/delete` | sets `deleted_at`; the row stays, login is refused |
| Branches | `GET /admin/branches` | read only: active staff, products and units per branch |

Only active common users can be edited or deleted: the admin account is
protected (404). The admin cannot reach the stock pages (403).

## Product API integration

Product details are never stored. When a page needs a product name,
`get_product()` (`app/product_api.py`) calls
`GET {PRODUCT_API_URL}/products/{id}` live. If the API is down, the
pages still work and show "(API Produits indisponible)".

For development and demos, `scripts/mock_product_api.py` stands in for
the real Product API: it serves a catalog of 16 electronics products on
`GET /products` and `GET /products/{id}` (404 for an unknown id).

    uvicorn scripts.mock_product_api:app --port 9000

`scripts/init_db.py` adds sample stock for these products in both
branches, with some lines at 0 or under 10 to show "Rupture" and
"Stock bas". Running it again only adds the missing lines.

## Interface

- Sidebar with icons, the user's name, role and branch, and a log out
  button. On a phone the sidebar becomes a top bar.
- One page per action, with a breadcrumb and a Cancel button.
- Key figures, status badges (En stock, Stock bas, Rupture; Actif,
  Supprimé) and clear empty states.
- A green message confirms every action ("Stock ajouté.", "Employé
  créé."); a red message explains every refusal and keeps the values
  typed in the form.
- Errors 403 and 404 show a clean page instead of raw JSON.
- Light theme only, so the pages look the same on every computer.
