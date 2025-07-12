from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
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
            'host': 'vcsa04.ati.pi.gov.br',
            'user': 'netbox-ro@VSPHERE.LOCAL',
            'pwd': '9i7j&BtSzwZ]',
            'port': 443,
            'datacenter': 'ATI-SLC-HCI'
        }

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
            ip_addresses = []
            if vm.guest and vm.guest.net:
                for nic in vm.guest.net:
                    if nic.ipAddress:
                        ip_addresses.extend(nic.ipAddress)

            ansible_host = ip_addresses[0] if ip_addresses else None
            self.inventory.add_host(name)
            self.inventory.set_variable(name, 'ansible_host', ansible_host)
            self.inventory.set_variable(name, 'vm_name', name)
            self.inventory.set_variable(name, 'vm_power_state', vm.runtime.powerState)
            self.inventory.set_variable(name, 'vm_guest_os', vm.config.guestFullName)

            if 'windows' in vm.config.guestFullName.lower():
                self.inventory.add_group('windows')
                self.inventory.add_child('windows', name)
            elif 'linux' in vm.config.guestFullName.lower():
                self.inventory.add_group('linux')
                self.inventory.add_child('linux', name)

        container.Destroy()
        Disconnect(si)
