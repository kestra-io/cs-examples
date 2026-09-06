# Kestra Monitoring: Prometheus + Grafana

Local monitoring stack for the Kestra instance in this project, wired into the root
`docker-compose.yml`. No changes were made to the Kestra service itself, it already
exposes Prometheus-formatted metrics at `:8081/prometheus` by default.

Purpose: give administrators enough signal to answer "do we need to scale, and which
lever (worker threads, worker replicas, or the DB connection pool) actually fixes it."

## What's running

| Service | Image | Port | Purpose |
|---|---|---|---|
| `prometheus` | `prom/prometheus:latest` | `9090` | Scrapes Kestra's `/prometheus` endpoint every 15s |
| `grafana` | `grafana/grafana-enterprise:latest` | `3000` | Dashboards + alerting, reading from Prometheus |

```bash
docker compose up -d prometheus grafana
```

## Files

```
monitoring/
├── prometheus/
│   └── prometheus.yml                        # scrape config
├── grafana/
│   └── provisioning/
│       ├── datasources/datasource.yml         # Prometheus datasource
│       ├── dashboards/
│       │   ├── dashboard.yml                  # loads dashboards from ./json
│       │   └── json/kestra-overview.json      # "Kestra Overview" dashboard
│       └── alerting/
│           ├── contactpoints.yaml             # Slack + Kestra webhook receivers
│           ├── notification-policies.yaml     # routes all alerts to the contact point
│           ├── rules.yaml                     # 6 alert rules
│           └── templates.yaml                 # readable notification text
└── flows/
    ├── fire_all_alerts.yaml       # synthetic load test (deploy manually, see below)
    └── grafana_alert_webhook.yaml # receives alerts via webhook, logs them (deploy manually)
```

Also: root-level `.env` holds `SLACK_WEBHOOK_URL`, passed through to the `grafana`
service in `docker-compose.yml` via `SLACK_WEBHOOK_URL: ${SLACK_WEBHOOK_URL}`.

## Access

| What | URL | Credentials |
|---|---|---|
| Grafana | http://localhost:3000 | `admin` / `Kestra1!` |
| Prometheus | http://localhost:9090 | none |
| Raw Kestra metrics | http://localhost:8081/prometheus | none |

Dashboard: **Kestra** folder → **Kestra Overview** (22 panels).

`prometheus.yml` scrapes both Kestra nodes over the compose network: `kestra:8081`
(labeled `kestra-standalone`) and `kestra-worker-wg1:8081` (labeled `kestra-worker-wg1`).
If `kestra-worker-wg1` isn't running, its target shows `down`, expected, not an error.

## How it fits together

Every capacity concern is wired the same way, one metric, in three places, all agreeing:

```
Prometheus metric  →  Dashboard panel (threshold line)  →  Alert rule (same threshold)  →  Slack + Kestra webhook flow
```

The dashboard panel and the alert rule always use the identical PromQL expression and
threshold value, so what the graph shows as "red" is exactly what fires the alert.

| Panel / Rule | Metric | Yellow | Red (fires) | Action |
|---|---|---|---|---|
| Worker Thread Pool Utilization | `running/threads`, per instance | 80% | 95% | Add worker threads or replicas |
| DB Pool Utilization | `hikaricp_connections_active/max` | 80% | 95% | Raise `maximum-pool-size` |
| DB Pool Pending Connections | `hikaricp_connections_pending` | n/a | 1 | Raise `maximum-pool-size` |
| DB Connection Acquire Time | `hikaricp_connections_acquire_seconds` | 50ms | 500ms | Early warning before pool exhaustion |
| JVM Heap Utilization | `jvm_memory_used/max_bytes` (heap) | 70% | 90% | Increase container/heap memory |
| Task Queued Time | `kestra_worker_queued_duration_seconds` | 1s | 5s | Add worker threads or replicas |

All 6 rules (`rules.yaml`) route through one notification policy to one contact point
(`slack-kestra-alerts`), which fans out to two receivers: Slack, and a webhook that
triggers `grafana_alert_webhook` in Kestra (currently just logs the payload).

These 6 panels are positioned at the top of the dashboard, directly under the stat row,
since they're the ones that call for action. The remaining panels (execution/queue
throughput, scheduler health, JDBC latency, etc.) have no fixed threshold: what counts
as "normal" is workload-dependent, add thresholds once you know your own baseline.

## Dashboard panels

- **Worker thread saturation**: Jobs Running/Pending/Threads, Utilization % (per
  instance), Tasks Started vs Ended (rate), Avg Task Duration, Task Queued Time (avg/max,
  the direct measurement of wait time, not an inferred proxy)
