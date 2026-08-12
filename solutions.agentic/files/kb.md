# Infra Team – Web Tier Playbooks

## 1) Nginx 502 / Unhealthy Upstreams (Linux)
**Symptoms:** 502 from internal portal, `nginx -t` OK, service running but upstream app momentarily unhealthy.

**Triage Steps:**
- Check service status: `systemctl status nginx`
- Validate config: `nginx -t`
- Tail errors: `journalctl -u nginx -n 100`
- Quick remediation (low risk): `systemctl restart nginx`
- Post-check: curl the internal URL and ensure HTTP 200 within 60s.

**Guardrails:** Only restart during low-risk windows or when incident severity is ≥2 and change is standard/reversible.


## 2) Disk Usage High (Linux)
Check with `df -h` and rotate logs with `logrotate` or `journalctl --vacuum-time=3d`. Avoid deleting app data.


## 3) Laptop Fan Noise (End User)
Non-urgent; advise cleaning and monitoring. Do **not** perform server actions.
