# AARAM

An e-commerce website for AARAM, a Nepali mattress brand that sells its own
mattresses directly to customers across Nepal. Built with Django 5.2 and
PostgreSQL as a Kathmandu University Year III / Semester II project.

The full plan is in [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md); design rules are in
[docs/DESIGN.md](docs/DESIGN.md). Work happens one phase at a time; each phase is
explained in `docs/phase-N.md`.

## Local setup (macOS)

These steps assume [Homebrew](https://brew.sh).

1. Install Python 3.12 and PostgreSQL 16:

   ```bash
   brew install python@3.12 postgresql@16
   brew services start postgresql@16
   ```

2. Create and activate a virtual environment, then install the dependencies:

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Create your local environment file and fill in the values:

   ```bash
   cp .env.example .env
   ```

   Set:

   - `SECRET_KEY` - any long random string. Generate one with:

     ```bash
     python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
     ```

   - `DEBUG` - `True` for local development.
   - `DATABASE_URL` - `postgres://<your-mac-username>@localhost:5432/aaram`.
   - `ALLOWED_HOSTS` - `localhost,127.0.0.1`.

4. Create the database, apply migrations and run the server:

   ```bash
   createdb aaram
   python manage.py migrate
   python manage.py runserver
   ```

   Open http://127.0.0.1:8000/ to see the home page.

## Running the tests

```bash
python manage.py test
```

The tests must pass before any phase is called done.

## Settings

Settings are split under `config/settings/`:

- `base.py` - shared settings; reads secrets from `.env`.
- `dev.py` - local development (used by `manage.py`); emails print to the console.
- `prod.py` - production; serves static files with WhiteNoise.

`manage.py` uses `dev` by default. In production, `config/wsgi.py` uses `prod`.
