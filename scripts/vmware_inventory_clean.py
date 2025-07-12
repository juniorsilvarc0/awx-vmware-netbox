#!/usr/bin/env python3
"""
Script de inventário VMware limpo - sem variáveis problemáticas do AWX
Baseado no script fornecido pelo usuário, adaptado para uso no AWX
"""
import ssl
import json
import os
import sys
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

def get_vcenter_config():
    """Obter configuração do vCenter via variáveis de ambiente"""
    config = {
        'host': os.environ.get('VCENTER_HOST'),
        'user': os.environ.get('VCENTER_USER'), 
        'pwd': os.environ.get('VCENTER_PASSWORD'),
        'port': int(os.environ.get('VCENTER_PORT', 443)),
        'datacenter': os.environ.get('DATACENTER_NAME', 'ATI-SLC-HCI')
    }
    
    missing = [k for k, v in config.items() if v is None and k != 'port']
    if missing:
        raise Exception(f"Variáveis de ambiente faltando: {', '.join(missing)}")
    
    return config

def sanitize_string(value):
    """Sanitizar strings para evitar problemas JSON"""
    if value is None:
        return None
    if isinstance(value, str):
        # Remove caracteres problemáticos
        value = value.replace('"', "'").replace('\n', ' ').replace('\r', ' ')
        value = value.replace('\\', '/').replace('{', '').replace('}', '')
        return value.strip()
    return value

def get_vm_data(vm):
    """Extrair dados da VM de forma limpa"""
    try:
        name = sanitize_string(vm.name)
        if not name or vm.config.template:
            return None
            
        config = vm.config
        summary = vm.summary
        runtime = vm.runtime
        guest = vm.guest
        
        # Coletar IPs
        ip_addresses = []
        if guest and guest.net:
            for nic in guest.net:
                if nic.ipAddress:
                    ip_addresses.extend([ip for ip in nic.ipAddress if ip and not ip.startswith('fe80')])
        
        # Calcular recursos
        memory_gb = round((summary.config.memorySizeMB / 1024), 1) if summary.config else 0
        
        # Determinar ambiente baseado no nome
        name_lower = name.lower()
        if 'prod' in name_lower:
            environment = 'production'
            criticality = 'high'
        elif 'dev' in name_lower:
            environment = 'development' 
            criticality = 'low'
        elif 'test' in name_lower:
            environment = 'testing'
            criticality = 'medium'
        elif 'stg' in name_lower:
            environment = 'staging'
            criticality = 'medium'
        else:
            environment = 'unknown'
            criticality = 'low'
        
        # Dados da VM (APENAS variáveis VMware, SEM variáveis AWX)
        vm_data = {
            'ansible_host': ip_addresses[0] if ip_addresses else None,
            'vm_name': name,
            'vm_uuid': sanitize_string(config.uuid),
            'vm_power_state': sanitize_string(runtime.powerState),
            'vm_guest_os': sanitize_string(config.guestFullName),
            'vm_guest_family': sanitize_string(guest.guestFamily if guest else None),
            'vm_cpu_count': summary.config.numCpu if summary.config else 0,
            'vm_memory_mb': summary.config.memorySizeMB if summary.config else 0,
            'vm_memory_gb': memory_gb,
            'vm_datacenter': sanitize_string(runtime.host.parent.parent.parent.name if runtime and runtime.host else None),
            'vm_cluster': sanitize_string(runtime.host.parent.name if runtime and runtime.host else None),
            'vm_folder': sanitize_string(vm.parent.name if vm.parent else None),
            'vm_ip_addresses': ip_addresses,
            'vm_hostname': sanitize_string(guest.hostName if guest else None),
            'vm_tools_status': sanitize_string(guest.toolsStatus if guest else None),
            'vm_tools_running': guest.toolsStatus == 'toolsOk' if guest else False,
            'vm_environment': environment,
            'vm_criticality': criticality,
            'vm_is_windows': 'windows' in (config.guestFullName.lower() if config and config.guestFullName else ''),
            'vm_is_linux': any(x in (config.guestFullName.lower() if config and config.guestFullName else '') 
                             for x in ['linux', 'ubuntu', 'centos', 'red hat', 'suse', 'debian']),
            'vm_cpu_category': 'high' if summary.config.numCpu >= 8 else 'medium' if summary.config.numCpu >= 4 else 'low',
            'vm_memory_category': 'high' if memory_gb >= 16 else 'medium' if memory_gb >= 8 else 'low' if memory_gb >= 4 else 'minimal'
        }
        
        return vm_data
        
    except Exception as e:
        print(f"Erro processando VM {getattr(vm, 'name', 'unknown')}: {str(e)}", file=sys.stderr)
        return None

def generate_inventory():
    """Gerar inventário limpo"""
    config = get_vcenter_config()
    
    # Conectar ao vCenter
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    si = SmartConnect(
        host=config['host'],
        user=config['user'], 
        pwd=config['pwd'],
        port=config['port'],
        sslContext=context
    )
    
    content = si.RetrieveContent()
    datacenter = next(
        (dc for dc in content.rootFolder.childEntity if dc.name == config['datacenter']),
        None
    )
    if not datacenter:
        raise Exception(f"Datacenter {config['datacenter']} não encontrado")
    
    # Obter VMs
    container = content.viewManager.CreateContainerView(
        datacenter.vmFolder, [vim.VirtualMachine], True
    )
    
    # Estrutura do inventário
    inventory = {
        '_meta': {
            'hostvars': {}
        },
        'all': {
            'children': ['ungrouped']
        },
        'powered_on': {'hosts': []},
        'powered_off': {'hosts': []},
        'suspended': {'hosts': []},
        'windows': {'hosts': []},
        'linux': {'hosts': []},
        'production': {'hosts': []},
        'development': {'hosts': []},
        'testing': {'hosts': []},
        'staging': {'hosts': []},
        'unknown': {'hosts': []},
        'ungrouped': {'hosts': []}
    }
    
    processed_count = 0
    for vm in container.view:
        try:
            vm_data = get_vm_data(vm)
            if not vm_data:
                continue
                
            host_name = vm_data['vm_name']
            
            # Adicionar host vars (SEM variáveis AWX problemáticas)
            inventory['_meta']['hostvars'][host_name] = vm_data
            
            # Adicionar a grupos baseado no estado
            power_state = vm_data.get('vm_power_state', '')
            if power_state == 'poweredOn':
                inventory['powered_on']['hosts'].append(host_name)
            elif power_state == 'poweredOff':
                inventory['powered_off']['hosts'].append(host_name)
            elif power_state == 'suspended':
                inventory['suspended']['hosts'].append(host_name)
            
            # Grupos por OS
            if vm_data.get('vm_is_windows'):
                inventory['windows']['hosts'].append(host_name)
            elif vm_data.get('vm_is_linux'):
                inventory['linux']['hosts'].append(host_name)
            
            # Grupos por ambiente
            environment = vm_data.get('vm_environment', 'unknown')
            if environment in inventory:
                inventory[environment]['hosts'].append(host_name)
            
            processed_count += 1
            
        except Exception as e:
            print(f"Erro processando VM: {str(e)}", file=sys.stderr)
            continue
    
    container.Destroy()
    Disconnect(si)
    
    print(f"Processadas {processed_count} VMs com sucesso", file=sys.stderr)
    return inventory

if __name__ == '__main__':
    try:
        inventory = generate_inventory()
        print(json.dumps(inventory, indent=2))
    except Exception as e:
        print(f"Erro fatal: {str(e)}", file=sys.stderr)
        sys.exit(1)