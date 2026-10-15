#!/usr/bin/python

# Copyright: (c) 2026, Miad Abdi <miad.abdi@sharifmind.ir>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=duplicate-code
DOCUMENTATION = r"""
---
module: pbs_gc_schedule
author: Miad Abdi (@miadabdi)
short_description: Manage the garbage collection schedule of a datastore
version_added: '1.0.0'
description: >
    Set the garbage-collection schedule of a datastore on a Proxmox Backup
    Server instance. The GC reclaims chunks forgotten by prune jobs.
notes:
  - Check mode is supported.
options:
  store:
    description: Name of the datastore.
    type: str
    required: yes
    aliases:
      - datastore
      - name
  schedule:
    description: GC schedule, e.g. C(sun 03:00).
    type: str
    required: yes
  state:
    description: C(present) ensures the schedule is set.
    type: str
    choices:
      - present
    default: present

extends_documentation_fragment:
  - miadabdi.proxmox.api_connection
"""

EXAMPLES = r"""
- name: Weekly GC on Sunday morning
  miadabdi.proxmox.pbs_gc_schedule:
    api_host: pbs.example.com
    api_user: root@pam
    api_auth_method: token
    api_token_name: ansible
    api_token_secret: "{{ pbs_token_secret }}"
    store: pbs-services
    schedule: "sun 03:00"
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.api_connection import api_connection_argspec, init

try:
    import proxmoxer
    HAS_PROXMOXER = True
except ImportError:
    HAS_PROXMOXER = False


def main():
    module_args = dict(
        store=dict(type="str", required=True, aliases=["datastore", "name"]),
        schedule=dict(type="str", required=True),
        state=dict(type="str", choices=["present"], default="present"),
    )
    result = dict(changed=False, msg="")
    module = AnsibleModule(
        argument_spec={**module_args, **api_connection_argspec},
        supports_check_mode=True
    )

    proxmox = init(module, result, "PBS")

    try:
        current = getattr(proxmox.config.datastore, module.params["store"]).get()
    except proxmoxer.ResourceException as e:
        result["msg"] = f"Could not get datastore config. Exception: {e}"
        module.fail_json(**result)

    if str((current or {}).get("gc-schedule")) != module.params["schedule"]:
        result["changed"] = True
        if not module.check_mode:
            try:
                getattr(proxmox.config.datastore, module.params["store"]).put(
                    **{"gc-schedule": module.params["schedule"]})
            except proxmoxer.ResourceException as e:
                result["msg"] = f"Could not update gc schedule. Exception: {e}"
                module.fail_json(**result)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
