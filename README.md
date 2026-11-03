# OpenShift Security Roadshow automation

Ansible collection that provisions the OpenShift Security Roadshow on the Red Hat Demo Platform (RHDP).

## Role: ocp5_rhacs

On `ACTION: provision` the role:

- Installs OpenShift GitOps
- Deploys the app-of-apps Argo CD Application from [ocp5-rhacs-gitops](https://github.com/rhpds/ocp5-rhacs-gitops)
- Installs the `oc-agentic` and FastMCP CLIs on the bastion
- Publishes Showroom user data for the OpenShift console, RHACS, Quay, GitOps, and the Lightwell TSSC routes

The GitOps chart stands up the roadshow workload: RHACS, the virtual machine used by the ACS labs, Quay, the demo applications, roadshow prerequisites, the ACS and OpenShift MCP servers, OpenShift Lightspeed, and the Lightwell TSSC workshop stack.

On `ACTION: destroy` the role removes the app-of-apps Application.

### Usage

Set `ACTION: provision` to deploy or `ACTION: destroy` to tear down.

Configurable variables are in `roles/ocp5_rhacs/defaults/main.yml`.

### Bounded bootstrap recovery

Provisioning polls the parent and labeled child Applications for up to 60 checks
within a 3600-second budget. Readiness requires completed sync operations and
Synced/Healthy state across consecutive samples, not just a successful apply.

Recovery waits for MachineConfig pools to finish updating and GitOps repo-server
and application-controller pods to be Ready across multiple samples. It then
resyncs only idle failed/degraded apps, or completed apps with remaining drift,
at their already-resolved commit(s). Active syncs are never cancelled. Each app
has at most three accepted recovery operations, five polls apart, with at most
three recovery requests per poll. Optimistic resource-version checks prevent a
stale snapshot from overwriting an operation started by another controller.

Recovery can be disabled with `ocp5_rhacs_bootstrap_recovery_enabled: false`.
The budget, interval, cooldown and sample count are configurable in defaults.
Permanent failures still fail provisioning by default. The legacy
`ocp5_rhacs_wait_for_apps_ignore_errors` override, if explicitly enabled, emits
a warning that the deployment has NOT passed GitOps validation.

Application specs can contain credentials. Polling and patch results use
`no_log`; progress and timeout reports contain only names, states and counters.

Tests: `python -m unittest discover -s tests -v`.