- **DB / connection pool**: Pool Utilization, Pending Connections, Acquire Time, JDBC
  Query Duration, often the real bottleneck in a JDBC-backed deployment
- **Scheduler health**: Evaluate/Loop Rate, Trigger Evaluation Duration, Evaluation Loop
  Duration, a distinct axis from worker/DB capacity
- **Execution / queue throughput**: Executions Started vs Ended, Avg Execution Duration,
  Queue Poll Size/Produce Rate/Receive Duration, Executor Thread Count
- **Host / API**: JVM Heap Utilization %, HTTP Server Request Rate (excl. health/metrics)

Every panel has a hover tooltip (ⓘ icon) explaining what it shows and what to do about it.

**Populates only once a flow runs** (Micrometer counters register lazily): the
rate/duration panels for worker tasks, executions, scheduler evaluation, queue
produce/receive, JDBC queries, Task Queued Time, DB acquire time. Everything else
(gauges: Jobs Running/Pending/Threads, Utilization %, Queue Poll Size, JVM Heap) is live
immediately, including at idle.

## Alerting setup

1. Create a Slack Incoming Webhook at https://api.slack.com/messaging/webhooks.
2. Paste the URL into `SLACK_WEBHOOK_URL=` in the root `.env`.
3. Recreate Grafana so it picks up the env var (file provisioning reloads live, but env
   vars are set at container start): `docker compose up -d grafana`.

`contactpoints.yaml` references it via `$__env{SLACK_WEBHOOK_URL}`, the raw URL only
ever lives in `.env` (gitignore it) and Grafana's internal storage.

**Test without waiting for a real breach**, via Grafana's receiver-test API (the URL
path segment is the unpadded base64 of the *receiver name*, not the integration `uid`):

```bash
RECEIVER_B64=$(echo -n "slack-kestra-alerts" | base64 | tr -d '=')
curl -s -X POST -u 'admin:Kestra1!' \
  "http://localhost:3000/apis/notifications.alerting.grafana.app/v0alpha1/namespaces/default/receivers/${RECEIVER_B64}/test" \
  -H "Content-Type: application/json" -H "x-grafana-org-id: 1" \
  --data-raw '{"integration":{"uid":"slack-kestra-webhook","type":"slack","version":"v1","settings":{"title":"{{ template \"kestra_alert_title\" . }}","text":"{{ template \"kestra_alert_message\" . }}"},"secureFields":{"url":true},"disableResolveMessage":false},"alert":{"labels":{"alertname":"test","instance":"kestra-standalone","threshold":"5","unit":"s"},"annotations":{"summary":"test summary","description":"test action"}}}'
```

Important: this API only renders whatever fields you pass in `settings` for that one
call, it does not read the receiver's actual stored config. Omit `title`/`text` here and
it silently falls back to Grafana's plain default template, which looks like your real
config is broken even though it's fine. Always include every overridden field.

### Notification text (`templates.yaml`)

Grafana's default message is `Value: A=100, B=100, C=1`, meaningless without knowing the
rule's internal query→reduce→threshold pipeline. Two custom templates replace it:

- `kestra_alert_title`: `FIRING: <alertname> (<instance>)`
- `kestra_alert_message`: the rule's own `summary` annotation, then
  `Current value: X (threshold: Y)`, then the `description` annotation as the action

```
FIRING: Kestra: Worker Thread Pool Utilization High (kestra-standalone)

Worker thread pool utilization has been above 95% for 5+ minutes on at least one instance.
Current value: 100.0% (threshold: 95%)

Action: Add more worker threads or worker replicas to the affected instance.
```

Wired into both receivers: Slack's `settings.title`/`text`, the Kestra webhook's
`settings.title`/`message`.

Two things make the value/threshold comparison possible:
- Every rule carries `threshold`/`unit` labels (e.g. `threshold: "95"`, `unit: "%"`),
  Grafana doesn't expose a rule's own threshold condition as a template variable, so
  it's set explicitly (duplicating the number already in `conditions[].evaluator.params`).
- `.Values` (the `A`/`B`/`C` pipeline values) is only populated on a real firing, a
  manual test notification renders `0.0` there, expected, not a bug.

**If you add more rule labels later**: check the whole rendered notification, not just
the piece you're changing. A label added for the message body can silently leak into
Grafana's *other* default templates (title, grouping) that you haven't overridden yet.

## Triggering a Kestra flow from an alert

All 6 rules also trigger `grafana_alert_webhook` (`solutions.alerting` namespace, deploy
manually the same way as `fire_all_alerts.yaml`) via a second receiver on the same
contact point, no separate notification policy needed. It currently just logs the
payload, a starting point for real remediation (branch on
`trigger.body.alerts[0].labels.alertname`).

