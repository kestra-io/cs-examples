# Kestra <> GitHub Integration

[![Github integration Loom overview](../../images/loom-01.png)](https://www.loom.com/share/77c8f527ee7741b09990e7d824e1fcbc)

This solution demonstrates how to integrate Kestra with GitHub. This includes:
- Sourcing scripts from a GitHub repository.
- Committing Kestra Flows in a GitHub repository for version control and collaboration.
- Synchronizing using GitHub Actions.
- Promoting Kestra Flows to Production from a Github Pull Request.

<br/>

**Instructional videos:**
- [1/4 - GitHub Integration Overview](https://www.loom.com/share/77c8f527ee7741b09990e7d824e1fcbc)
- [2/4 - Sourcing Scripts from GitHub](https://www.loom.com/share/df9ff0911a2d474e948af475e3529d31)
- [3/4 - Committing Kestra Flows to GitHub](https://www.loom.com/share/8bdbaa13e54a47cfa2efa0d81f73a216)
- [4/4 - Promoting to Production from PRs](https://www.loom.com/share/a352bc37465e4b689b7701be7c1ec2cc)

<br/>

### Prerequisites
- A Publicly accessible Kestra instance with a URL that can be reached by GitHub Actions.
- A GitHub repository to store Kestra Flows and scripts.
- A GitHub Personal Access Token (PAT) with appropriate permissions to access the repository.

## Overview

![Github Integration Diagram](./imgs/git-int-overview.png)

The integration consists of the following sections:

A. **Sourcing Scripts from GitHub**: how to source scripts stored in a GitHub repository and use them in Kestra Flows.
B. **Committing Kestra Flows to GitHub**: how to commit Kestra Flows to a GitHub repository for version control (ie: `dev` branch).
C. **Promoting to Production from PRs**: how to use GitHub Actions to synchronize Kestra Flows between branches (e.g., from `dev` to `main`) and promote them to Production.

<br/><br/><br/>

## A. Sourcing Scripts from GitHub

[![Scenario 1](./imgs/loom-02.png)](https://www.loom.com/share/df9ff0911a2d474e948af475e3529d31)

Architecture:

<img src="./imgs/git-int-01.png" alt="Sourcing Scripts from GitHub Diagram" style="max-width:760px;"/>

Synchronize external scripts (Python, Bash) developed in IDEs like VS Code with Kestra. There are two primary architectural patterns:

<br/>

### 1. Single Flow Integration (Git Clone)

Best for scripts dedicated to a specific workflow.

* **Logic**: Uses a temporary working directory to pull code during execution.
* **Method**: Combine `io.kestra.plugin.core.flow.WorkingDirectory` with `io.kestra.plugin.git.Clone`.
* **Workflow**:
1. Define `WorkingDirectory` task.
2. Add `Clone` task to pull the repository into that directory.
3. Subsequent tasks reference files locally (e.g., `./scripts/my_script.py`).


```yaml
id: github_demo_with_gitclone
tasks:
  - id: my_working_dir
    type: io.kestra.plugin.core.flow.WorkingDirectory
    tasks:
      - id: clone_git
        type: io.kestra.plugin.git.Clone
        url: "https://github.com/your-repo.git"
        branch: "kestra"
      - id: python_task
        type: io.kestra.plugin.scripts.python.Commands
        commands:
          - python3 path/to/script.py

```

For complete example, see: **[`github_demo_with_gitclone.yaml`](./flows/github_demo_with_gitclone.yml)**

<br/>

### 2. Multi-Flow Integration (Namespace Files)

Best for shared scripts used by multiple flows within a namespace.

* **Logic**: Syncs GitHub files to Kestra **Namespace Files** persistent storage.
* **Method**: Use `io.kestra.plugin.git.SyncNamespaceFiles` (OSS) or `io.kestra.plugin.git.NamespaceSync` (EE).
* **Automation**: Use a GitHub Action to trigger a "System" sync flow via Webhook on every push.

#### The Sync Flow (System Namespace)

Create an administrative flow to handle the synchronization.

```yaml
id: github_sys_sync_namespacefiles
namespace: system
triggers:
  - id: on_webhook
    type: io.kestra.plugin.core.trigger.Webhook
    key: "{{secret('YOUR_WEBHOOK_TOKEN')}}"
tasks:
  - id: sync_namespace_files
    type: io.kestra.plugin.git.SyncNamespaceFiles
    url: "https://github.com/your-repo.git"
    gitDirectory: "scripts/path"
    namespace: "your.target.namespace"
```

For complete example, see: **[`github_sys_sync_namespacefiles.yaml`](./flows/github_sys_sync_namespacefiles.yml)**

#### The GitHub Action

Automate the sync whenever code changes in GitHub.

```yaml
name: sync_kestra_namespace_files
on:
  push:
    branches: [kestra]
jobs:
  trigger-kestra:
    runs-on: ubuntu-latest
    steps:
      - name: send_kestra_webhook
        run: |
          curl -X POST "https://<your-kestra-url>/api/v1/<tenant-id>/executions/webhook/system/github_sys_sync_namespacefiles/${{ secrets.KESTRA_WEBHOOK_KEY }}"
```

For complete example, see: **[`./github_actions/kestra-namespace-files-sync.yml`](./github_actions/kestra-namespace-files-sync.yml)**

#### Consuming Files in Flows

In your functional flows, enable `namespaceFiles` to access the synced scripts.

```yaml
tasks:
  - id: python_task
    type: io.kestra.plugin.scripts.python.Commands
    namespaceFiles:
        enabled: true
        include:
            - pre-process/pre_process.py
    commands:
      - python3 pre-process/pre_process.py

```

For complete example, see: **[`github_demo_with_namespacefiles.yaml`](./flows/github_demo_with_namespacefiles.yml)**

<br/><br/><br/>

## B. Committing Kestra Flows to GitHub

[![Scenario 2](./imgs/loom-03.png)](https://www.loom.com/share/8bdbaa13e54a47cfa2efa0d81f73a216)

Architecture:

<img src="./imgs/git-int-02.png" alt="Committing Kestra Flows to GitHub Diagram" style="max-width:760px;"/>


Backup and version control your Kestra Flow YAML definitions by automatically pushing them to a GitHub repository.

**Benefits**:
- **Source of Truth**: Maintain a "digital twin" of your Kestra environment in Git.
- **Version History**: While Kestra tracks internal revisions, pushing to GitHub enables standard Git-based collaboration and auditing.

### Implementation

There are two primary methods to push flows from Kestra to Git:

1. **PushFlows Plugin (OSS)**: Specifically designed to push Kestra Flow YAMLs to a target Git directory.
2. **NamespaceSync Plugin (EE)**: An Enterprise-tier plugin that synchronizes both Flows and Namespace Files simultaneously.

### The Push Flow (System Namespace)

Define an administrative flow in the `system` namespace to manage the backup.

```yaml
id: github_sys_push_flows_to_git
namespace: system
tasks:
  - id: push_flows
    type: io.kestra.plugin.git.PushFlows
    url: "https://github.com/your-repo.git"
    username: your_username
    password: "{{ secret('github_token') }}" # Use a GitHub PAT
    gitDirectory: "kestra/flows"
    sourceNamespace: "solutions.github_integration"
    branch: "kestra"

triggers:   
  - id: on_15min_interval
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "*/15 * * * *"

  - id: on_flow_execution_in_namespace
    type: io.kestra.plugin.core.trigger.Flow
    preconditions:
      id: filter_namespace
      flows:
        - namespace: solutions.github_integration
          states: [CREATED, SUCCESS, FAILED]
```

For complete example, see: **[`github_sys_push_flows_to_git.yaml`](./flows/github_sys_push_flows_to_git.yml)**

**Triggering Mechanisms**

Automate the backup process using these trigger types:

* **Schedule Trigger**: Run the sync on a regular interval (e.g., every 15 minutes) to ensure GitHub stays up to date.
* **Flow Trigger**: Automatically trigger the sync whenever a flow in your target namespace finishes (success or failure). This ensures every executed version is captured in Git.

### Best Practices

* **Use the System Namespace**: Keep administrative sync tasks isolated from functional workflows.
* **Parameterize**: Use inputs for `branch` and `namespace` to allow for manual, fine-tuned syncs when needed.
* **Dry Run**: Set `dryRun: true` during initial setup to validate the GitHub connection and directory mapping without actually committing code.

<br/><br/><br/>

## C. Promoting to Production from PRs

[![Scenario 3](./imgs/loom-04.png)](https://www.loom.com/share/a352bc37465e4b689b7701be7c1ec2cc)

Architecture:

<img src="./imgs/git-int-03.png" alt="Promoting to Production from PRs Diagram" style="max-width:760px;"/>

Deploy production-ready Kestra flows by synchronizing them from a GitHub repository to a Kestra Production instance.

**Benefits**
- **CI/CD for Workflows**: Implements a GitOps approach where changes are only deployed to Production after a Pull Request (PR) is merged.
- **Environment Parity**: Ensures your Production instance reflects the validated state of your `main` branch.
- **Automated Deployment**: Removes manual YAML uploads by using GitHub Actions to trigger Kestra's internal synchronization.

### Implementation

1. **SyncFlows Plugin (OSS)**: Pulls Flow YAML definitions from a specific Git directory into a target Kestra namespace.
2. **NamespaceSync Plugin (EE)**: Synchronizes both Flows and Namespace Files from Git, treating the repository as the absolute Source of Truth.

### The Pull Flow (System Namespace)

Define an administrative flow in the `system` namespace to handle the incoming sync request.

```yaml
id: github_sys_pull_flows_from_git
namespace: system
triggers:
  - id: on_webhook
    type: io.kestra.plugin.core.trigger.Webhook
    key: "{{secret('YOUR_WEBHOOK_TOKEN')}}" # Store this in GitHub Secrets
tasks:
  - id: sync_flows
    type: io.kestra.plugin.git.SyncFlows
    url: "https://github.com/your-repo.git"
    password: "{{ secret('github_token') }}"
    gitDirectory: "kestra/flows"
    branch: "main"
    targetNamespace: "production.namespace"

```

For complete example, see: **[`github_sys_pull_flows_from_git.yaml`](./flows/github_sys_pull_flows_from_git.yml)**

### GitHub Action Automation

Configure a GitHub Action to trigger the Kestra webhook specifically when code is pushed to `main` or when a Pull Request is merged.

```yaml
name: sync_kestra_flows_on_prs
on:
  push:
    branches: [main]
  pull_request:
    types: [closed]
    branches: [main]

jobs:
  trigger-kestra:
    if: github.event.pull_request.merged == true || github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - name: send_kestra_webhook
        run: |
          curl -X POST "https://<your-kestra-url>/api/v1/<tenant-id>/executions/webhook/system/github_sys_pull_flows_from_git/${{ secrets.KESTRA_WEBHOOK_KEY }}" \
          -H "Content-Type: application/json" \
          -d '{"message": "Deployment from GitHub PR"}'

```

For complete example, see: **[`./github_actions/kestra-prs-sync.yml`](./github_actions/kestra-prs-sync.yml)**

### Best Practices

* **PR Merged Logic**: Ensure the GitHub Action only triggers if a PR is actually merged, rather than just closed.
* **Webhook Security**: Always use a unique secret key for your Webhook and store it in GitHub Secrets.
* **Manual Overrides**: Include inputs for `branch` and `namespace` in your Kestra flow to allow for manual "emergency" syncs from the Kestra UI.

<br/><br/>

## Conclusion

This solution provides a comprehensive approach to integrating Kestra with GitHub for sourcing scripts, version controlling flows, and promoting changes to Production. By leveraging Kestra's Git plugins and GitHub Actions, teams can implement robust CI/CD practices for their data workflows, ensuring reliability, collaboration, and traceability.
