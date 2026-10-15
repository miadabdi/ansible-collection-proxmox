#!/usr/bin/python

# Copyright: (c) 2026, Miad Abdi <miad.abdi@sharifmind.ir>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=duplicate-code
DOCUMENTATION = r"""
---
module: pbs_prune_job
author: Miad Abdi (@miadabdi)
short_description: Manage prune jobs on a Proxmox Backup Server
version_added: '1.0.0'
description: >
    Create and update prune jobs (retention enforcement) on a Proxmox Backup
    Server instance.
notes:
  - Check mode is supported.
options:
  id:
    description: ID of the prune job.
    type: str
    required: yes
  store:
    description: Name of the datastore the job operates on.
    type: str
    required: yes
  schedule:
    description: Schedule for the job, e.g. C(daily).
    type: str
    required: yes
  keep_daily:
    description: Number of daily snapshots to retain.
    type: int
  keep_weekly:
    description: Number of weekly snapshots to retain.
    type: int
  keep_monthly:
    description: Number of monthly snapshots to retain.
    type: int
  state:
    description: C(present) ensures the job exists with the given settings.
    type: str
    choices:
      - present
    default: present

extends_documentation_fragment:
  - miadabdi.proxmox.api_connection
"""

EXAMPLES = r"""
- name: Daily prune with 7 daily / 2 weekly / 1 monthly retention
  miadabdi.proxmox.pbs_prune_job:
    api_host: pbs.example.com
    api_user: root@pam
    api_auth_method: token
    api_token_name: ansible
    api_token_secret: "{{ pbs_token_secret }}"
    id: prune-pbs-services
    store: pbs-services
    schedule: daily
    keep_daily: 7
    keep_weekly: 2
    keep_monthly: 1
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.api_connection import api_connection_argspec, init

try:
    import proxmoxer
    HAS_PROXMOXER = True
except ImportError:
    HAS_PROXMOXER = False

DRIFT_KEYS = ["store", "schedule", "keep-daily", "keep-weekly", "keep-monthly"]


def _make_params(module: AnsibleModule, include_name=False) -> dict:
    params = {
        "store": module.params["store"],
        "schedule": module.params["schedule"],
    }
    for key in ("keep_daily", "keep_weekly", "keep_monthly"):
        if module.params[key] is not None:
            params[key.replace("_", "-")] = module.params[key]
    if include_name:
        params["id"] = module.params["id"]
    return params


def main():
    module_args = dict(
        id=dict(type="str", required=True),
        store=dict(type="str", required=True),
        schedule=dict(type="str", required=True),
        keep_daily=dict(type="int"),
        keep_weekly=dict(type="int"),
        keep_monthly=dict(type="int"),
        state=dict(type="str", choices=["present"], default="present"),
    )
    result = dict(changed=False, msg="")
    module = AnsibleModule(
        argument_spec={**module_args, **api_connection_argspec},
        supports_check_mode=True
    )

    proxmox = init(module, result, "PBS")
    desired = _make_params(module, include_name=True)

    try:
        jobs = proxmox.config.prune.get()
    except proxmoxer.ResourceException as e:
        result["msg"] = f"Could not get list of prune jobs. Exception: {e}"
        module.fail_json(**result)

    current = next((j for j in jobs if j.get("id") == module.params["id"]), None)

    if current is None:
        result["changed"] = True
        if not module.check_mode:
            try:
                proxmox.config.prune.post(**desired)
            except proxmoxer.ResourceException as e:
                result["msg"] = f"Could not create prune job. Exception: {e}"
                module.fail_json(**result)
        module.exit_json(**result)

    drift = {key: desired[key] for key in DRIFT_KEYS
             if key in desired and str(current.get(key)) != str(desired[key])}
    if drift:
        result["changed"] = True
        if not module.check_mode:
            try:
                getattr(proxmox.config.prune, module.params["id"]).put(**drift)
            except proxmoxer.ResourceException as e:
                result["msg"] = f"Could not update prune job. Exception: {e}"
                module.fail_json(**result)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
