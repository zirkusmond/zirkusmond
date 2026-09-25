# Listmonk Migration Guide

This guide covers migrating from Mailchimp to Listmonk with Brevo SMTP.

## Overview

- **Self-hosted newsletter**: Listmonk on OVH (news.zirkusmond.de)
- **Shared database**: Uses existing PostgreSQL container with separate `listmonk_db` database
- **SMTP**: Brevo (all-in-one for transactional + newsletter emails)
- **Cost**: Starter plan €25/month (20k emails) or Business €65/month (60k emails)
- **Cost savings**: ~€95-119/month (€1,140-1,428/year) vs Mailchimp's €144/month

## Prerequisites

1. **Brevo account setup**:
   - You already have Brevo configured for transactional emails
   - Upgrade to Starter plan (€25/month for 20k emails) or Business plan (€65/month for 60k emails)
   - Get your existing SMTP credentials from Brevo settings

2. **DNS configuration**:
   - Add `news.zirkusmond.de` A record → OVH server IP
   - Brevo SPF/DKIM should already be configured for zirkusmond.de (from existing setup)

3. **GitHub Secrets** (add these in repo settings):
   - `LISTMONK_URL` = `http://prod_listmonk:9000` (for production)
   - `LISTMONK_API_USERNAME` = admin username (set during Listmonk setup)
   - `LISTMONK_API_PASSWORD` = admin password (set during Listmonk setup)
   - `LISTMONK_LIST_ID` = `1` (or the ID of your default list in Listmonk)

## Deployment Steps

### 1. Create Docker volume on server

SSH into your OVH server and create the required volume for Listmonk uploads:

```bash
ssh user@your-server

# Production - stores uploaded campaign images/attachments
docker volume create ubuntu_zm_listmonk_data
```

### 2. Export Mailchimp subscribers to Django database

**IMPORTANT: Do this BEFORE shutting down Mailchimp!**

```bash
# Locally, with Mailchimp credentials still in .envrc
cd backend
uv run python manage.py export_mailchimp_to_db
```

This ensures all Mailchimp subscribers (including any not in Django DB) are captured.

### 3. Create the Listmonk database

```bash
# On the server, create the listmonk_db database
cd ~/zirkusmond
docker exec -i prod_postgres psql -U mond -d postgres -c "CREATE DATABASE listmonk_db OWNER mond;"

# Verify it was created
docker exec -i prod_postgres psql -U mond -d postgres -c "\l"
```

### 4. Initialize Listmonk

Database config is already in `docker-compose.yml` - no manual env setup needed!

```bash
# First time setup - this creates the database schema and admin user
docker compose run --rm listmonk ./listmonk --install

# You'll be prompted to create an admin username/password
# Save these credentials - you'll need them for LISTMONK_API_USERNAME and LISTMONK_API_PASSWORD
```

### 5. Start Listmonk

```bash
docker compose up -d listmonk
```

### 6. Configure nginx reverse proxy

The `deploy/nginx.default` file already includes the Listmonk block. Just reload nginx:

```bash
docker exec nginx-nginx-1 nginx -s reload
```

### 7. Access Listmonk UI and create a list

1. Visit https://news.zirkusmond.de
2. Login with the admin credentials you created
3. Create a new mailing list (e.g., "Newsletter")
4. Note the list ID (usually `1` for the first list)
5. Update the `LISTMONK_LIST_ID` GitHub secret with this ID

### 8. Configure SMTP in Listmonk UI

1. Go to Settings → SMTP
2. Add Brevo SMTP settings (same as your Django transactional setup):
   - Host: `smtp-relay.brevo.com`
   - Port: `587`
   - Username: Your Brevo SMTP username (from Brevo → SMTP & API → SMTP)
   - Password: Your Brevo SMTP password/key
   - TLS: STARTTLS
3. Send a test email to verify SMTP is working

**Note**: This uses the same Brevo account for both Django transactional emails AND Listmonk newsletter emails - one unified platform!

### 9. Export existing subscribers from Django to Listmonk

```bash
# On the server
cd ~/zirkusmond
docker compose exec zm uv run python manage.py export_subscribers_to_listmonk
```

