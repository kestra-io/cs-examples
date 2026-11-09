"""Writes one catalog App per user-facing flow of solutions.kestra4infra (python3 scripts/gen_apps.py)."""
from pathlib import Path

NS = "solutions.kestra4infra"
HERE = Path(__file__).parent.parent / "apps"

# id, flowId, title, button, tags, intro, running, success_blocks
APPS = [
    ("k4i-provision-deployment", "provision_deployment", "Request an application deployment", "Provision",
     ["kestra4infra", "provisioning"],
     "Servers, VLAN, security group, firewall rule, service account, DNS, TLS certificate, application and\n"
     "health check, built in one request and recorded as one deployment with a lease.\n\n"
     "Every resource lands in the inventory with its owner, its expiry dates and its day-2 actions.\n\n"
     "_Demo environment: only the certificate is really issued, the other steps are simulated._",
     "Building your deployment, step by step:",
     [("Logs", {"taskIds": ["finalize"]}), ("Assets", None)]),

    ("k4i-blast-radius", "blast_radius", "Blast radius of an asset", "Analyse",
     ["kestra4infra", "risk"],
     "What breaks if this asset breaks, which deployments and teams are hit, and what the asset depends on.\n\n"
     "Read from the dependency graph the provisioning tasks recorded. Try the issuing CA or the core switch.",
     "Walking the dependency graph:",
     [("Logs", {"taskIds": ["report"]}), ("Outputs", None)]),

    ("k4i-renew-certificate", "renew_certificate", "Renew a TLS certificate", "Renew",
     ["kestra4infra", "day-2", "security"],
     "Re-issues the certificate, pushes it to its application and checks the application still answers.\n\n"
     "Also runs on its own 15 days before expiry (`cert_expiry_autorenew`).",
     "Renewing:",
     [("Logs", {"taskIds": ["issue_certificate", "record_certificate"]}), ("Assets", ["kestra4infra.Certificate"])]),

    ("k4i-rotate-service-account", "rotate_service_account", "Rotate a service account password", "Rotate",
     ["kestra4infra", "day-2", "security"],
     "Sets a new password, stores it in Vault and restarts the application that runs as the account.\n\n"
     "Also runs on its own 7 days before the password expires (`service_account_autorotate`).",
     "Rotating:",
     [("Logs", {"taskIds": ["rotate", "restart_application"]}), ("Assets", ["kestra4infra.ServiceAccount"])]),

    ("k4i-resize-vm", "resize_vm", "Resize a server", "Resize",
     ["kestra4infra", "day-2", "compute"],
     "Changes CPU and memory through Terraform. Check the server's blast radius first: the application on it restarts.",
     "Resizing:",
     [("Assets", ["io.kestra.plugin.ee.assets.VM"])]),

    ("k4i-reapply-configuration", "reapply_configuration", "Re-apply the server baseline", "Run",
     ["kestra4infra", "day-2", "compliance"],
     "Runs the CIS RHEL 9 baseline playbook on a server again, or in check mode to report drift only.",
     "Running the playbook:",
     [("Logs", {"taskIds": ["playbook"]}), ("Assets", ["io.kestra.plugin.ee.assets.VM"])]),

    ("k4i-run-health-check", "run_health_check", "Check an application", "Check",
     ["kestra4infra", "day-2", "operations"],
     "Calls the application's health endpoint and records the result.\n\n"
     "_Demo environment: pick the result. `degraded` opens an incident with its blast radius on its own._",
     "Checking:",
     [("Logs", {"taskIds": ["check"]}), ("Assets", ["kestra4infra.HealthCheck"])]),

    ("k4i-extend-lease", "extend_lease", "Extend a deployment lease", "Extend",
     ["kestra4infra", "day-2", "governance"],
     "Pushes the deployment's expiry further and lifts an overdue flag. The service account's expiry follows.",
     "Extending:",
     [("Assets", ["io.kestra.plugin.ee.assets.Deployment"])]),

    ("k4i-decommission-deployment", "decommission_deployment", "Decommission a deployment", "Decommission",
     ["kestra4infra", "retirement"],
     "Removes every resource of the deployment, last built first: health check, certificate, DNS, application,\n"
     "servers, account, firewall rule, security group, VLAN. Shared infrastructure is left alone.",
     "Tearing down in reverse dependency order:",
     [("Assets", None)]),

    ("k4i-setup-shared-infra", "setup_shared_infra", "Register the shared infrastructure", "Register",
     ["kestra4infra", "admin"],
     "Records the core switch, edge firewall, DNS zone, AD domain, issuing CA and CIS baseline every deployment\n"
     "builds on. Run once before the first deployment; running it again is safe.",
     "Registering:",
     [("Assets", None)]),
]


def indent(text, n):
    pad = " " * n
    return "\n".join(pad + line if line else "" for line in text.splitlines())


def block(kind, arg):
    if kind == "Logs":
        ids = "\n".join(f"            - {t}" for t in arg["taskIds"])
        return f"      - type: io.kestra.plugin.ee.apps.execution.blocks.Logs\n        filter:\n          taskIds:\n{ids}\n"
    if kind == "Outputs":
        return "      - type: io.kestra.plugin.ee.apps.execution.blocks.Outputs\n"
    if kind == "Assets":
        if not arg:
            return "      - type: io.kestra.plugin.ee.apps.execution.blocks.Assets\n"
        inc = "\n".join(f"            - {t}" for t in arg)
        return f"      - type: io.kestra.plugin.ee.apps.execution.blocks.Assets\n        filter:\n          include:\n{inc}\n"
    raise ValueError(kind)


for app_id, flow, title, button, tags, intro, running, success in APPS:
    tag_lines = "\n".join(f"  - {t}" for t in tags)
    success_blocks = "".join(block(k, a) for k, a in success)
    src = f"""id: {app_id}
namespace: {NS}
type: io.kestra.plugin.ee.apps.Execution
flowId: {flow}

displayName: {title}
description: "{intro.splitlines()[0].replace(chr(34), chr(39))}"
tags:
{tag_lines}

access:
  type: PRIVATE
  catalog: true

layout:
  - on: OPEN
    blocks:
      - type: io.kestra.plugin.ee.apps.core.blocks.Markdown
        content: |
          ## {title}

{indent(intro, 10)}

      - type: io.kestra.plugin.ee.apps.execution.blocks.CreateExecutionForm

      - type: io.kestra.plugin.ee.apps.execution.blocks.CreateExecutionButton
        text: {button}
        style: INFO

  - on: RUNNING
    blocks:
      - type: io.kestra.plugin.ee.apps.core.blocks.Markdown
        content: |
          ## {running}

      - type: io.kestra.plugin.ee.apps.execution.blocks.Gantt

  - on: SUCCESS
    blocks:
      - type: io.kestra.plugin.ee.apps.core.blocks.Markdown
        content: |
          ## Done

{success_blocks}
  - on: FAILURE
    blocks:
      - type: io.kestra.plugin.ee.apps.core.blocks.Markdown
        content: |
          ## {title}: failed

      - type: io.kestra.plugin.ee.apps.core.blocks.Stacktrace

      - type: io.kestra.plugin.ee.apps.execution.blocks.Logs
        filter:
          logLevel: ERROR
"""
    (HERE / f"{flow}.yaml").write_text(src)
    print("wrote", HERE / f"{flow}.yaml")
