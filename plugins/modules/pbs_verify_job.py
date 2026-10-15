#!/usr/bin/python

# Copyright: (c) 2026, Miad Abdi <miad.abdi@sharifmind.ir>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=duplicate-code
DOCUMENTATION = r"""
---
module: pbs_verify_job
author: Miad Abdi (@miadabdi)
short_description: Manage verify jobs on a Proxmox Backup Server
version_added: '1.0.0'
description: >
    Create and update verify jobs (checksum verification of stored snapshots)
    on a Proxmox Backup Server instance.
notes:
  - Check mode is supported.
options:
  id:
    description: ID of the verify job.
    type: str
    required: yes
  store:
    description: Name of the datastore the job operates on.
    type: str
    required: yes
  schedule:
    description: Schedule for the job, e.g. C(daily) or C(sun 03:00).
    type: str
    required: yes
  outdated_after:
    description: >
        Verify snapshots that are older than the specified number of days.
        If not set, only new snapshots are verified.
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
- name: Daily verification of all snapshots older than a day
  miadabdi.proxmox.pbs_verify_job:
    api_host: pbs.example.com
    api_user: root@pam
    api_auth_method: token
    api_token_name: ansible
    api_token_secret: "{{ pbs_token_secret }}"
    id: verify-pbs-services
    store: pbs-services
    schedule: daily
    outdated_after: 86400
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.api_connection import api_connection_argspec, init

try:
    import proxmoxer
    HAS_PROXMOXER = True
except ImportError:
    HAS_PROXMOXER = False

DRIFT_KEYS = ["store", "schedule", "outdated-after"]


def _make_params(module: AnsibleModule) -> dict:
    params = {
        "id": module.params["id"],
        "store": module.params["store"],
        "schedule": module.params["schedule"],
    }
    if module.params["outdated_after"] is not None:
        params["outdated-after"] = module.params["outdated_after"]
    return params


def main():
    module_args = dict(
        id=dict(type="str", required=True),
        store=dict(type="str", required=True),
        schedule=dict(type="str", required=True),
        outdated_after=dict(type="int"),
        state=dict(type="str", choices=["present"], default="present"),
    )
    result = dict(changed=False, msg="")
    module = AnsibleModule(
        argument_spec={**module_args, **api_connection_argspec},
        supports_check_mode=True
    )

    proxmox = init(module, result, "PBS")
    desired = _make_params(module)

    try:
        jobs = proxmox.config.verify.get()
    except proxmoxer.ResourceException as e:
        result["msg"] = f"Could not get list of verify jobs. Exception: {e}"
        module.fail_json(**result)

    current = next((j for j in jobs if j.get("id") == module.params["id"]), None)

    if current is None:
        result["changed"] = True
        if not module.check_mode:
            try:
                proxmox.config.verify.post(**desired)
            except proxmoxer.ResourceException as e:
                result["msg"] = f"Could not create verify job. Exception: {e}"
                module.fail_json(**result)
        module.exit_json(**result)

    drift = {key: desired[key] for key in DRIFT_KEYS
             if key in desired and str(current.get(key)) != str(desired[key])}
    if drift:
        result["changed"] = True
        if not module.check_mode:
            try:
                getattr(proxmox.config.verify, module.params["id"]).put(**drift)
            except proxmoxer.ResourceException as e:
                result["msg"] = f"Could not update verify job. Exception: {e}"
                module.fail_json(**result)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
