# HBntory - Backoffice features

Server-side rendered pages (FastAPI + Jinja2). Every rule is checked
in the backend (`app/auth.py`, `app/stock_service.py`,
`app/user_service.py`), not only in the HTML.

## Common users (staff)

| Feature | Route | Rule |
|---------|-------|------|
| Consult stock | `GET /stock` | only the stock of their own branch |
| Add stock | `POST /stock/add` | positive integer, product must exist in the Product API |
| Remove stock | `POST /stock/remove` | positive integer, stock never negative |

The branch is always `user.branch_id`. A `branch_id` sent by the browser
is ignored, so a common user cannot operate on another branch.

## Admin

| Feature | Route | Rule |
|---------|-------|------|
| List users | `GET /admin/users` | role, branch, active or deleted |
| Create a common user | `POST /admin/users` | unique username, password of 8+ characters (stored hashed), existing branch |
| Change a password | `POST /admin/users/{id}/password` | 8+ characters, stored hashed |
| Change a branch | `POST /admin/users/{id}/branch` | branch must exist |
| Soft-delete a user | `POST /admin/users/{id}/delete` | sets `deleted_at`; the row stays, login is refused |

Only active common users can be modified or deleted: the admin account
is protected. The admin cannot reach `/stock` (403).

## Product API integration

Product details are never stored. When the stock page needs a product
name, `get_product()` (`app/product_api.py`) calls
`GET {PRODUCT_API_URL}/products/{id}` live. If the API is down, the page
still works and shows "(Product API unavailable)".
