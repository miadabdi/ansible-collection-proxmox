#!/usr/bin/python

# Copyright: (c) 2026, Miad Abdi <miad.abdi@sharifmind.ir>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=duplicate-code
DOCUMENTATION = r"""
---
module: pbs_s3_datastore
author: Miad Abdi (@miadabdi)
short_description: Manage S3-backed datastores on a Proxmox Backup Server
version_added: '1.0.0'
description: >
    Create S3-backed datastores on a Proxmox Backup Server instance.
    PBS requires an S3 endpoint (see M(miadabdi.proxmox.pbs_s3_endpoint)) and
    uses the datastore name as the bucket key prefix.
    For local-filesystem datastores use M(miadabdi.proxmox.pbs_datastore) instead.
notes:
  - Check mode is supported.
  - PBS cannot update the backend of an existing datastore: if one exists with
    a different configuration, this module fails instead of silently diverging.
  - The local cache path is mandatory for S3 datastores; size the disk for
    chunk staging (64-128 GiB recommended).
options:
  name:
    description: Name of the datastore. Also used as the S3 bucket key prefix — keep them identical.
    type: str
    required: yes
  cache_path:
    description: Local path where chunks are staged before upload.
    type: str
    required: yes
    aliases:
      - path
  backend:
    description: >
        Backend definition string, e.g.
        C(type=s3,client=<endpoint-name>,bucket=<bucket>).
    type: str
    required: yes
  state:
    description: C(present) ensures the datastore exists.
    type: str
    choices:
      - present
    default: present

extends_documentation_fragment:
  - miadabdi.proxmox.api_connection
"""

EXAMPLES = r"""
- name: Create an S3-backed datastore
  miadabdi.proxmox.pbs_s3_datastore:
    api_host: pbs.example.com
    api_user: root@pam
    api_auth_method: token
    api_token_name: ansible
    api_token_secret: "{{ pbs_token_secret }}"
    name: pbs-services
    cache_path: /var/lib/proxmox-backup/cache/pbs-services
    backend: "type=s3,client=seaweedfs-tls,bucket=pbs-services"
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
        name=dict(type="str", required=True),
        cache_path=dict(type="str", required=True, aliases=["path"]),
        backend=dict(type="str", required=True),
        state=dict(type="str", choices=["present"], default="present"),
    )
    result = dict(changed=False, msg="")
    module = AnsibleModule(
        argument_spec={**module_args, **api_connection_argspec},
        supports_check_mode=True
    )

    proxmox = init(module, result, "PBS")

    try:
        datastores = proxmox.config.datastore.get()
    except proxmoxer.ResourceException as e:
        result["msg"] = f"Could not get list of datastores. Exception: {e}"
        module.fail_json(**result)

    current = next((d for d in datastores if d.get("name") == module.params["name"]), None)
    if current is not None:
        # PBS has no update for S3 backends; fail loudly on drift.
        if current.get("path") != module.params["cache_path"]:
            result["msg"] = (f"datastore {module.params['name']} exists with different "
                             f"config: path={current.get('path')}")
            module.fail_json(**result)
        module.exit_json(**result)

    result["changed"] = True
    if not module.check_mode:
        try:
            proxmox.config.datastore.post(
                name=module.params["name"],
                path=module.params["cache_path"],
                backend=module.params["backend"],
            )
        except proxmoxer.ResourceException as e:
            result["msg"] = f"Could not create S3 datastore. Exception: {e}"
            module.fail_json(**result)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
