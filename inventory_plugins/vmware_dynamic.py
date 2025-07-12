from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import ssl
import re
from ansible.plugins.inventory import BaseInventoryPlugin
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

class InventoryModule(BaseInventoryPlugin):
    NAME = 'vmware_dynamic'

    def verify_file(self, path):
        return path.endswith(('inventory.yml', 'vmware_inventory.yml'))

    def _sanitize_string(self, value):
        """Sanitiza strings para evitar problemas de JSON/YAML"""
        if value is None:
            return None
        if isinstance(value, str):
            # Remove caracteres de controle e aspas problemáticas
            value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
            value = value.replace('"', "'").replace('\n', ' ').replace('\r', ' ')
            return value.strip()
        return value

    def parse(self, inventory, loader, path, cache=True):
        self.inventory = inventory
        self.loader = loader

        vcenter_config = {
            'host': os.environ.get('VCENTER_HOST'),
            'user': os.environ.get('VCENTER_USER'),
            'pwd': os.environ.get('VCENTER_PASSWORD'),
            'port': int(os.environ.get('VCENTER_PORT', 443)),
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
            try:
                if not vm.config or vm.config.template or vm.name.startswith('template'):
                    continue

                name = vm.name
                config = vm.config
                summary = vm.summary
                runtime = vm.runtime
                guest = vm.guest
                
                # Validações básicas
                if not name or not config:
                    continue

                ip_addresses = []
                if guest and guest.net:
                    for nic in guest.net:
                        if nic.ipAddress:
                            ip_addresses.extend([ip for ip in nic.ipAddress if ip and not ip.startswith('fe80')])

                memory_gb = round((summary.config.memorySizeMB / 1024), 1) if summary.config else 0

                vm_data = {
                    'ansible_host': ip_addresses[0] if ip_addresses else None,
                    'vm_name': self._sanitize_string(name),
                    'vm_uuid': self._sanitize_string(config.uuid if config else None),
                    'vm_power_state': self._sanitize_string(runtime.powerState if runtime else None),
                    'vm_guest_os': self._sanitize_string(config.guestFullName if config else None),
                    'vm_guest_family': self._sanitize_string(guest.guestFamily if guest else None),
                    'vm_cpu_count': summary.config.numCpu if summary.config else 0,
                    'vm_memory_mb': summary.config.memorySizeMB if summary.config else 0,
                    'vm_memory_gb': memory_gb,
                    'vm_datacenter': self._sanitize_string(runtime.host.parent.parent.parent.name if runtime and runtime.host else None),
                    'vm_cluster': self._sanitize_string(runtime.host.parent.name if runtime and runtime.host else None),
                    'vm_folder': self._sanitize_string(vm.parent.name if vm.parent else None),
                    'vm_ip_addresses': ip_addresses,
                    'vm_hostname': self._sanitize_string(guest.hostName if guest else None),
                    'vm_tools_status': self._sanitize_string(guest.toolsStatus if guest else None),
                    'vm_tools_running': guest.toolsStatus == 'toolsOk' if guest else False,
                    'vm_environment': 'production' if 'prod' in name.lower() else 'development' if 'dev' in name.lower() else 'testing' if 'test' in name.lower() else 'staging' if 'stg' in name.lower() else 'unknown',
                    'vm_criticality': 'high' if 'prod' in name.lower() else 'medium' if 'test' in name.lower() or 'stg' in name.lower() else 'low',
                    'vm_is_windows': 'windows' in (config.guestFullName.lower() if config and config.guestFullName else ''),
                    'vm_is_linux': any(x in (config.guestFullName.lower() if config and config.guestFullName else '') for x in ['linux', 'ubuntu', 'centos', 'red hat', 'suse', 'debian']),
                    'vm_cpu_category': 'high' if summary.config.numCpu >= 8 else 'medium' if summary.config.numCpu >= 4 else 'low',
                    'vm_memory_category': 'high' if memory_gb >= 16 else 'medium' if memory_gb >= 8 else 'low' if memory_gb >= 4 else 'minimal'
                }

                # Sanitizar nome do host para evitar problemas
                safe_name = self._sanitize_string(name)
                if not safe_name:
                    safe_name = f"vm_{config.uuid[:8]}" if config and config.uuid else f"unknown_vm_{len(self.inventory.hosts)}"
                
                self.inventory.add_host(safe_name)
                for k, v in vm_data.items():
                    if v is not None:  # Só adicionar variáveis não-nulas
                        self.inventory.set_variable(safe_name, k, v)

                # Criar grupos por estado de energia
                if runtime and runtime.powerState == 'poweredOn':
                    self.inventory.add_group('powered_on')
                    self.inventory.add_child('powered_on', safe_name)
                elif runtime and runtime.powerState == 'poweredOff':
                    self.inventory.add_group('powered_off')
                    self.inventory.add_child('powered_off', safe_name)
                elif runtime and runtime.powerState == 'suspended':
                    self.inventory.add_group('suspended')
                    self.inventory.add_child('suspended', safe_name)

                # Criar grupos por sistema operacional
                if vm_data['vm_is_windows']:
                    self.inventory.add_group('windows')
                    self.inventory.add_child('windows', safe_name)
                elif vm_data['vm_is_linux']:
                    self.inventory.add_group('linux')
                    self.inventory.add_child('linux', safe_name)
            
            except Exception as e:
                # Log do erro mas continua processando outras VMs
                print(f"Erro processando VM {getattr(vm, 'name', 'unknown')}: {str(e)}")
                continue

        container.Destroy()
        Disconnect(si)
