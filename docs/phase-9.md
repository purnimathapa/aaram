# Phase 9: Deploy and defend

## What this phase prepared

Everything needed to put AARAM on a public URL and to present it at the defense.
The actual hosting account, domain and secret keys are set up by the team; this
phase made the project deploy-ready and host-agnostic and wrote the demo script.

## Hosting choice

For a Django + PostgreSQL app that also makes outbound calls to Khalti, sends
SMTP email and runs a scheduled job, we chose **Railway** (Hobby, about
US$5/month): managed PostgreSQL, no cold-start sleep during the defense, outbound
HTTPS and SMTP both allowed, and cron for the unpaid-order expiry. **Render** is
the documented alternative (its free tier sleeps, expires the database after 30
days and blocks SMTP, so a paid instance is needed for a real deployment).
Uploaded images go to **Cloudflare R2** (free tier, no egress fees), which is
S3-compatible and used through `django-storages`.

## New and changed files

- `Procfile` - `release` runs `migrate` and `collectstatic`; `web` runs gunicorn.
- `runtime.txt` - pins Python 3.12.
- `config/settings/prod.py` - `CSRF_TRUSTED_ORIGINS` from the environment, and
  optional S3/R2 media storage that turns on only when a bucket is configured
  (otherwise media stays on the local disk).
- `requirements.txt` - `django-storages` and `boto3` (used only when R2 is
  configured).
- `.env.example` - the production variables (CSRF origins and the `AWS_*` media
  settings).
- `README.md` - a Deployment section: the steps, the environment variables, media
  on R2, the scheduled `expire_unpaid_orders` job, and how to run
  `check --deploy`.
- `docs/demo-script.md` - the ten-minute defense walkthrough with who presents
  each module.

## Deploying (summary)

1. Push to GitHub; create a web service and a managed PostgreSQL database on the
   host.
2. Set the environment variables from `.env.example`, including
   `DJANGO_SETTINGS_MODULE=config.settings.prod`, a real `SECRET_KEY`,
   `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, the SMTP and Khalti values, and the
   `AWS_*` media values if using R2.
3. The `release` step migrates and collects static files on each deploy.
4. Create a superuser and (optionally) load the sample fixtures.
5. Schedule `expire_unpaid_orders` every few minutes.

## Likely defense questions

1. **How does the same code run locally and in production without changing it?**
   All environment-specific values are read from environment variables, and the
   settings are split: `dev.py` for local (console email, plain HTTP) and
   `prod.py` for the server (HTTPS hardening, WhiteNoise, optional R2 media).
   The host sets `DJANGO_SETTINGS_MODULE` to the production settings; nothing in
   the code changes between the two.

2. **Why store uploaded images on R2 instead of on the server?**
   On most hosts the application's disk is temporary and is wiped on each deploy,
   so uploaded images would vanish. An object store like R2 keeps them
   permanently and serves them cheaply (no egress fee). The storage backend is
   chosen by whether the bucket variables are set, so local development still
   uses the disk.

3. **What keeps the site secure in production?**
   `prod.py` forces HTTPS, marks cookies secure, enables HSTS and the nosniff and
   anti-framing headers, and lists the site in `CSRF_TRUSTED_ORIGINS`.
   `manage.py check --deploy` confirms there are no security warnings.
