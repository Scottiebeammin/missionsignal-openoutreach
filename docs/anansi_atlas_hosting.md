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

- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`
- `SERVER_EMAIL`

The app uses Django email settings only. No newsletter platform or third-party marketing automation is wired in yet.

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
