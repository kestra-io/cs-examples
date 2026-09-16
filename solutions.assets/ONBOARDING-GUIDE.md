# Onboarding your Ansible inventory into Kestra Assets

This guide walks through turning an existing Ansible inventory into a live, queryable inventory
inside Kestra, and then building a fleet dashboard on top of it that answers questions like "how
many VMs are unpatched", "what OS mix are we running", "which clouds are we on", and "whose TLS
certificates expire this month".

It is written for whoever maintains your Ansible inventory and playbooks. You do not need to know
Kestra in depth, but you should be comfortable reading YAML and running a flow from the UI.

The approach is deliberately non-invasive: your inventory stays the source of truth and stays where
it is. Kestra reads it with `ansible-inventory`, so `group_vars`, `host_vars` and any dynamic
inventory plugin you already use are all applied before Kestra sees a single host. Nothing about
your existing playbooks changes.

Placeholders used throughout - replace with values for your environment:

| Placeholder | Meaning |
|---|---|
| `<KESTRA_BASE_URL>` | The base URL of your Kestra instance, e.g. `https://kestra.example.com` |
| `<NAMESPACE>` | The Kestra namespace you want these flows and assets to live in, e.g. `company.infra` |
| `<TENANT>` | Your Kestra tenant id, if your instance has tenants enabled |
| `<API_TOKEN>` | A Kestra API token for the account that will register assets |

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Decide what you want to slice the fleet by](#2-decide-what-you-want-to-slice-the-fleet-by)
3. [Register the inventory as assets](#3-register-the-inventory-as-assets)
4. [Keep it current](#4-keep-it-current)
5. [Build the fleet dashboard](#5-build-the-fleet-dashboard)
6. [Where to go next](#6-where-to-go-next)
7. [Troubleshooting / common pitfalls](#7-troubleshooting--common-pitfalls)

---

## 1. Prerequisites

- **Kestra Enterprise Edition.** Assets are an EE feature, available from 1.2 onwards.
- **Kestra 2.0.0 or later, if you want the dashboard.** Asset registration (sections 2 to 4) works
  on 1.2 and 1.3. Asset-backed *dashboard charts* were added in 2.0.0 and were not backported to
  the 1.3 line. On 1.3 you can still browse and filter everything from the built-in **Assets**
  page, but you cannot chart it.
- **The supplied flow is written for 2.0.** The loop task was renamed between the two lines, so the
  flow YAML is not portable as-is. If you are registering assets on 1.3, make these two changes:

  | | 1.2 / 1.3 | 2.0 |
  |---|---|---|
  | Loop task type | `io.kestra.plugin.core.flow.ForEach` | `io.kestra.plugin.core.flow.Loop` |
  | Iteration variable | `{{ taskrun.value }}` | `{{ item.value }}` |

  Using the 1.3 form on 2.0 fails at deploy time with
  `No plugin registered for the defined type: 'io.kestra.plugin.core.flow.ForEach'`.
- The `plugin-ansible` and `plugin-kestra` plugins installed on your instance. If you build a
  minimal image from the `-no-plugins` base, add them explicitly:
  ```dockerfile
  RUN /app/kestra plugins install io.kestra.plugin:plugin-ansible:LATEST
  RUN /app/kestra plugins install io.kestra.plugin:plugin-kestra:LATEST
  ```
- An API token for the account that will register assets, stored as a Kestra secret rather than
  written into the flow. Create the token under **Administration > Users > (your user) > API
  Tokens**, or over the API:
  ```bash
  curl -u '<USER>:<PASSWORD>' -X POST -H 'Content-Type: application/json' \
    -d '{"name":"assets-onboarding","description":"inventory sync"}' \
    '<KESTRA_BASE_URL>/api/v1/users/<USER_ID>/api-tokens'
  ```
  The response field `fullToken` is shown **once only**. Store it immediately as the secret
  `KESTRA_API_TOKEN` in the namespace the flow runs in (**Namespaces > (your namespace) >
  Secrets**).

## 2. Decide what you want to slice the fleet by

This is the only step that needs real thought, and it is worth doing before you write any YAML.

An asset in Kestra has a small set of core fields (`id`, `namespace`, `type`, `displayName`,
`description`) plus a free-form `metadata` map. Every question you want the dashboard to answer
has to correspond to a metadata key. You cannot group by something you did not store.

Kestra ships a `VM` asset type whose *typed* metadata fields are `provider`, `region` and `state`.
Use those three names for exactly those concepts, so the built-in Assets UI renders them properly.
Everything else you want is free-form and can be named whatever suits you.

A worked set of keys for the questions in the introduction:

| Metadata key | Example value | Answers |
|---|---|---|
| `provider` | `aws`, `azure`, `gcp`, `onprem` | Which cloud are we on |
| `region` | `eu-west-1`, `dc-frankfurt` | Where does it run |
| `state` | `running`, `stopped` | Is it live |
| `os` | `ubuntu 22.04` | Full OS mix |
| `os_family` | `ubuntu`, `rhel`, `windows` | Coarser OS mix |
| `patch_status` | `patched`, `pending`, `failed` | How many are unpatched |
| `cert_expiry` | `2026-10-05` | Raw expiry date, for display |
| `cert_status` | `ok`, `expiring_90d`, `expiring_30d`, `expired` | How many certs need attention |

Two decisions in that table are worth calling out, because they are the difference between a
dashboard that works and one that does not:

**Store both a raw value and a bucketed value for anything date-like.** `cert_expiry` is a date,
and a chart cannot group by a date that is different for every host - you would get one bar per
host. `cert_status` buckets the same information into four values, which is what actually makes a
readable chart. Compute the bucket when you write the asset, not when you read it.

**Store both `os` and `os_family`.** `os` gives you the detailed breakdown and `os_family` gives
you the three-or-four-way split for a summary chart. They cost nothing to store and you will want
both within a day of having the dashboard.

Where these values come from is up to you. In the example below they are host vars in the
inventory. In practice they will more likely come from a mix of host vars, `ansible_facts`
gathered by a playbook, and whatever your patch-management tooling already reports.

## 3. Register the inventory as assets

The flow is in [`flows/ansible_inventory_to_assets.yaml`](flows/ansible_inventory_to_assets.yaml).
It has two tasks.

**Task 1 resolves the inventory.** It runs `ansible-inventory --list`, which is the important
detail: you get the inventory *as Ansible sees it*, with all group vars, host vars and dynamic
inventory plugins already applied. A small Python step then reshapes it into a flat JSON array and
computes the derived fields from section 2.

Both files the task needs are supplied through `inputFiles`, which writes them into the task's
working directory before the commands run:

```yaml
  - id: resolve_inventory
    type: io.kestra.plugin.ansible.cli.AnsibleCLI
    containerImage: cytopia/ansible:latest-tools
    taskRunner:
      type: io.kestra.plugin.scripts.runner.docker.Docker
    outputFiles:
      - hosts.json
    inputFiles:
      inventory.yml: |
        all:
          children:
            linux:
              hosts:
                web-prd-01: {ansible_host: 10.0.1.11, os_family: ubuntu, os_version: "22.04", cloud: aws, region: eu-west-1, state: running, patch_status: patched, cert_expiry: "2026-12-20"}
                # ... the rest of your hosts
      to_assets.py: |
        # full script below
    commands:
      - ansible-inventory -i inventory.yml --list > raw.json && python3 to_assets.py
```

**Both steps must be a single `commands` entry.** `AnsibleCLI` runs each entry in its own
container with a fresh working-directory volume, so `raw.json` written by one entry does not exist
for the next one. Splitting them looks tidier and fails with `Captured 0 output file(s)` followed
by the task erroring, which is a confusing way to learn this. Chain them with `&&`.

### Supplying your real inventory

The example ships a small inventory inline so the flow is self-contained and runnable as-is. Do
not do that with a real inventory. Put `inventory.yml` and `to_assets.py` in a namespace file
directory, keep them in Git, and sync them into the namespace. Then replace the whole `inputFiles`
block with:

```yaml
    namespaceFiles:
      enabled: true
```

Namespace files land in the same working directory, so the two `commands` are unchanged. You get
version control and review on the inventory, which is what you want for something this load-bearing.

### The transform script

`to_assets.py` reads what `ansible-inventory` produced, flattens `_meta.hostvars` into one record
per host, and computes the derived fields from section 2. This is the piece you will actually edit,
because the metadata keys you chose determine what it emits.

```python
import json, datetime

raw = json.load(open("raw.json"))
hostvars = raw.get("_meta", {}).get("hostvars", {})
today = datetime.date.today()
out = []

for host, v in hostvars.items():
    expiry = v.get("cert_expiry")
    days = None
    bucket = "unknown"
    if expiry:
        days = (datetime.date.fromisoformat(expiry) - today).days
        if days < 0:
            bucket = "expired"
        elif days <= 30:
            bucket = "expiring_30d"
        elif days <= 90:
            bucket = "expiring_90d"
        else:
            bucket = "ok"
    out.append({
        "id": host,
        "ip": v.get("ansible_host"),
        "os_family": v.get("os_family"),
        "os_version": v.get("os_version"),
        "os": f'{v.get("os_family")} {v.get("os_version")}',
        "cloud": v.get("cloud"),
        "region": v.get("region"),
        "state": v.get("state"),
        "patch_status": v.get("patch_status"),
        "last_patched": v.get("last_patched"),
        "cert_expiry": expiry,
        "cert_days_remaining": days,
        "cert_status": bucket,
    })

json.dump(out, open("hosts.json", "w"))
print(f"prepared {len(out)} hosts")
```

Note the `bucket = "unknown"` default. A host with no `cert_expiry` set still produces a record,
and shows up in the certificate chart as `unknown` rather than vanishing from the fleet count.
Silently dropping hosts with incomplete data is the failure mode to avoid here: an inventory
dashboard that quietly undercounts is worse than one that shows you the gaps.

`hosts.json` is listed in `outputFiles`, which is what makes it readable by the next task.

**Task 2 registers one asset per host.** A `ForEach` walks the JSON array and upserts a `VM` asset
for each entry.

```yaml
  - id: register_assets
    type: io.kestra.plugin.core.flow.Loop
    values: "{{ read(outputs.resolve_inventory.outputFiles['hosts.json']) }}"
    tasks:
      - id: upsert
        type: io.kestra.plugin.kestra.ee.assets.Set
        kestraUrl: http://kestra-webserver:8080
        assetId: "{{ fromJson(item.value).id }}"
        assetType: io.kestra.plugin.ee.assets.VM
        namespace: <NAMESPACE>
        auth:
          apiToken: "{{ secret('KESTRA_API_TOKEN') }}"
        metadata:
          provider: "{{ fromJson(item.value).cloud }}"
          region: "{{ fromJson(item.value).region }}"
          state: "{{ fromJson(item.value).state }}"
          os: "{{ fromJson(item.value).os }}"
          patch_status: "{{ fromJson(item.value).patch_status }}"
          cert_expiry: "{{ fromJson(item.value).cert_expiry }}"
          cert_status: "{{ fromJson(item.value).cert_status }}"
```

**Set `kestraUrl` explicitly on any containerised deployment.** `Set` calls the Kestra API, and the
call is made from inside the worker container. Left unset it falls back to `kestra.url` from your
configuration, which is the browser-facing URL (`https://kestra.example.com`, or worse
`http://localhost:8082`) and is usually not reachable from the worker. The failure is
`Connect to http://localhost:8082 failed: Connection refused`. Use the internal service address
instead, for example `http://kestra-webserver:8080` on Docker Compose or the Kubernetes Service
DNS name.

Three things to know about `Set`:

- It is an **upsert** keyed on `assetId`. Re-running refreshes metadata in place rather than
  creating duplicates, which is what makes section 4 safe.
- An asset id is **unique per tenant**, and neither namespace nor type is part of that identity.
  Two assets cannot share an id in one tenant even if their namespaces differ. Use your hostname
  or an inventory-stable id, and prefix it if hostnames might collide across environments.
- The `namespace` you give the asset controls RBAC visibility, so use it to scope who can see
  which slice of the fleet.

Run the flow once from the UI, then open the **Assets** page. You should see one `VM` asset per
host in your inventory, each carrying the metadata from section 2.

Two notes on reading the run:

- On 2.0, `Loop` runs each iteration as a **sub-execution**, not as an inline task run. A failure
  in the parent shows only `Loop iteration N ended in FAILED in sub-execution [...]`. The real
  error is in the linked child execution's logs, so follow the link rather than hunting in the
  parent.
- Numeric metadata survives as numbers. `cert_days_remaining` arrives as `166`, not `"166"`, so
  numeric comparisons in chart filters behave as you would expect.

## 4. Keep it current

An inventory snapshot that is a week old is worse than no inventory, because people trust it.
Add a schedule so the assets refresh on their own:

```yaml
triggers:
  - id: nightly
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "0 6 * * *"
```

Because `Set` is an upsert, a scheduled re-run simply refreshes metadata on the existing assets.
Hosts removed from the inventory are not deleted automatically - if you want that, add a reconcile
step using `io.kestra.plugin.kestra.ee.assets.List` and `Delete`.

### Acting on staleness: `FreshnessTrigger`

Once the sync runs on a schedule, an asset's *last updated* timestamp becomes a liveness signal.
Every host still in the inventory gets its metadata refreshed on each run, so any asset that stops
being refreshed has dropped out of the inventory. `FreshnessTrigger` turns that into an event you
can act on:

```yaml
triggers:
  - id: host_went_stale
    type: io.kestra.plugin.kestra.ee.assets.FreshnessTrigger
    assetType: io.kestra.plugin.ee.assets.VM
    namespace: <NAMESPACE>
    maxStaleness: PT26H      # nightly sync + 2h grace
    interval: PT1H           # how often to check
    kestraUrl: http://kestra-webserver:8080
    auth:
      apiToken: "{{ secret('KESTRA_API_TOKEN') }}"

tasks:
  - id: decommission
    type: io.kestra.plugin.core.flow.Subflow
    namespace: <NAMESPACE>
    flowId: host_decommission
    inputs:
      host: "{{ trigger.assets[0].id }}"
      last_seen: "{{ trigger.assets[0].lastUpdated }}"
```

The trigger context gives you `trigger.assets` with `id` and `lastUpdated`, so the downstream flow
knows which host and how long it has been gone. Typical downstream actions: revoke monitoring and
backup jobs, release the licence or IP reservation, open a decommission ticket, remove DNS, then
`io.kestra.plugin.kestra.ee.assets.Delete` the asset itself so it stops re-firing.

Filter with `metadataQuery` if you want different handling per slice of the fleet, for example
alerting on stale production hosts but auto-decommissioning stale lab hosts.

:::alert{type="warning"}
**Guard any destructive downstream action against a sync outage.** Staleness means "the sync flow
stopped updating this asset", which is not the same as "this host is gone". If the sync flow itself
breaks, or someone points it at an empty inventory, *every* asset goes stale at once and a naive
decommission automation will happily tear down the entire fleet.

Put a circuit breaker in front of anything destructive. The cheap version is a count check at the
top of the decommission flow: if more than a handful of hosts went stale in the same window, stop
and page a human instead. Set `maxStaleness` to comfortably more than one sync interval so a single
missed run does not trip it, and consider having the decommission flow open a ticket for approval
rather than acting directly until you trust the signal.
:::

Two smaller notes: set `maxStaleness` relative to your sync schedule (a nightly sync wants at least
`PT26H`, not `PT24H`, or normal jitter will trip it), and set `kestraUrl` here for the same reason
as in section 3, since the trigger also calls the Kestra API. The plugin's bundled example shows a
`checkInterval` property, which does not exist; the real property name is `interval`.

## 5. Build the fleet dashboard

**Requires Kestra 2.0.0 or later.** See section 1.

The dashboard is in [`dashboards/vm_fleet_inventory.yaml`](dashboards/vm_fleet_inventory.yaml).
Create it from **Dashboards > Create**, paste the YAML, and save.

Every chart follows the same shape: pick a metadata key as the grouping column, count, and filter
to VM assets.

```yaml
  - id: patch_status
    type: io.kestra.plugin.core.dashboard.chart.Bar
    chartOptions:
      displayName: Patch status
      column: patch_status
      width: 6
    data:
      type: io.kestra.plugin.ee.dashboard.data.Assets
      columns:
        patch_status:
          field: METADATA
          key: patch_status
          displayName: Patch status
        total:
          agg: COUNT
          displayName: VMs
      where:
        - field: TYPE
          type: EQUAL_TO
          value: io.kestra.plugin.ee.assets.VM
```

The supplied dashboard has five charts:

| Chart | Type | Shows |
|---|---|---|
| Patch status | Bar | `patched` / `pending` / `failed` counts |
| Certificate expiry | Bar | `ok` / `expiring_90d` / `expiring_30d` / `expired` counts |
| OS distribution | Pie (donut) | Full OS mix |
| Cloud provider | Pie (donut) | Fleet split across clouds and on-prem |
| Certificates expiring within 30 days | Table | The actionable list, filtered with `IN` on `cert_status` |

The last one is the pattern worth copying. Charts that count are useful for reporting; a table
filtered to the rows that need action is what someone actually works from:

```yaml
      where:
        - field: TYPE
          type: EQUAL_TO
          value: io.kestra.plugin.ee.assets.VM
        - field: METADATA
          key: cert_status
          type: IN
          values:
            - expired
            - expiring_30d
```

One behaviour to be aware of: **asset charts ignore the dashboard time range.** They always show
current inventory rather than a window. That is usually what you want for an inventory, but it
means the time-range selector at the top of the dashboard has no effect on these charts.

## 6. Where to go next

Once the inventory is in Kestra as assets, a few things become available that are hard to do with
a flat inventory file:

- **Populate flow inputs from live inventory.** A `SELECT` input can be driven by the `assets()`
  Pebble function, so an operator running a patching playbook picks from the actual fleet rather
  than typing a hostname.
- **Lineage.** Setting `assets: enableAuto: true` on an `AnsibleCLI` task registers the inventory
  hosts a playbook targeted as input assets. That gives you "which playbooks touched this host"
  for free. Note it records the relationship only, with no metadata, so it complements the flow in
  section 3 rather than replacing it.
- **Event-driven automation.** `EventTrigger` fires on asset `CREATED` / `UPDATED` / `DELETED` /
  `USED` events and can be scoped by type, namespace and metadata, so "a host moved to
  `patch_status: failed`" can launch a remediation flow.

## 7. Troubleshooting / common pitfalls

**`colorByColumn` is rejected on a Bar chart.** It is valid on `Pie` but not on `Bar`. A Bar chart
accepts only `tooltip`, `width`, `description`, `displayName`, `column` and `legend`. The error is
explicit about it:
```
Unrecognized field "colorByColumn" (class io.kestra.plugin.core.dashboard.chart.bars.BarOption),
not marked as ignorable (6 known properties: "tooltip", "width", "description", "displayName",
"column", "legend")
```

**A table column is silently missing.** If a metadata key does not exist on the assets, the column
is quietly omitted from the results rather than erroring. A typo in a metadata key therefore
produces an incomplete table, not a visible failure. Check the key name against the Assets page.

**A chart produces one bar per host.** You are grouping by a value that is unique per host, such
as a raw date or an IP. Add a bucketed metadata key as described in section 2.

**The dashboard will not save at all, with a `dataFilterClass is null` error.** Your instance is
older than 2.0.0 and does not have the asset dashboard data source. Asset registration still works
- use the Assets page instead of a dashboard, and see section 1.

**Assets are registered but all metadata is empty.** Check that the host vars actually reached
Ansible. Run the first task alone and inspect `hosts.json` in the task outputs before blaming the
registration step.

**Duplicate assets after a rename.** Asset identity is the id, so renaming a host in your inventory
creates a new asset rather than renaming the existing one. The old one stays until you delete it.
If hostnames churn, key `assetId` on something stable instead.

**`No plugin registered for the defined type: 'io.kestra.plugin.core.flow.ForEach'`.** You are
deploying the 1.3 form of the flow to a 2.0 instance. See the version table in section 1.

**`Captured 0 output file(s)` and the first task fails.** Your `ansible-inventory` and `python3`
steps are separate `commands` entries. Chain them into one with `&&`; see section 3.

**`Connect to http://localhost:... failed: Connection refused` on the upsert task.** `kestraUrl` is
unset or points at a browser-facing URL. See section 3.

**`Execution was killed during image pull`.** The worker is trying to pull `cytopia/ansible` and
cannot reach the registry. Pre-pull the image on your worker hosts and set
`pullPolicy: IF_NOT_PRESENT` on the task runner, which is what the supplied flow does. Relevant to
anyone running with restricted egress.
