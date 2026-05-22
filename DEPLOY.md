# Deployment runbook — pocket.ionyx.org

This is the production runbook for the single droplet hosting `pocket.ionyx.org`. It documents what's where, how to redeploy, and how to recover when things go wrong.

If you're picking the project up for the first time, read **HANDOFF.md** first.

## Architecture

```
Browser ─https─▶ Cloudflare ─https─▶ Nginx :443 ─proxy─▶ Gunicorn 127.0.0.1:8002 ─▶ Django + Postgres
                                       │                          │
                                       └─/static/ alias────▶ /home/pocket/apps/pocket/staticfiles/
```

- **Domain**: `pocket.ionyx.org`. Cloudflare orange cloud is on; SSL/TLS mode is **Full** (CF terminates with its cert, origin terminates with snakeoil — CF doesn't validate origin cert in Full mode).
- **Origin**: a single DigitalOcean droplet, accessed via `ssh mydroplet`. The droplet also hosts unrelated services (`ionyx`, `n8n`, `sablonmechanics-v2`, plus Caddy installed but inactive). Pocket is isolated to its own user / port / database.
- **Web server**: Nginx 1.24.
- **App server**: Gunicorn 26 (systemd-managed), 2 sync workers, bound to `127.0.0.1:8002`.
- **Database**: Postgres 16 on the same droplet (`pocket` role + `pocket` database).
- **TLS at origin**: snakeoil cert (`/etc/ssl/certs/ssl-cert-snakeoil.pem`). Pre-existing on the droplet; not managed by Certbot for this site.

## What's where

| Thing | Path |
| --- | --- |
| Linux user | `pocket` (UID 1003), supplementary group `www-data` |
| Code | `/home/pocket/apps/pocket/` (clone of `git@github.com:aamsa/pocket.git`, branch `main`) |
| Virtualenv | `/home/pocket/apps/pocket/.venv/` (Python 3.12) |
| Static files (collected) | `/home/pocket/apps/pocket/staticfiles/` |
| Tailwind built CSS | `/home/pocket/apps/pocket/static/css/output.css` |
| Environment file | `/etc/pocket.env` (owner `root:pocket`, mode `0640`) |
| Postgres DB password backup | `/root/.pocket-db-pw` (mode `0600`) |
| systemd unit | `/etc/systemd/system/pocket.service` |
| Nginx vhost | `/etc/nginx/sites-available/pocket` (symlinked to `sites-enabled/`) |
| Gunicorn log | `journalctl -u pocket` |
| Nginx access log | `/var/log/nginx/access.log` |
| Nginx error log | `/var/log/nginx/error.log` |

The home directory has `chmod o+x` so Nginx (running as `www-data`) can traverse to the staticfiles directory without listing the home contents.

## Day-2 redeploy

```bash
ssh mydroplet
cd /home/pocket/apps/pocket
sudo -u pocket git pull
sudo -u pocket .venv/bin/pip install -r requirements.txt
sudo -u pocket .venv/bin/tailwindcss -i static/css/input.css -o static/css/output.css --minify
sudo -u pocket bash -c 'set -a; . /etc/pocket.env; set +a; \
  .venv/bin/python manage.py migrate --noinput && \
  .venv/bin/python manage.py collectstatic --noinput'
systemctl restart pocket
systemctl status pocket --no-pager
```

If the deploy was a no-op for migrations / static files (just a template / view tweak), you can skip those steps — `git pull && systemctl restart pocket` is enough. Always tail `journalctl -u pocket -f` for ~10 seconds after the restart to confirm there's no boot-time exception.

## One-time: May 2026 revamp (fresh start)

The revamp removed the pocket/transfer/sharing/credit-card models and replaced them with the income/expense ledger. There is **no data migration** — it's a clean reset. On the droplet, after pulling the revamp code:

```bash
ssh mydroplet
cd /home/pocket/apps/pocket
sudo -u pocket git pull
sudo -u pocket .venv/bin/pip install -r requirements.txt
systemctl stop pocket
# Drop & recreate the application database (destroys old pocket/transfer data).
sudo -u postgres psql -c "DROP DATABASE pocket;"
sudo -u postgres psql -c "CREATE DATABASE pocket OWNER pocket;"
sudo -u pocket bash -c 'set -a; . /etc/pocket.env; set +a; \
  .venv/bin/tailwindcss -i static/css/input.css -o static/css/output.css --minify && \
  .venv/bin/python manage.py migrate --noinput && \
  .venv/bin/python manage.py collectstatic --noinput && \
  .venv/bin/python manage.py createuser admin --superuser --display-name "Admin" --password "<pw>" && \
  .venv/bin/python manage.py createuser wife --display-name "Wife" --password "<pw>" && \
  .venv/bin/python manage.py seed_household admin wife'
systemctl start pocket
# Optional: seed today's snapshot so the net-worth chart has a baseline immediately.
sudo -u pocket bash -c 'set -a; . /etc/pocket.env; set +a; .venv/bin/python manage.py snapshot_balances'
```

`migrate` auto-seeds the default categories + starter sources via a `post_migrate` signal; `seed_household` claims those sources for the household.

## Scheduled jobs (systemd timers)

Two nightly management commands keep the ledger current. Run them as the `pocket` user, sourcing `/etc/pocket.env`, **recurring first** so the day's auto-entries are included in the snapshot. Use `pocket-*` names so co-tenant services are untouched.

`/etc/systemd/system/pocket-maintenance.service`:
```ini
[Unit]
Description=Pocket nightly maintenance (recurring + snapshot)
After=network.target postgresql.service

[Service]
Type=oneshot
User=pocket
WorkingDirectory=/home/pocket/apps/pocket
EnvironmentFile=/etc/pocket.env
ExecStart=/home/pocket/apps/pocket/.venv/bin/python manage.py run_recurring
ExecStart=/home/pocket/apps/pocket/.venv/bin/python manage.py snapshot_balances
```

`/etc/systemd/system/pocket-maintenance.timer`:
```ini
[Unit]
Description=Run Pocket maintenance nightly

[Timer]
OnCalendar=*-*-* 00:05:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable: `systemctl daemon-reload && systemctl enable --now pocket-maintenance.timer`. Check: `systemctl list-timers pocket-maintenance.timer` and `journalctl -u pocket-maintenance.service -n 50`. The timezone follows the droplet's (set to match Asia/Jakarta if needed). Both commands are idempotent, so a manual re-run or a `Persistent=true` catch-up after downtime is safe.

## Rollback

```bash
ssh mydroplet
cd /home/pocket/apps/pocket
sudo -u pocket git log --oneline -5         # find the previous good commit
sudo -u pocket git checkout <prev-sha>
# If the rollback crosses a migration boundary, manually `migrate <app> <prev-migration-id>`
# BEFORE the checkout so Django can find the right files. Check `manage.py showmigrations`.
systemctl restart pocket
```

`git checkout <sha>` is the safe move — it puts the working tree in detached HEAD without losing main. To return to latest: `git checkout main && git pull && systemctl restart pocket`.

## Common operations

### Tail logs
```bash
journalctl -u pocket -n 200 -f       # gunicorn (access + error)
tail -f /var/log/nginx/access.log    # all vhosts; grep for pocket.ionyx.org
tail -f /var/log/nginx/error.log
```

### Django shell on prod
```bash
ssh mydroplet
cd /home/pocket/apps/pocket
sudo -u pocket bash -c 'set -a; . /etc/pocket.env; set +a; .venv/bin/python manage.py shell'
```

### Reset a user's password
```bash
sudo -u pocket bash -c 'set -a; . /etc/pocket.env; set +a; \
  .venv/bin/python manage.py setpassword <username> --password "<new>" --no-force-change'
```

### Add a user
```bash
sudo -u pocket bash -c 'set -a; . /etc/pocket.env; set +a; \
  .venv/bin/python manage.py createuser <username> [--superuser] --display-name "<Name>" --password "<pw>" && \
  .venv/bin/python manage.py setpassword <username> --password "<pw>" --no-force-change'
```

### Postgres console
```bash
sudo -u postgres psql pocket
# Or with the application credentials:
PGPASSWORD=$(grep ^DB_PASSWORD= /etc/pocket.env | cut -d= -f2) psql -h 127.0.0.1 -U pocket pocket
```

### Reload Nginx after config change
```bash
nginx -t && systemctl reload nginx
```

`reload`, never `restart`. Reload re-reads config without dropping connections; restart drops every other vhost on the box too.

## Troubleshooting

**Browser: "502 Bad Gateway" or hangs.** Gunicorn died. `systemctl status pocket` and `journalctl -u pocket -n 100` to see the traceback. Most often: a migration didn't run, an env var is missing, or `output.css` wasn't rebuilt and a template references a class that doesn't exist (Tailwind v4 silently ignores unknown classes, so this rarely 502s — but worth a check).

**Browser: "Bad Request (400)".** `ALLOWED_HOSTS` doesn't include the host you're hitting. The env file lists `pocket.ionyx.org,127.0.0.1,localhost`. If you're testing via a Cloudflare tunnel or a different domain, edit `/etc/pocket.env` and `systemctl restart pocket`.

**Static files: 403 Forbidden.** Nginx (running as `www-data`) can't traverse `/home/pocket`. Re-apply `chmod o+x /home/pocket`. The directory itself stays `o-r` so its contents aren't listable.

**Static files: 404 Not Found.** `collectstatic` wasn't run, or it ran as the wrong user and Nginx can't read the result. Run `sudo -u pocket .venv/bin/python manage.py collectstatic --noinput` and confirm files land in `/home/pocket/apps/pocket/staticfiles/`.

**TLS: "ERR_SSL_VERSION_OR_CIPHER_MISMATCH" from browser.** Cloudflare SSL mode is set to "Full Strict". Switch to "Full" — the origin cert is snakeoil and won't validate against a public CA.

**TLS: "Cloudflare can't reach origin".** DigitalOcean droplet firewall might not have 443 / 80 open to Cloudflare's IP ranges. `ufw status` and verify; if locked down, allow CF IPs from <https://www.cloudflare.com/ips-v4/>.

**Migration crash mid-deploy.** Stop the world: `systemctl stop pocket`. Investigate (`journalctl -u pocket`). Re-apply migrations with `migrate --fake-initial` only if you understand exactly what's missing. When in doubt: roll back the code to the previous SHA, restart, then redeploy carefully.

**Cloudflare cache returning stale assets.** Bump `STATIC_VERSION` in `/etc/pocket.env` (it's a query-string cache buster the templates append to `output.css` and `app.js`), then `systemctl restart pocket`. As a heavier hammer, use the Cloudflare dashboard → Caching → Configuration → Purge Everything.

## Things NOT to touch on the droplet

- Other vhosts in `/etc/nginx/sites-available/` (`default`, `ionyx`, `n8n`, `sablonmechanics`, `sablonmechanics-v2`)
- Other systemd units (`ionyx.service`, `n8n.service`, `sablonmechanics-v2.service`)
- Other Postgres databases (`ionyx`, `sablonmechanics`, `sablonmechanics_v1_test`, `sablonmechanics_v2`) or roles
- `/etc/letsencrypt/` (Certbot manages the certs for the other ionyx subdomains, not for this one)
- `/etc/caddy/Caddyfile` (Caddy is installed but inactive — leave it alone)
- The droplet's `tailscaled` (different access path used elsewhere)

## Acceptance check after any change

```bash
ssh mydroplet "for svc in nginx postgresql@16-main ionyx n8n sablonmechanics-v2 pocket; do
  printf '%-22s %s\n' \"\$svc\" \"\$(systemctl is-active \$svc)\"
done"
curl -sI https://pocket.ionyx.org/accounts/login/ -m 10 | head -1   # 200
```

All six services should report `active`. `pocket.ionyx.org/accounts/login/` should return `HTTP/2 200`.
