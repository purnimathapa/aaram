# Phase 0: Setup

## What this phase built

The project skeleton: a Django 5.2 project that a fresh clone can install,
migrate and run, with the custom email-login user model in place before the
first migration, the eight apps registered, the base page shell (header,
footer, messages) matching the Main mockup, the design tokens, a home page with
the hero, and one passing test. No business features yet.

## New files and what they do

### Project configuration
- `requirements.txt` - pinned dependencies (Django 5.2, psycopg 3, django-environ, Pillow, requests, whitenoise, gunicorn).
- `.gitignore` - keeps `.venv`, `.env`, `media/`, `staticfiles/` and caches out of Git.
- `.env.example` - the environment variables to set locally, with empty values.
- `manage.py` - Django's command-line entry point; uses the `dev` settings by default.
- `config/settings/base.py` - shared settings. Reads `SECRET_KEY`, `DEBUG`, `DATABASE_URL` and `ALLOWED_HOSTS` from `.env`; registers the eight apps; sets `AUTH_USER_MODEL = "accounts.User"`, `TIME_ZONE = "Asia/Kathmandu"` and `USE_TZ = True`.
- `config/settings/dev.py` - development settings; prints emails to the console.
- `config/settings/prod.py` - production settings; adds the WhiteNoise middleware and compressed static storage.
- `config/urls.py` - routes `/admin/` and includes `core.urls` at `/`.
- `config/wsgi.py` - WSGI entry point for gunicorn; uses the `prod` settings.

### Apps
- `accounts/` - the custom user model.
  - `models.py` - `User(AbstractUser)` with `username` removed, a unique `email` as the login field (`USERNAME_FIELD`), a `phone` field, and a `UserManager` that creates users by email.
  - `admin.py` - registers `User` with the admin, rebuilt around email and phone.
  - `migrations/0001_initial.py` - creates the user table; generated before the first `migrate`.
- `catalog/`, `cart/`, `orders/`, `payments/`, `reviews/`, `dashboard/` - registered apps whose `models.py` names the models each will hold in a later phase.
- `core/` - public store pages.
  - `views.py` - the `home` view.
  - `urls.py` - the home URL, named `core:home`.
  - `tests.py` - the home-page test.
  - `templates/core/home.html` - the home page: the hero (headline, lead, two buttons) and the mattress layer illustration.

### Templates (shared)
- `templates/base.html` - the page shell: fonts, both stylesheets, a skip link, the header, the messages partial, a `content` block, and the footer.
- `templates/partials/header.html` - the top COD bar, the AARAM / आराम wordmark, the nav, the search box and the account and cart icons, matching the Main mockup.
- `templates/partials/footer.html` - the dark footer with the Shop, Help and Contact columns and the sample-project note.
- `templates/partials/messages.html` - renders Django messages with the status colours.

### Styles
- `static/css/tokens.css` - every token from `docs/DESIGN.md` as CSS custom properties (colours, spacing scale, radii, fonts, content width).
- `static/css/main.css` - the stylesheet in commented sections: base, layout, buttons, header, hero, messages, footer, responsive. Plain class names, no framework, no inline styles, no `!important`.

### Docs
- `README.md` - macOS setup with Homebrew, the virtual environment, `.env`, the database, and how to run the server and the tests.
- `docs/phase-0.md` - this file.

## How to test it manually

1. Follow the setup steps in `README.md` (venv, `pip install`, `.env`, `createdb aaram`).
2. `python manage.py migrate` - applies all migrations, including `accounts.0001_initial`.
3. `python manage.py test` - the one test passes.
4. `python manage.py runserver`, then open http://127.0.0.1:8000/ - the home page shows the header, the hero with the layer illustration, and the footer. Check that it still reads well when the window is narrowed to about 360 px.
5. `python manage.py createsuperuser` (email and password), then open http://127.0.0.1:8000/admin/ and confirm you log in with the email and that Users appears.

## Likely defense questions

1. **Why a custom user model, and why create it in this phase?**
   AARAM logs people in by email, not a username. Django strongly recommends
   setting a custom `AUTH_USER_MODEL` before the first migration, because
   changing it afterwards means rebuilding the migration history. So we defined
   `accounts.User` now, with email as `USERNAME_FIELD`, before running `migrate`
   even once.

2. **How does login by email work in the model?**
   We subclass `AbstractUser`, set `username = None`, make `email` unique, set
   `USERNAME_FIELD = "email"` and `REQUIRED_FIELDS = []`, and provide a
   `UserManager` whose `create_user` and `create_superuser` take an email
   instead of a username. Passwords are still hashed by Django's `set_password`.

3. **Why split settings into base, dev and prod, and where do secrets come from?**
   Shared settings live in `base.py`; `dev.py` and `prod.py` only hold what
   differs (console email in dev, WhiteNoise in prod). Secrets and
   machine-specific values (`SECRET_KEY`, `DEBUG`, `DATABASE_URL`,
   `ALLOWED_HOSTS`) are read from `.env` with django-environ, so nothing
   sensitive is committed. `.env` is git-ignored; `.env.example` documents the keys.

4. **Why is `TIME_ZONE` Asia/Kathmandu with `USE_TZ = True`?**
   The store and its customers are in Nepal, so times display in Nepal time,
   while `USE_TZ = True` stores timestamps in UTC in the database. That keeps
   order times correct and unambiguous.

5. **Why does the home page use a base template and partials instead of one file?**
   Every page shares the same header, footer and message area. Putting them in
   `base.html` and `templates/partials/` means we write them once and each page
   only fills the `content` block, which is what the design guide asks for and
   keeps the pages consistent.
```
