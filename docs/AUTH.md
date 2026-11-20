# HBntory - Authentication and Authorization (Backoffice)

## Login flow

1. `GET /login` shows the form.
2. `POST /login` calls `authenticate()` (`app/auth.py`):
   - unknown username -> refused;
   - soft-deleted user (`deleted_at` set) -> refused;
   - wrong password (`verify_password` fails) -> refused.
   The same message is shown in every case ("Invalid username or
   password.") so an attacker cannot tell which usernames exist.
3. On success, only the user's id is stored in a signed session cookie
   (`SessionMiddleware`, key from `SECRET_KEY`). The password is never
   stored in the cookie.
4. On every request, `get_current_user()` reloads the user from the
   database. If the user was soft-deleted in the meantime, the session
   is cleared and the browser goes back to `/login`.
5. `POST /logout` clears the session.

## Authorization rules (enforced in the backend)

| Rule | How |
|------|-----|
| Only logged-in users reach the Backoffice | every page depends on `get_current_user` |
| Common users cannot use admin pages | `/admin/*` depends on `require_admin` -> 403 for staff |
| The admin cannot perform stock operations | `/stock*` depends on `require_staff` -> 403 for the admin; the database also refuses (admin has no branch) |
| Staff only touch their own branch | the branch is always `user.branch_id`, never a value sent by the browser |

Hiding a button in the page is not enough: anyone can send a request
with `curl`. That is why every rule is checked on the server.

## Password storage

Passwords are hashed with PBKDF2-SHA256, a random salt per user and
600,000 iterations (`app/security.py`). Only
`pbkdf2_sha256$iterations$salt$hash` is stored.

- **Plain text is not acceptable:** if the database leaks, every
  password can be read at once.
- **Plain SHA256 is not acceptable:** it is designed to be fast, so an
  attacker can test billions of guesses per second, and without a salt
  two users with the same password get the same hash, which makes
  precomputed (rainbow) tables work.
- **PBKDF2 with salt and many iterations** makes every guess slow and
  every hash unique.

## Run it

    pip install -r requirements.txt
    python3 scripts/init_db.py
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/login.
