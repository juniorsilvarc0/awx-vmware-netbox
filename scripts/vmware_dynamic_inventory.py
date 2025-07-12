#!/usr/bin/env python3
"""
Inventário dinâmico VMware para AWX - Otimizado para 1000+ VMs
Arquivo: scripts/vmware_dynamic_inventory.py
Credenciais gerenciadas pelo AWX via variáveis de ambiente
"""

import json
import sys
import ssl
import time
import os
import argparse
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

class VMwareInventory:
    def __init__(self):
        self.inventory = {
            '_meta': {
                'hostvars': {}
            }
        }
        self.read_settings()
        
    def read_settings(self):
        """Lê configurações das variáveis de ambiente do AWX"""
        self.vcenter_host = os.environ.get('VMWARE_HOST', os.environ.get('VCENTER_HOST'))
        self.vcenter_user = os.environ.get('VMWARE_USER', os.environ.get('VMWARE_USERNAME'))
        self.vcenter_password = os.environ.get('VMWARE_PASSWORD')
        self.vcenter_port = int(os.environ.get('VMWARE_PORT', '443'))
        self.datacenter_name = os.environ.get('DATACENTER_NAME', 'ATI-SLC-HCI')
        self.validate_certs = os.environ.get('VMWARE_VALIDATE_CERTS', 'false').lower() == 'true'
        
        # Verificar credenciais obrigatórias
        if not all([self.vcenter_host, self.vcenter_user, self.vcenter_password]):
            raise Exception("Credenciais VMware não encontradas nas variáveis de ambiente")
    
    def connect_to_vcenter(self):
        """Conecta ao vCenter"""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        if not self.validate_certs:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        
        try:
            self.service_instance = SmartConnect(
                host=self.vcenter_host,
                user=self.vcenter_user,
                pwd=self.vcenter_password,
                port=self.vcenter_port,
                sslContext=context
            )
            return True
        except Exception as e:
            print(f"Erro ao conectar ao vCenter: {str(e)}", file=sys.stderr)
            return False
    
    def get_datacenter(self):
        """Encontra o datacenter especificado"""
        content = self.service_instance.RetrieveContent()
        for dc in content.rootFolder.childEntity:
            if dc.name == self.datacenter_name:
                return dc
        raise Exception(f"Datacenter {self.datacenter_name} não encontrado")
    
    def process_vm(self, vm):
        """Processa uma VM individual e retorna suas informações"""
        try:
            # Verificar se é uma VM válida
            if (not vm.config or 
                vm.config.template or 
                vm.name.startswith('template')):
                return None
            
            summary = vm.summary
            config = vm.config
            runtime = vm.runtime
            guest = vm.guest
            
            # Obter endereços IP
            ip_addresses = []
            if guest and guest.net:
                for nic in guest.net:
                    if nic.ipAddress:
                        ip_addresses.extend([ip for ip in nic.ipAddress if ip and not ip.startswith('fe80')])
            
            # Obter informações de localização
            datacenter = None
            cluster = None
            folder = None
            
            try:
                if runtime and runtime.host:
                    cluster = runtime.host.parent.name
                    datacenter = runtime.host.parent.parent.parent.name
                if vm.parent:
                    folder = vm.parent.name
            except:
                pass
            
            # Calcular memória em GB
            memory_gb = round((summary.config.memorySizeMB / 1024), 1) if summary.config else 0
            
            # Classificar ambiente baseado no nome
            vm_name_lower = vm.name.lower()
            if any(x in vm_name_lower for x in ['prod', 'prd', 'production']):
                environment = 'production'
            elif any(x in vm_name_lower for x in ['dev', 'devel', 'development']):
                environment = 'development'
            elif any(x in vm_name_lower for x in ['test', 'tst', 'qa', 'homolog']):
                environment = 'testing'
            elif any(x in vm_name_lower for x in ['stg', 'staging']):
                environment = 'staging'
            else:
                environment = 'unknown'
            
            # Determinar sistema operacional
            guest_os = config.guestFullName.lower() if config.guestFullName else ''
            is_windows = 'windows' in guest_os
            is_linux = any(x in guest_os for x in ['linux', 'ubuntu', 'centos', 'red hat', 'suse', 'debian'])
            
            vm_data = {
                # Ansible essentials
                'ansible_host': ip_addresses[0] if ip_addresses else None,
                
                # VM básico
                'vm_name': vm.name,
                'vm_uuid': config.uuid,
                'vm_power_state': runtime.powerState,
                'vm_guest_os': config.guestFullName,
                'vm_guest_family': guest.guestFamily if guest else None,
                
                # Recursos
                'vm_cpu_count': summary.config.numCpu if summary.config else 0,
                'vm_memory_mb': summary.config.memorySizeMB if summary.config else 0,
                'vm_memory_gb': memory_gb,
                
                # Localização
                'vm_datacenter': datacenter,
                'vm_cluster': cluster,
                'vm_folder': folder,
                
                # Rede
                'vm_ip_addresses': ip_addresses,
                'vm_hostname': guest.hostName if guest else None,
                
                # VMware Tools
                'vm_tools_status': guest.toolsStatus if guest else None,
                'vm_tools_running': guest.toolsStatus == 'toolsOk' if guest else False,
                
                # Classificações
                'vm_environment': environment,
                'vm_criticality': 'high' if environment == 'production' else 'medium' if environment in ['testing', 'staging'] else 'low',
                'vm_is_windows': is_windows,
                'vm_is_linux': is_linux,
                
                # Categorias de recursos
                'vm_cpu_category': 'high' if summary.config.numCpu >= 8 else 'medium' if summary.config.numCpu >= 4 else 'low',
                'vm_memory_category': 'high' if memory_gb >= 16 else 'medium' if memory_gb >= 8 else 'low' if memory_gb >= 4 else 'minimal'
            }
            
            return vm_data
            
        except Exception as e:
            print(f"Erro ao processar VM {vm.name}: {str(e)}", file=sys.stderr)
            return None
    
    def get_inventory(self):
        """Coleta inventário completo do vCenter"""
        if not self.connect_to_vcenter():
            return self.inventory
        
        try:
            datacenter = self.get_datacenter()
            
            # Criar container view para VMs
            container = self.service_instance.RetrieveContent().viewManager.CreateContainerView(
                datacenter.vmFolder, [vim.VirtualMachine], True
            )
            
            # Inicializar grupos
            groups = {
                'all': {'children': []},
                'vmware_vms': {'hosts': []},
                'powered_on': {'hosts': []},
                'powered_off': {'hosts': []},
                'suspended': {'hosts': []},
                'windows': {'hosts': []},
                'linux': {'hosts': []},
                'production': {'hosts': []},
                'development': {'hosts': []},
                'testing': {'hosts': []},
                'staging': {'hosts': []},
                'high_cpu': {'hosts': []},
                'medium_cpu': {'hosts': []},
                'low_cpu': {'hosts': []},
                'high_memory': {'hosts': []},
                'medium_memory': {'hosts': []},
                'low_memory': {'hosts': []},
                'minimal_memory': {'hosts': []},
                'tools_ok': {'hosts': []},
                'tools_outdated': {'hosts': []},
                'tools_not_installed': {'hosts': []}
            }
            
            processed_count = 0
            total_vms = len(container.view)
            
            # Processar VMs em lotes para performance
            batch_size = 50
            for i in range(0, total_vms, batch_size):
                batch = container.view[i:i + batch_size]
                
                for vm in batch:
                    vm_data = self.process_vm(vm)
                    if not vm_data:
                        continue
                    
                    vm_name = vm_data['vm_name']
                    processed_count += 1
                    
                    # Adicionar ao inventário
                    self.inventory['_meta']['hostvars'][vm_name] = vm_data
                    groups['vmware_vms']['hosts'].append(vm_name)
                    
                    # Agrupar por estado
                    power_state = vm_data['vm_power_state'].lower()
                    if power_state == 'poweredon':
                        groups['powered_on']['hosts'].append(vm_name)
                    elif power_state == 'poweredoff':
                        groups['powered_off']['hosts'].append(vm_name)
                    elif power_state == 'suspended':
                        groups['suspended']['hosts'].append(vm_name)
                    
                    # Agrupar por SO
                    if vm_data['vm_is_windows']:
                        groups['windows']['hosts'].append(vm_name)
                    elif vm_data['vm_is_linux']:
                        groups['linux']['hosts'].append(vm_name)
                    
                    # Agrupar por ambiente
                    env = vm_data['vm_environment']
                    if env in groups:
                        groups[env]['hosts'].append(vm_name)
                    
                    # Agrupar por recursos
                    cpu_cat = vm_data['vm_cpu_category']
                    mem_cat = vm_data['vm_memory_category']
                    
                    if f'{cpu_cat}_cpu' in groups:
                        groups[f'{cpu_cat}_cpu']['hosts'].append(vm_name)
                    if f'{mem_cat}_memory' in groups:
                        groups[f'{mem_cat}_memory']['hosts'].append(vm_name)
                    
                    # Agrupar por VMware Tools
                    tools_status = vm_data.get('vm_tools_status', '').lower()
                    if tools_status == 'toolsok':
                        groups['tools_ok']['hosts'].append(vm_name)
                    elif tools_status == 'toolsold':
                        groups['tools_outdated']['hosts'].append(vm_name)
                    elif tools_status == 'toolsnotinstalled':
                        groups['tools_not_installed']['hosts'].append(vm_name)
                
                # Log de progresso a cada lote
                if i % (batch_size * 5) == 0:
                    print(f"Processadas {min(i + batch_size, total_vms)}/{total_vms} VMs", file=sys.stderr)
            
            # Remover grupos vazios e adicionar ao inventário
            for group_name, group_data in groups.items():
                if group_name != 'all' and (group_data['hosts'] or group_name == 'vmware_vms'):
                    self.inventory[group_name] = group_data
                    if group_name != 'vmware_vms':
                        groups['all']['children'].append(group_name)
            
            self.inventory['all'] = groups['all']
            
            # Adicionar metadados
            self.inventory['_meta']['inventory_metadata'] = {
                'vcenter_host': self.vcenter_host,
                'datacenter': self.datacenter_name,
                'total_vms': processed_count,
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'groups_created': len(groups['all']['children'])
            }
            
            container.Destroy()
            print(f"Inventário gerado: {processed_count} VMs, {len(groups['all']['children'])} grupos", file=sys.stderr)
            
        except Exception as e:
            print(f"Erro ao gerar inventário: {str(e)}", file=sys.stderr)
        finally:
            try:
                Disconnect(self.service_instance)
            except:
                pass
        
        return self.inventory
    
    def get_host(self, hostname):
        """Retorna informações de um host específico"""
        inventory = self.get_inventory()
        return inventory['_meta']['hostvars'].get(hostname, {})

def main():
    """Função principal - compatível com Ansible inventory script"""
    parser = argparse.ArgumentParser(description='VMware Dynamic Inventory')
    parser.add_argument('--list', action='store_true', help='List all hosts')
    parser.add_argument('--host', help='Get specific host info')
    
    args = parser.parse_args()
    
    try:
        inventory = VMwareInventory()
        
        if args.list:
            # Retornar inventário completo
            result = inventory.get_inventory()
            print(json.dumps(result, indent=2))
        elif args.host:
            # Retornar informações de host específico
            result = inventory.get_host(args.host)
            print(json.dumps(result, indent=2))
        else:
            # Padrão: retornar inventário completo
            result = inventory.get_inventory()
            print(json.dumps(result, indent=2))
            
    except Exception as e:
        print(f"Erro no inventário dinâmico: {str(e)}", file=sys.stderr)
        print(json.dumps({'_meta': {'hostvars': {}}}))
        sys.exit(1)

if __name__ == '__main__':
    main()