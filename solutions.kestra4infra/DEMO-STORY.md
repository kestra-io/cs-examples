# kestra4infra demo story

### The story in one line
In most companies, provisioning ends when the ticket closes. In Kestra, a deployment stays a live
inventory of connected assets. Each asset carries its own expiry dates, its own day-2 actions, and
the dependencies recorded by the tasks that built it. That's why renewals happen on their own,
impact is answerable in seconds, and teardown is safe.

### The problem to open with (2 min)
- A typical request (VM, VLAN, firewall rule, DNS, AD account, certificate, app) goes through 6 to 8 tools and teams. At the end, the knowledge of what was built and what it depends on lives in tickets and people's heads.
- Day 2 is where the cost sits: certificates expire, service-account passwords expire, leases are never reclaimed, and nobody can say what breaks if the shared switch or the CA goes down.
- vRA handles day 1 well and day 2 poorly. Its catalog doesn't know about the dependency graph.

### Act 1: One request, one deployment (5 min)
- Run `provision_deployment` from its form: `orders`, `prod`, 2 servers.
- While it runs, show the Gantt view: VLAN, security group, firewall, service account, then per server Terraform, AD join, CIS hardening, app install and DNS, then certificate and health check.
- Open the deployment in the new UI: 11 resources, each with an owner, metadata and buttons.
- **Talking point:** each step declares the asset it built and what it built it from, so the inventory is produced by the automation itself. Nobody maintains a CMDB by hand.

### Act 2: The dependency graph (3 min)
- Open a VM's Dependencies tab: switch to VLAN to VM to app to certificate to health check.
- Point out the shared assets (core switch, edge firewall, AD, CA, CIS baseline). They belong to no deployment, and that's where risk concentrates.
- **Talking point:** the graph comes from the automation's own lineage, so it can't drift from reality the way a CMDB does.

### Act 3: Day 2 lives on the asset (5 min)
- Show the buttons where people look: Renew on the certificate, Rotate on the service account, Resize and Re-apply configuration on a VM, Extend lease and Decommission on the deployment.
- Click Renew certificate. It's a real `openssl` re-issue: the expiry moves, the old serial is kept, and a health check runs afterwards.
- **Talking point:** requesting a resource and operating it use the same mechanism, a form on a flow. Operations don't need a separate catalog.

### Act 4: Expiry becomes an event, not a scan (4 min)
- Show `billing-uat`. Its certificate and password were created with 10-day and 5-day lifetimes. Without anyone clicking, the certificate was renewed and the password rotated, and the metadata says `renewed_by: cert_expiry_autorenew`.
- Show the VM-created trigger: a CMDB entry and monitoring enrolment fired 2 seconds after the VM appeared. Provisioning doesn't know that flow exists.
- **Talking point:** these are asset triggers. Teams subscribe to asset events, such as "any new VM" or "any certificate within 15 days", instead of editing someone else's pipeline. That decouples the platform team from the security, CMDB and monitoring teams.

### Act 5: Blast radius (5 min, the high point)
- Run Blast radius on the issuing CA: 6 assets in 2 deployments, two teams to notify.
- Then simulate an outage: run the health check with `outcome=degraded`. The incident flow starts on its own and lists the suspects (everything the app depends on, the shared switch and CA included), the deployments affected and the team to page.
- **Talking point:** the same graph answers "what breaks if I touch this" before a change and "what could have caused this" during an incident. That's change risk and root-cause triage from one model.

### Act 6: Clean exit (2 min)
- Decommission a deployment: the flow finds its resources in the inventory and removes them last-built-first. Shared infrastructure isn't touched, expiry dates are cleared, and the deployment shows as destroyed.
- **Talking point:** no orphaned DNS records, firewall rules or AD accounts. That's the usual audit finding after a vRA decommission.

### Doors it opens (the close)
- **Change risk scoring:** run blast radius on every change ticket's target and attach the result to the CAB record.
- **Compliance by metadata:** certificate expiry, password age, OS end-of-life, firewall rule recertification and licence expiry are already on the assets. One dashboard or report covers audits.
- **Lease and cost governance:** expired leases are flagged automatically, and cost center and owner sit on every asset for chargeback.
- **Drift and patching:** baseline changes come with their blast radius. Re-apply configuration is one click or one trigger, and patch waves can be built from `patch_group`.
- **vRA migration:** the catalog item becomes the form, day-2 actions sit on assets, and the dependency graph is something vRA never had.

### Two ways to pitch it

| Angle | Audience | Lead with | Critical failure mode |
|---|---|---|---|
| **Day-2 automation** | Ops and platform teams, vRA customers | Acts 3, 4, 6: renewals, rotations, clean teardown | Comes across as a better runbook tool if the graph isn't shown. Keep Act 5 in even when short on time. |
| **Risk and resilience** | Infra leadership, security, change management | Acts 2 and 5: graph, blast radius, incident | Falls apart if asked "where does the graph come from in brownfield?" Answer: discovery flows (VMware, NetBox, cloud APIs) record existing assets the same way. Only greenfield is built here, so say so. |

### What to say about the simulation
- It's a working demo of the model, not of the integrations. The certificate step is real. VM, network, DNS, AD and firewall steps are simulated, with the production task (Terraform, Ansible, NetBox, PowerShell, PAN-OS API) in a comment under each one.
- Lead with that honestly. The value shown is the asset model, triggers and graph, and those are fully real.

### Practical notes for the session
- Expiry-based triggers fire at Kestra's hourly expiry check. Either show the `billing-uat` results that already exist, or set `kestra.assets.ttl-check.fixed-delay: PT1M` and restart Kestra before the session.
- Reset afterwards: run the health check with `healthy` on `orders-prod-app`.
- Total is about 25 minutes. A 10-minute cut is Act 1 (pre-run), Act 4 and Act 5.
