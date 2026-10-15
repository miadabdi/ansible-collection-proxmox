#!/usr/bin/python

# Copyright: (c) 2026, Miad Abdi <miad.abdi@sharifmind.ir>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=duplicate-code
DOCUMENTATION = r"""
---
module: pbs_namespace
author: Miad Abdi (@miadabdi)
short_description: Manage datastore namespaces on a Proxmox Backup Server
version_added: '1.0.0'
description: >
    Ensure namespaces exist on a datastore. Clients cannot create namespaces
    themselves — every producer namespace must be pre-created, e.g. for
    standby hosts restoring another host's backups.
notes:
  - Check mode is supported.
  - Deleting a namespace does not delete its snapshots; forget them first.
options:
  store:
    description: Name of the datastore.
    type: str
    required: yes
    aliases:
      - datastore
  name:
    description: Namespace ID, e.g. C(gitlab).
    type: str
    required: yes
    aliases:
      - ns
  state:
    description: C(present) ensures the namespace exists, C(absent) removes it.
    type: str
    choices:
      - present
      - absent
    default: present

extends_documentation_fragment:
  - miadabdi.proxmox.api_connection
"""

EXAMPLES = r"""
- name: Ensure the gitlab namespace exists
  miadabdi.proxmox.pbs_namespace:
    api_host: pbs.example.com
    api_user: root@pam
    api_auth_method: token
    api_token_name: ansible
    api_token_secret: "{{ pbs_token_secret }}"
    store: pbs-services
    name: gitlab
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
        store=dict(type="str", required=True, aliases=["datastore"]),
        name=dict(type="str", required=True, aliases=["ns"]),
        state=dict(type="str", choices=["present", "absent"], default="present"),
    )
    result = dict(changed=False, msg="")
    module = AnsibleModule(
        argument_spec={**module_args, **api_connection_argspec},
        supports_check_mode=True
    )

    proxmox = init(module, result, "PBS")

    try:
        namespaces = getattr(proxmox.admin.datastore, module.params["store"]).namespace.get()
    except proxmoxer.ResourceException as e:
        result["msg"] = f"Could not get list of namespaces. Exception: {e}"
        module.fail_json(**result)

    exists = any(n.get("ns") == module.params["name"] for n in namespaces)

    if exists and module.params["state"] == "absent":
        result["changed"] = True
        if not module.check_mode:
            try:
                getattr(getattr(proxmox.admin.datastore, module.params["store"]).namespace,
                        module.params["name"]).delete()
            except proxmoxer.ResourceException as e:
                result["msg"] = f"Could not delete namespace. Exception: {e}"
                module.fail_json(**result)
        module.exit_json(**result)

    if not exists and module.params["state"] == "present":
        result["changed"] = True
        if not module.check_mode:
            try:
                getattr(proxmox.admin.datastore, module.params["store"]).namespace.post(
                    name=module.params["name"])
            except proxmoxer.ResourceException as e:
                result["msg"] = f"Could not create namespace. Exception: {e}"
                module.fail_json(**result)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
