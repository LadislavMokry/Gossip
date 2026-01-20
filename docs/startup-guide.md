# Startup Guide

## Prereqs

- Python 3.12+
- Supabase project credentials in `.env.local`

Required env vars:

```
SUPABASE_URL=...
SUPABASE_KEY=...
```

## Install dependencies

```
python3 -m pip install -r requirements.txt
```

If your environment enforces PEP 668 and blocks installs, use:

```
python3 -m pip install -r requirements.txt --break-system-packages
```

## Start the API (local dev)

```
python -m uvicorn app.main:app --reload --port 8000
```

Open:

```
http://127.0.0.1:8000
```

## Server access (Hetzner)

SSH from your local machine:

```
ssh -i "$env:USERPROFILE\\.ssh\\id_ed25519_hetzner" root@46.224.232.56
```

Move into the repo + activate venv:

```
cd /root/OnePlace
source .venv/bin/activate
```

Check service status:

```
systemctl status oneplace-api.service --no-pager
systemctl list-timers --all | grep oneplace
```

Logs:

```
tail -n 50 /var/log/oneplace/pipeline.log
```

Admin UI (basic auth):

```
http://46.224.232.56/
```