Webhook URL format for this multi-tenant EE instance:
```
/api/v1/{tenant}/executions/webhook/{namespace}/{flowId}/{key}
```
e.g. `http://kestra:8080/api/v1/solutions/executions/webhook/solutions.alerting/grafana_alert_webhook/<key>`
(what Grafana uses, over the compose network) or `http://localhost:8080/...` from the
host. Confirmed no authentication needed, secured by the secret `key` in the path only.

## Load-testing the alerts

`monitoring/flows/fire_all_alerts.yaml` (deploy manually) dispatches ~600 `Sleep` tasks
across parallel `ForEach` branches with randomized durations, to saturate worker threads
and force a real backlog so the alerts can be verified against genuine metric breaches.

**Running it blocks the instance**, nothing else can run while it saturates worker
threads. Confirm with whoever owns the instance first.

Sizing notes:
- Size the task count comfortably above the *reachable* worker thread count, `kestra_worker_job_thread` sums across **all** workers, including any idle worker-group
  that your flow's tasks can't actually reach (see the `by (instance)` note below).
- Randomize each task's duration (`duration: "PT{{ randomInt(300, 600) }}S"`), not
  identical durations, or every task completes in the same instant and "100%
  utilization" only lasts as long as one shared duration, likely too short to clear the
  alert's `for` window.

**Why the alert rules and the Utilization panel evaluate `by (instance)`, not a global
`sum()`**: with more than one worker present, summing `running`/`threads` across all of
them dilutes real saturation on one worker by however much idle capacity another worker
contributes, genuine 100% saturation of the only reachable worker can read as 50%
system-wide and never cross the alert threshold. Evaluating per-instance means one
worker's saturation is judged on its own, unaffected by a sibling sitting idle.

Confirmed end-to-end: all 6 alerts wired to Slack + the Kestra webhook flow, with real
firings observed for Worker Thread Pool Utilization and Task Queued Time (the two this
test can actually reach), including correct fire → resolve lifecycle and the `instance`
label surfacing directly in the Slack title. DB Pool and JVM Heap rules are not expected
to fire from this test, flagged from the start as side-effect-only or not attempted
(forcing real heap exhaustion risks destabilizing the instance).

## Operational notes

- **`color.mode: "thresholds"` breaks multi-series panels.** It colors each series by its
  *own* value, not a fixed per-series color, two series in the same threshold band render
  identically and look like one broken line. Use `"palette-classic"` for any panel with
  more than one target; keep `"thresholds"` only for single-series panels (lets the line
  itself recolor at the boundary).
- **Hard `min`/`max` clips real data.** Fine for percent panels (can't legitimately exceed
  100). For unbounded metrics (Pending Connections, Acquire Time, Task Queued Time), use
  `custom.axisSoftMin`/`axisSoftMax` instead, guarantees the threshold line is visible at
  idle, but still auto-expands if real data spikes higher.
- **`rate()` needs a metric to change value between two scrapes.** The first time a given
  label combination (e.g. one `flow_id`) is ever scraped, it's already at its incremented
  value, no captured "0 → 1" transition, so `rate()` reads `0` no matter how long you
  wait. Trigger the same flow twice to see rate-based panels populate. To sanity-check a
  single run, query the raw counter instead:
  `curl -s "http://localhost:9090/api/v1/query?query=sum(kestra_worker_started_count_total)"`.

## Considered, not added

- Host-level: `system_cpu_usage`, `system_load_average_1m`, `jvm_gc_pause_seconds`,
  `process_cpu_usage`
- Worker retry rate: `kestra_worker_retried_count_total`
- Per-flow/per-task-type breakdown (`by (namespace_id, flow_id, task_type)`): labels exist
  and were confirmed live, left out to avoid an ever-growing legend as flows are added

## Extending

- **Add a scrape target**: new entry under `static_configs.targets` in `prometheus.yml`.
- **Add a panel**: edit `kestra-overview.json` (include a `description` for the tooltip),
  or build in the Grafana UI and export back. Force a reload:
  `curl -X POST -u admin:Kestra1! http://localhost:3000/api/admin/provisioning/dashboards/reload`
- **Add a threshold line**: `fieldConfig.defaults.custom.thresholdsStyle: {mode: "dashed"}`
  plus a `thresholds.steps` array. See panels 14, 17, 18, 19, 20, 22 in
  `kestra-overview.json` for working examples.
- **Full metric reference**: https://kestra.io/docs/administrator-guide/monitoring
