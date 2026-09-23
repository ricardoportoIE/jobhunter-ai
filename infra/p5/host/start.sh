#!/bin/bash
set -euo pipefail
umask 077
cd /opt/jobhunter
test -f /opt/jobhunter-session
python3 scripts/init_env.py
printf '\nWEB_PORT=15173\nAPI_PORT=18000\nJOBHUNTER_DB_PORT=15433\n' >> .env
mkdir -p .private
chown 10001:10001 .private
chmod 700 .private
docker compose up --build --detach --wait --wait-timeout 180
docker compose run --rm --no-deps -T -v /opt/jobhunter/.private:/private migrate \
  python -m jobhunter_api.manage bootstrap --credentials-file /private/login.txt
docker compose run --rm --no-deps -T migrate python -m jobhunter_api.manage seed
python3 infra/p5/host/operations.py verify
python3 infra/p5/host/operations.py backup
python3 infra/p5/host/operations.py restore-check
cat > /etc/systemd/system/jobhunter-health.service <<'UNIT'
[Unit]
Description=Publish redacted JobHunter demo health
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/jobhunter/infra/p5/host/operations.py health
UNIT
cat > /etc/systemd/system/jobhunter-health.timer <<'UNIT'
[Unit]
Description=Check the private demo each minute
[Timer]
OnBootSec=60
OnUnitActiveSec=60
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now jobhunter-health.timer
python3 infra/p5/host/operations.py health
touch .private/ready
