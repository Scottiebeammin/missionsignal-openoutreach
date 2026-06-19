# Anansi Atlas Deployment Checklist

Use this checklist to make `anansiatlas.com` live without committing secrets or changing DNS prematurely.

## Recommended Target

Use **Render Docker Web Service + Render PostgreSQL** for the first public pilot unless there is a confirmed, production-ready host already available at `66.223.49.89`.

Why Render:

- The repo already has a Dockerfile.
- Render supports environment variables, deploy logs, managed SSL, and managed PostgreSQL.
- It avoids operating a VPS for the first pilot.
- PostgreSQL is safer than a production SQLite file for real signups.

## Pre-Deploy

1. Push code to GitHub.
2. Choose the deployment host.
3. Create a production PostgreSQL database.
4. Confirm the production web command.
5. Confirm static file strategy.
6. Confirm admin access plan.

## Required Environment Variables

Set these in the deployment host. Do not commit real values.

- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS=anansiatlas.com,www.anansiatlas.com`
- `CSRF_TRUSTED_ORIGINS=https://anansiatlas.com,https://www.anansiatlas.com`
- `DATABASE_URL`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`
- `SERVER_EMAIL`

## Existing Optional / Broader App Variables

These may be needed only if running broader OpenOutreach automation features, not the Anansi Atlas public landing page:

- `HOST_UID`
- `HOST_GID`
- `TZ`
- `DJANGO_ALLOW_ASYNC_UNSAFE`

Most Anansi Atlas public landing and deterministic dashboard features do not require LinkedIn credentials, LLM keys, scraping, crawling, agents, or external APIs.

## Deploy

1. Build from the Dockerfile.
2. Set all production environment variables.
3. Run migrations:

   ```bash
   .venv/bin/python manage.py migrate --no-input
   ```

   In a Docker deployment, run the equivalent command inside the release/deploy environment.

4. Collect static files:

   ```bash
   .venv/bin/python manage.py collectstatic --no-input
   ```

5. Create an admin user:

   ```bash
   .venv/bin/python manage.py createsuperuser
   ```

6. Start the web service.

## Domain and SSL

1. Confirm the deployment host target value.
2. Update DNS only after the deployment host is ready.
3. Point:

   - `anansiatlas.com`
   - `www.anansiatlas.com`

   to the deployment host.

4. Enable SSL for both hostnames.
5. Verify HTTP redirects to HTTPS if the host supports it.

## Smoke Test

1. Open `https://anansiatlas.com/anansi-atlas/`.
2. Confirm the landing page renders.
3. Submit a test signup.
4. Confirm redirect to `/anansi-atlas/thanks/`.
5. Confirm the `InterestSignup` exists in Django admin.
6. Confirm `info@anansiatlas.com` receives the notification email.
7. Open `/admin/` and confirm admin login works.
8. Check deployment logs for errors.
9. Confirm no secrets appear in logs.

## Rollback Notes

- Keep the previous deployment available until signup and admin smoke tests pass.
- If email fails, signups should still save locally; check `InterestSignup` in admin.
- If DNS has already changed and the app is unavailable, point DNS back to the previous host while the issue is fixed.
