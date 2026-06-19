# Render Deployment Steps for Anansi Atlas

This guide prepares `anansiatlas.com` to serve the public Anansi Atlas landing page and collect real `InterestSignup` records.

Do not commit secrets. Do not change DNS until the Render service is deployed, tested, and ready for custom domains.

## 1. Push the Repository

From the local repo:

```bash
git push origin main
```

## 2. Create Render PostgreSQL

1. In Render, create a new PostgreSQL database.
2. Choose the same region you plan to use for the web service.
3. Copy the internal database URL.
4. Use that value as `DATABASE_URL` on the web service.

## 3. Create Render Web Service

1. Create a new Web Service in Render.
2. Connect the GitHub repository.
3. Choose Docker deployment.
4. Use the existing Dockerfile path:

   ```text
   compose/linkedin/Dockerfile
   ```

5. Set Docker build arg:

   ```text
   BUILD_ENV=production
   ```

6. Set the web service start command to:

   ```bash
   gunicorn openoutreach.wsgi:application --bind 0.0.0.0:$PORT
   ```

Important: do not let Render run the Dockerfile default command for the public website. The default container command is for the original OpenOutreach daemon. The public Anansi Atlas site needs the Django web server command above.

## 4. Environment Variables

Use this template. Replace placeholders in Render's environment settings. Do not commit real values.

```text
SECRET_KEY=
DEBUG=False
ALLOWED_HOSTS=anansiatlas.com,www.anansiatlas.com,<render-app-domain>
CSRF_TRUSTED_ORIGINS=https://anansiatlas.com,https://www.anansiatlas.com,https://<render-app-domain>
DATABASE_URL=
EMAIL_HOST=
EMAIL_PORT=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=info@anansiatlas.com
SERVER_EMAIL=info@anansiatlas.com
```

Optional broader OpenOutreach variables are not required for the public Anansi Atlas landing page.

## 5. Static Files

Before the public launch, run:

```bash
python manage.py collectstatic --no-input
```

The repo currently defines:

- `STATIC_URL=/static/`
- `STATIC_ROOT=<repo>/staticfiles`

Render can serve static files if configured for the generated `staticfiles` directory, or a reverse proxy/static host can serve that directory. The current public landing page mostly uses inline template CSS, but Django admin static files still matter for admin review of signups.

## 6. Run Migrations

Run this in Render Shell or as a one-off job:

```bash
python manage.py migrate --no-input
```

## 7. Create Django Admin User

Run:

```bash
python manage.py createsuperuser
```

Use this account to review `InterestSignup` records in Django admin.

## 8. Test the Render App URL

Before changing DNS:

1. Open `https://<render-app-domain>/anansi-atlas/`.
2. Confirm the landing page loads.
3. Submit a test signup.
4. Confirm redirect to `/anansi-atlas/thanks/`.
5. Open `/admin/`.
6. Confirm the `InterestSignup` record exists.
7. Confirm `info@anansiatlas.com` receives the notification email.
8. Check Render logs for errors.

## 9. Add Custom Domains

In Render:

1. Add `anansiatlas.com`.
2. Add `www.anansiatlas.com`.
3. Render will provide the DNS records needed for the service.

## 10. Update DNS

Only after the Render service works on its Render URL:

1. Log in to the DNS provider currently managing:

   - `NS1.HOSTING.BUSINESSIDENTITY.LLC`
   - `NS2.HOSTING.BUSINESSIDENTITY.LLC`

2. Replace the current records pointing at `66.223.49.89` with the records Render provides.
3. Keep the previous DNS values noted until the Render domain is fully verified.

No DNS changes have been made from this repo.

## 11. Verify SSL

After DNS updates propagate:

1. Open `https://anansiatlas.com/anansi-atlas/`.
2. Open `https://www.anansiatlas.com/anansi-atlas/`.
3. Confirm both load over HTTPS.
4. Submit one production test signup.
5. Confirm the signup appears in admin.
6. Confirm the notification email arrives at `info@anansiatlas.com`.

## 12. Launch Blockers To Clear

- Confirm Render web start command uses Django web serving, not the daemon default.
- Configure static serving for Django admin assets.
- Set all production environment variables.
- Run migrations on the production database.
- Create a production admin user.
- Verify outbound email credentials.
- Only then update DNS.
