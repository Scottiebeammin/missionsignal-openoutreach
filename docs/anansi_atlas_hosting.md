# Anansi Atlas Hosting and Domain Notes

## Current Domain

- Domain: `anansiatlas.com`
- Registrar/DNS appears to use: DomainRegistry.com LLC / BusinessIdentity
- Nameservers confirmed by DNS:
  - `NS1.HOSTING.BUSINESSIDENTITY.LLC`
  - `NS2.HOSTING.BUSINESSIDENTITY.LLC`
- Current DNS resolution observed during local verification:
  - `anansiatlas.com` A record: `66.223.49.89`
  - `www.anansiatlas.com` A record: `66.223.49.89`

No DNS changes were made.

## Current Lead Capture

The public Anansi Atlas page at `/anansi-atlas/` stores `InterestSignup` records locally and redirects to `/anansi-atlas/thanks/`.

After a signup is saved, Django sends a plain-text notification email to:

- `info@anansiatlas.com`

The signup remains saved even if the notification email fails.

## Required Production Email Variables

Set these in the production environment. Do not commit secret values.

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`
- `SERVER_EMAIL`

The app uses Django email settings only. No newsletter platform or third-party marketing automation is wired in yet.

## Deployment Target Recommendation

Fastest and safest target for the first public Anansi Atlas pilot:

1. **Render Docker Web Service + managed PostgreSQL**

   Render is a good fit because this repo already has a Dockerfile and Django can run as a simple web service. Use Render's managed PostgreSQL for `InterestSignup` records instead of relying on a local SQLite file. This keeps deployment simple while giving the pilot a real database, backups, environment variables, logs, and managed SSL.

2. **Railway**

   Railway is also fast for Django plus PostgreSQL, but the repo does not currently include Railway-specific config. It is a reasonable alternative if the user already prefers Railway.

3. **DigitalOcean App Platform**

   Also viable for a Dockerized Django app with managed database, but generally a bit more setup-heavy than Render for a first landing page pilot.

4. **Fly.io**

   Strong for containerized apps and regional deployment, but it introduces more operational concepts than needed for a simple public landing page and signup capture.

5. **Current `66.223.49.89` host / VPS**

   Potentially usable only if the user has hosting control, SSH or control panel access, Python/Docker support, process management, SSL, and database backup capability. Without those details, it is riskier than a managed app host.

## Current Host Review

The repository does not contain deployment config specific to `66.223.49.89`.

Because `anansiatlas.com` and `www.anansiatlas.com` currently resolve to `66.223.49.89`, the domain appears to point at an existing hosting account or default host. From the repo alone, it is not possible to confirm whether that host is unused, active, shared hosting, VPS, or another service.

Questions/credentials needed from the user before using the current host:

- Is `66.223.49.89` controlled by the user?
- Is it shared hosting, VPS, cPanel-style hosting, or another platform?
- Does it support Docker or Python 3.12 web apps?
- Is SSH available?
- Is there a database available, preferably PostgreSQL?
- How are environment variables configured?
- How are long-running web processes managed?
- How is HTTPS/SSL provisioned?
- Are backups available for the database?

## Still Needed To Make The Site Live

1. Deployment host

   Choose where the Django app will run, such as a VPS, platform-as-a-service, or container host.

2. Database

   Configure a production database and backups. Local development currently uses SQLite under `data/`.

3. Environment variables

   Set production values for Django secrets, email settings, allowed hosts, database connection, and any existing app configuration required by the deployment target.

4. Static files

   Run Django static collection during deployment and serve `STATIC_ROOT` through the host, reverse proxy, or object storage/CDN.

5. `ALLOWED_HOSTS`

   Configure production hostnames, including:

   - `anansiatlas.com`
   - `www.anansiatlas.com`

6. DNS records

   Point the apex and `www` records to the selected deployment host. Current records already point to `66.223.49.89`, but that address still needs to match the actual production host.

7. SSL

   Provision HTTPS certificates for `anansiatlas.com` and `www.anansiatlas.com`, commonly through Let's Encrypt or the deployment host's managed certificate system.

8. Smoke test

   Verify:

   - `/anansi-atlas/` loads over HTTPS.
   - The signup form saves an `InterestSignup`.
   - `info@anansiatlas.com` receives the notification email.
   - `/anansi-atlas/thanks/` renders after submission.
   - Admin review of `InterestSignup` records works.