This will bulk import all ~6000 subscribers from your Django database into Listmonk.

### 10. Update GitHub secrets

Add/update these repository secrets:
- `LISTMONK_URL` = `http://prod_listmonk:9000`
- `LISTMONK_API_USERNAME` = your admin username
- `LISTMONK_API_PASSWORD` = your admin password
- `LISTMONK_LIST_ID` = `1` (or your list ID)

Remove old Mailchimp secrets (optional, but recommended for cleanup):
- `MAILCHIMP_API_KEY`
- `MAILCHIMP_SERVER_PREFIX`
- `MAILCHIMP_AUDIENCE_ID`

### 11. Deploy the updated code

Push to `prod` branch to trigger the deployment workflow. The workflow automatically:
- Pulls the `listmonk/listmonk:latest` image
- Starts the Listmonk container
- Uses Listmonk API instead of Mailchimp for new signups
- Falls back gracefully if Listmonk is unavailable (still saves to Django DB)

### 12. Test the integration

1. Test newsletter signup on your website
2. Verify the subscriber appears in both:
   - Django admin (`/mondmin/newsletter/newsletterregistration/`)
   - Listmonk UI (https://news.zirkusmond.de/admin/subscribers)
3. Send a test campaign from Listmonk to verify SMTP is working

## Rollback Plan

If something goes wrong:

1. **Keep the Django `NewsletterRegistration` model** - all emails are still stored there
2. **Revert the code changes** by reverting the commits
3. **Re-enable Mailchimp** by adding back the secrets and deploying
4. The Listmonk container can stay running without interfering

## Cost Comparison

### Mailchimp (current)
- €120 + VAT/month for 6000 subscribers
- ~€144/month with VAT (20% VAT)
- **€1,728/year**

### Listmonk + Brevo (new)

**Option 1: Starter Plan (recommended)**
- €25/month for 20,000 emails
- Covers: 300 transactional/month + 3 newsletter campaigns (6k × 3 = 18k)
- **€300/year**
- **Savings: €119/month (€1,428/year) = 83% cheaper**

**Option 2: Business Plan**
- €65/month for 60,000 emails
- Covers: 300 transactional/month + 9 newsletter campaigns (6k × 9 = 54k)
- **€780/year**
- **Savings: €79/month (€948/year) = 55% cheaper**

**Option 3: Pay-as-you-go** (if sending < 1 campaign/month)
- Free tier: 300 transactional emails/day (covers Django)
- €1/1000 marketing emails
- Only viable if sending very infrequently

## Troubleshooting

### Listmonk won't start
- Check logs: `docker compose logs listmonk`
- Verify database connection (check `DB_PASSWORD` env var)
- Ensure `listmonk_db` database exists

### Subscribers not syncing
- Check Django logs for Listmonk API errors
- Verify `LISTMONK_URL` is correct (should be `http://prod_listmonk:9000` from within Docker network)
- Test API manually: `curl -u username:password http://prod_listmonk:9000/api/subscribers`

### SMTP not working
- Verify Brevo SMTP credentials in Listmonk settings (Settings → SMTP & API in Brevo dashboard)
- Ensure you've upgraded from free tier (free tier has daily limits)
- Test SMTP from Listmonk UI (Settings → SMTP → Send test email)
- Check Brevo dashboard for sending quota/limits

### Emails marked as spam
- Ensure SPF/DKIM records are properly configured in DNS (should already be set up for Brevo)
- Check Brevo deliverability settings and domain authentication
- Warm up your sending reputation (start with smaller batches)
- Use Brevo's email validation tools

## Next Steps

1. **Upgrade Brevo plan**: Move from free tier to Starter (€25/month) or Business (€65/month)
2. **Warm up sending**: Start with small campaigns initially to build sender reputation
3. **Create templates in Listmonk**: Design your newsletter templates
4. **Set up campaigns**: Schedule your first campaign
5. **Monitor deliverability**: Check Brevo dashboard for bounce/spam rates
6. **Cancel Mailchimp subscription**: Once you're confident everything works (save €1,428/year!)
