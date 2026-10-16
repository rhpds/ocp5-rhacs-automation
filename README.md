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
