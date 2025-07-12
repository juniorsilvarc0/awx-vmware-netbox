from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import ssl
from ansible.plugins.inventory import BaseInventoryPlugin
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

class InventoryModule(BaseInventoryPlugin):
    NAME = 'vmware_dynamic'

    def verify_file(self, path):
        return path.endswith(('inventory.yml', 'vmware_inventory.yml'))

    def parse(self, inventory, loader, path, cache=True):
        self.inventory = inventory
        self.loader = loader

        vcenter_config = {
            'host': os.environ.get('VMWARE_HOST', os.environ.get('VCENTER_HOST')),
            'user': os.environ.get('VMWARE_USER', os.environ.get('VCENTER_USERNAME')),
            'pwd': os.environ.get('VMWARE_PASSWORD'),
            'port': int(os.environ.get('VMWARE_PORT', 443)),
            'datacenter': os.environ.get('DATACENTER_NAME')
        }

        missing = [k for k, v in vcenter_config.items() if v is None]
        if missing:
            raise Exception(f"Missing required environment variables: {', '.join(missing)}")

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        si = SmartConnect(
            host=vcenter_config['host'],
            user=vcenter_config['user'],
            pwd=vcenter_config['pwd'],
            port=vcenter_config['port'],
            sslContext=context
        )

        content = si.RetrieveContent()
        datacenter = next(
            (dc for dc in content.rootFolder.childEntity if dc.name == vcenter_config['datacenter']),
            None
        )
        if not datacenter:
            raise Exception(f"Datacenter {vcenter_config['datacenter']} not found")

        container = content.viewManager.CreateContainerView(
            datacenter.vmFolder, [vim.VirtualMachine], True
        )

        for vm in container.view:
            if not vm.config or vm.config.template or vm.name.startswith('template'):
                continue

            name = vm.name
            config = vm.config
            summary = vm.summary
            runtime = vm.runtime
            guest = vm.guest

            ip_addresses = []
            if guest and guest.net:
                for nic in guest.net:
                    if nic.ipAddress:
                        ip_addresses.extend([ip for ip in nic.ipAddress if ip and not ip.startswith('fe80')])

            memory_gb = round((summary.config.memorySizeMB / 1024), 1) if summary.config else 0

            vm_data = {
                'ansible_host': ip_addresses[0] if ip_addresses else None,
                'vm_name': name,
                'vm_uuid': config.uuid,
                'vm_power_state': runtime.powerState,
                'vm_guest_os': config.guestFullName,
                'vm_guest_family': guest.guestFamily if guest else None,
                'vm_cpu_count': summary.config.numCpu if summary.config else 0,
                'vm_memory_mb': summary.config.memorySizeMB if summary.config else 0,
                'vm_memory_gb': memory_gb,
                'vm_datacenter': runtime.host.parent.parent.parent.name if runtime and runtime.host else None,
                'vm_cluster': runtime.host.parent.name if runtime and runtime.host else None,
                'vm_folder': vm.parent.name if vm.parent else None,
                'vm_ip_addresses': ip_addresses,
                'vm_hostname': guest.hostName if guest else None,
                'vm_tools_status': guest.toolsStatus if guest else None,
                'vm_tools_running': guest.toolsStatus == 'toolsOk' if guest else False,
                'vm_environment': 'production' if 'prod' in name.lower() else 'development' if 'dev' in name.lower() else 'testing' if 'test' in name.lower() else 'staging' if 'stg' in name.lower() else 'unknown',
                'vm_criticality': 'high' if 'prod' in name.lower() else 'medium' if 'test' in name.lower() or 'stg' in name.lower() else 'low',
                'vm_is_windows': 'windows' in config.guestFullName.lower(),
                'vm_is_linux': any(x in config.guestFullName.lower() for x in ['linux', 'ubuntu', 'centos', 'red hat', 'suse', 'debian']),
                'vm_cpu_category': 'high' if summary.config.numCpu >= 8 else 'medium' if summary.config.numCpu >= 4 else 'low',
                'vm_memory_category': 'high' if memory_gb >= 16 else 'medium' if memory_gb >= 8 else 'low' if memory_gb >= 4 else 'minimal'
            }

            self.inventory.add_host(name)
            for k, v in vm_data.items():
                self.inventory.set_variable(name, k, v)

        container.Destroy()
        Disconnect(si)
