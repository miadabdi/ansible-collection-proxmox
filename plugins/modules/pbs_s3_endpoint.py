#!/usr/bin/python

# Copyright: (c) 2026, Miad Abdi <miad.abdi@sharifmind.ir>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=duplicate-code
DOCUMENTATION = r"""
---
module: pbs_s3_endpoint
author: Miad Abdi (@miadabdi)
short_description: Manage S3 endpoints on a Proxmox Backup Server
version_added: '1.0.0'
description: >
    Register and update S3 endpoints used as backends for S3-backed datastores
    on a Proxmox Backup Server instance.
notes:
  - Check mode is supported.
  - Access and secret keys can only be set at creation (PBS does not return them).
options:
  name:
    description: ID of the S3 endpoint configuration.
    type: str
    required: yes
    aliases:
      - id
  endpoint:
    description: Hostname or IP of the S3 server (without scheme).
    type: str
    required: yes
  port:
    description: Port of the S3 server.
    type: int
    required: yes
  access_key:
    description: S3 access key.
    type: str
    required: yes
  secret_key:
    description: S3 secret key. Only used when the endpoint is created.
    type: str
    required: yes
  fingerprint:
    description: >
        Fingerprint of the S3 server TLS certificate
        (colon-separated hex, e.g. C(AA:BB:CC:...)). Required when the
        endpoint uses self-signed certificates.
    type: str
    required: yes
  state:
    description: C(present) ensures the endpoint exists with the given settings.
    type: str
    choices:
      - present
    default: present

extends_documentation_fragment:
  - miadabdi.proxmox.api_connection
"""

EXAMPLES = r"""
- name: Register a SeaweedFS S3-TLS endpoint
  miadabdi.proxmox.pbs_s3_endpoint:
    api_host: pbs.example.com
    api_user: root@pam
    api_auth_method: token
    api_token_name: ansible
    api_token_secret: "{{ pbs_token_secret }}"
    name: seaweedfs-tls
    endpoint: 10.0.0.10
    port: 8334
    access_key: "{{ s3_access_key }}"
    secret_key: "{{ s3_secret_key }}"
    fingerprint: "AA:BB:CC:DD:..."
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.api_connection import api_connection_argspec, init

try:
    import proxmoxer
    HAS_PROXMOXER = True
except ImportError:
    HAS_PROXMOXER = False

# Only these are compared for drift and PUT on update; the master-key and
# other fields PBS returns stay untouched.
DRIFT_KEYS = ["endpoint", "port", "fingerprint"]


def _make_params(module: AnsibleModule, include_secrets=False) -> dict:
    params = {
        "id": module.params["name"],
        "endpoint": module.params["endpoint"],
        "port": module.params["port"],
        "access-key": module.params["access_key"],
        "fingerprint": module.params["fingerprint"],
    }
    if include_secrets:
        params["secret-key"] = module.params["secret_key"]
    return params


def main():
    module_args = dict(
        name=dict(type="str", required=True, aliases=["id"]),
        endpoint=dict(type="str", required=True),
        port=dict(type="int", required=True),
        access_key=dict(type="str", required=True, no_log=True),
        secret_key=dict(type="str", required=True, no_log=True),
        fingerprint=dict(type="str", required=True),
        state=dict(type="str", choices=["present"], default="present"),
    )
    result = dict(changed=False, msg="")
    module = AnsibleModule(
        argument_spec={**module_args, **api_connection_argspec},
        supports_check_mode=True
    )

    proxmox = init(module, result, "PBS")
    desired = _make_params(module, include_secrets=True)

    try:
        endpoints = proxmox.config.s3.get()
    except proxmoxer.ResourceException as e:
        result["msg"] = f"Could not get list of S3 endpoints. Exception: {e}"
        module.fail_json(**result)

    current = next((e for e in endpoints if e.get("id") == module.params["name"]), None)

    if current is None:
        result["changed"] = True
        if not module.check_mode:
            try:
                proxmox.config.s3.post(**desired)
            except proxmoxer.ResourceException as e:
                result["msg"] = f"Could not create S3 endpoint. Exception: {e}"
                module.fail_json(**result)
        module.exit_json(**result)

    # Drift check on the non-secret fields only.
    drift = {key: desired[key] for key in DRIFT_KEYS
             if str(current.get(key)) != str(desired[key])}
    if drift:
        result["changed"] = True
        if not module.check_mode:
            try:
                getattr(proxmox.config.s3, module.params["name"]).put(**drift)
            except proxmoxer.ResourceException as e:
                result["msg"] = f"Could not update S3 endpoint. Exception: {e}"
                module.fail_json(**result)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
