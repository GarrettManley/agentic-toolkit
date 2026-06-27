# Runbook: Install Docker Engine in WSL2 for the sec-research sandbox

**Date:** 2026-06-26 · **Closes:** 2026-06-22-stage4a-sandbox-design.md §8 (install procedure gap)
· **Trackers:** hb-ctr (live-validate), hb-nxz (hardening follow-ups)

Stand up the Docker engine the Stage-4a sandbox calls via `wsl -e docker …`. Engine-in-WSL2,
**not Docker Desktop** (the code contract is `wsl -e docker`; the 4a spec locked this).

## Preconditions (verified 2026-06-26)

- Single WSL2 distro `Ubuntu` (noble / 24.04), default (`wsl -e` resolves here). It also hosts
  aether's Postgres (cluster 16, port 5432). `wsl -e docker info` == `wsl -d Ubuntu docker info`.
- **systemd already enabled** (`/etc/wsl.conf` → `[boot] systemd=true`, PID 1 = systemd). No
  `wsl.conf` edit needed; systemd auto-starts both Docker and Postgres on distro boot.
- No Docker installed anywhere prior.

## Install (run as root — `wsl -d Ubuntu -u root`; idempotent)

Reproduce inline (this exact sequence was used):

```bash
# 1. prerequisites
apt-get update -qq && apt-get install -y -qq ca-certificates curl
# 2. official Docker GPG key (idempotent overwrite)
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
# 3. apt source (idempotent overwrite)
ARCH="$(dpkg --print-architecture)"; CODENAME="$(. /etc/os-release && echo "$VERSION_CODENAME")"
echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list
# 4. install engine
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
# 5. enable + start (systemd present → also gives reboot-persistence for free)
systemctl enable --now docker
# 6. allow non-sudo `wsl -e docker` for the default user
usermod -aG docker garrett
```

**Resolved versions installed (the pin):** `docker-ce 5:29.6.1-1~ubuntu.24.04~noble`
(Docker 29.6.1), `containerd.io 2.2.5`. Re-pin to these exact strings for a reproducible
rebuild (`apt-get install docker-ce=5:29.6.1-1~ubuntu.24.04~noble …`).

## Group-apply (the only Postgres-blast-radius step) — was NOT needed

Docker-group membership normally needs a fresh distro session (`wsl -t Ubuntu`), which would
restart the distro and bounce Postgres. **In practice it was not required:** immediately after
`usermod`, `wsl -e docker info` returned exit 0 as the default user, and Postgres stayed online
(verified `pg_lsclusters` → cluster 16 still `online`). If a future machine needs the restart:
quiesce aether Postgres first, run `wsl -t Ubuntu` (terminate *only* this distro, never
`wsl --shutdown`), then verify both come back (systemd auto-starts them; `pg_lsclusters` →
`online`, `wsl -e docker info` → rc 0).

## Verify (the sandbox entry points)

```bash
wsl -e docker info                         # rc 0, no sudo
cd sec-research && python scripts/sandbox/doctor.py   # exit 0; pulls node:22-slim, python:3.12-slim, rust:1-slim, ruby:3.3-slim
VERIFY_LIVE=1 python -m pytest -q          # 348 passed, 1 skipped (LLM_LIVE only)
```

## Networking note

The Docker install switches iptables to nft and adds Docker's FORWARD/nat chains. Postgres
listens on loopback (127.0.0.1:5432); Docker does not touch loopback INPUT, so DB connectivity
is unaffected (verified post-install).

## Rollback

`systemctl disable --now docker`; `apt-get purge -y docker-ce docker-ce-cli containerd.io
docker-buildx-plugin docker-compose-plugin`; `rm /etc/apt/sources.list.d/docker.list
/etc/apt/keyrings/docker.asc`; `gpasswd -d garrett docker`. Postgres / WSL untouched.

## Recovery (partial-failure)

Each step is check-before-apply, so re-running is safe. If install fails after the apt source is
added (step 3) but before the engine installs (step 4), just re-run from step 4 — the key/source
overwrites are idempotent. If `systemctl enable --now docker` fails, inspect
`journalctl -u docker --no-pager | tail`; a common cause is iptables/nft conflicts (resolved here
by the `iptables` package the engine pulls in).
