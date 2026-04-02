# GlobalInfra – Ops & Access Playbooks

## 1) Web Service Outage (Nginx 502 / Unhealthy Upstreams)

**Context:** Internal or customer-facing web portals intermittently return `502 Bad Gateway`.
**Symptoms:** `nginx -t` OK, process running, but app backend unreachable or unhealthy.

**Triage Steps:**

1. Check service status: `systemctl status nginx`
2. Validate config syntax: `nginx -t`
3. Tail last 100 logs: `journalctl -u nginx -n 100`
4. Quick remediation (low risk): `systemctl restart nginx`
5. Verify: `curl -s -o /dev/null -w "%{http_code}" https://<site>` → expect `200`

**Guardrails:**

* Restart only if the issue is scoped to one host.
* Skip if during active deploy window or major incident.
* Always log the action in JIRA before/after execution.

---

## 2) New User Provisioning (Internal Tools)

**Context:** Common requests for granting access to GitLab, VPN, or Grafana.
**Symptoms:** User reports “unauthorized”, “invalid login”, or “access denied” messages.

**Triage / Provisioning Steps:**

1. Validate user identity via HR system or LDAP.
2. Check existing account: `ldapsearch -x uid=<username>`
3. If missing, run provisioning workflow:

   ```bash
   ./create_user.sh --username <user> --group devops
   ```
4. Add user to requested system (GitLab example):

   ```bash
   gitlab-user add <user> --group devops
   ```
5. Confirm successful login test or send password reset link.

**Guardrails:**

* Only auto-provision from corporate email domain.
* Never reuse passwords or tokens.
* Audit all created accounts weekly.

---

## 3) API Token Rotation Request

**Context:** Developer requests new service token for CI/CD or application integration.
**Symptoms:** Expired token alerts or “401 Unauthorized” errors on API calls.

**Rotation Steps:**

1. Validate requester’s team & service scope.
2. Deactivate previous token:

   ```bash
   ./revoke_token.sh --service payments
   ```
3. Issue new one via internal vault:

   ```bash
   ./create_token.sh --service payments --ttl 90d
   ```
4. Update dependent workflows (Jenkins, GitHub, etc.) with the new token.
5. Confirm integration success with a sample API call.

**Guardrails:**

* Only one active token per service per user.
* Rotate secrets every 90 days.
* Log token ID (not value) in audit trail.

---

## 4) Disk Usage High (Linux)

**Context:** System alert or user report: “low space on `/var` or `/opt`”.
**Triage Steps:**

1. Run `df -h` and identify partitions >85%.
2. Check largest files: `du -sh /* | sort -rh | head -10`
3. Rotate logs:

   ```bash
   logrotate /etc/logrotate.conf
   journalctl --vacuum-time=3d
   ```
4. For app logs, archive to S3: `aws s3 sync /var/log/app s3://infra-archives/$(hostname)/`
5. Verify free space after cleanup.

**Guardrails:**

* Never delete `/var/lib` or `/etc` manually.
* Escalate if >90% persists post-cleanup.

---

## 5) Irrelevant: Coffee Machine Network Timeout ☕

**Context:** Office IoT appliance “CoffeeBot” fails to connect to Wi-Fi.
**Note:** Not managed by InfraOps. Forward to Facilities Helpdesk.

Use your legs and walk down the street to Honey & Basil Coffee!
