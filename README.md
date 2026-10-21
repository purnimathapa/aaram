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

## Deployment

The app is deployed as a standard Django + PostgreSQL service. It is
host-agnostic: it reads everything from environment variables and ships a
`Procfile` (`release` runs migrations and `collectstatic`; `web` runs gunicorn).
We host on **Railway** (managed PostgreSQL, no cold starts, outbound calls to
Khalti and SMTP email both work, and a scheduled job for unpaid-order expiry);
**Render** is an alternative (its free tier sleeps, expires the database after 30
days and blocks SMTP, so use a paid instance for a real deployment).

### Steps

1. Push the repository to GitHub and create a web service from it on the host.
2. Add a managed PostgreSQL database; the host provides `DATABASE_URL`.
3. Set the environment variables (see `.env.example`). The important ones:
   - `SECRET_KEY` - a long random value (not the dev one).
   - `DEBUG=False`, `ALLOWED_HOSTS=<your-domain>`,
     `CSRF_TRUSTED_ORIGINS=https://<your-domain>`.
   - `DJANGO_SETTINGS_MODULE=config.settings.prod` (so the production settings,
     with HTTPS hardening, are used).
   - Email SMTP (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`,
     `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`).
   - `KHALTI_SECRET_KEY` (sandbox key) and `KHALTI_BASE_URL`.
4. The `release` command migrates and collects static files automatically on
   each deploy; WhiteNoise serves the static files.
5. Create a superuser once (`python manage.py createsuperuser` in the host
   shell) and load sample data if wanted (`python manage.py loaddata fixtures/*.json`).
6. Schedule `python manage.py expire_unpaid_orders` (for example every 10
   minutes) so abandoned Khalti orders release their stock.

### Media (uploaded product images)

Set the `AWS_*` variables to an S3-compatible bucket and media is stored there
instead of the local disk. We use **Cloudflare R2** (free tier, no egress fees):
set `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ACCESS_KEY_ID`, `AWS_S3_SECRET_ACCESS_KEY`,
`AWS_S3_ENDPOINT_URL` (the R2 endpoint) and `AWS_S3_CUSTOM_DOMAIN` (the public
media host). If these are left empty, media falls back to the local disk.

### Checking the production settings

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py check --deploy
```

This should report no issues with a real `SECRET_KEY` set.
