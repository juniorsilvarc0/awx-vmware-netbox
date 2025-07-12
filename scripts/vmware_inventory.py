#!/usr/bin/env python3
"""
Script de inventário dinâmico VMware para AWX/Ansible
Arquivo: vmware_inventory.py
"""

import json
import sys
import ssl
import time
import logging
from datetime import datetime
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

# Configurar logging para saída em tempo real
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Configurações do vCenter
VCENTER_CONFIG = {
    'host': 'vcsa04.ati.pi.gov.br',
    'user': 'netbox-ro@VSPHERE.LOCAL',
    'pwd': '9i7j&BtSzwZ]',
    'port': 443,
    'datacenter': 'ATI-SLC-HCI'
}

def print_progress(current, total, vm_name=""):
    """Exibe progresso da coleta de VMs"""
    percentage = (current / total) * 100 if total > 0 else 0
    bar_length = 50
    filled_length = int(bar_length * current // total) if total > 0 else 0
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    
    # Truncar nome da VM se muito longo
    display_name = vm_name[:30] + "..." if len(vm_name) > 30 else vm_name
    
    print(f'\rProgresso: |{bar}| {current}/{total} ({percentage:.1f}%) - {display_name}', 
          end='', flush=True, file=sys.stderr)

def get_vm_info(vm, vm_index=0, total_vms=0):
    """Extrai informações detalhadas da VM"""
    try:
        # Atualizar progresso
        print_progress(vm_index, total_vms, vm.name)
        
        summary = vm.summary
        config = vm.config
        runtime = vm.runtime
        guest = vm.guest
        
        # Obter informações de rede
        networks = []
        if vm.network:
            for network in vm.network:
                networks.append(network.name)
        
        # Obter informações de datastore
        datastores = []
        if vm.datastore:
            for ds in vm.datastore:
                datastores.append(ds.name)
        
        # Obter endereços IP
        ip_addresses = []
        if guest and guest.net:
            for nic in guest.net:
                if nic.ipAddress:
                    ip_addresses.extend(nic.ipAddress)
        
        vm_info = {
            'vm_name': vm.name,
            'vm_uuid': config.uuid if config else None,
            'vm_power_state': runtime.powerState if runtime else None,
            'vm_guest_os': config.guestFullName if config else None,
            'vm_cpu_count': summary.config.numCpu if summary.config else None,
            'vm_memory_mb': summary.config.memorySizeMB if summary.config else None,
            'vm_datacenter': vm.summary.runtime.host.parent.parent.parent.name if vm.summary.runtime.host else None,
            'vm_cluster': vm.summary.runtime.host.parent.name if vm.summary.runtime.host else None,
            'vm_folder': vm.parent.name if vm.parent else None,
            'vm_networks': networks,
            'vm_datastores': datastores,
            'vm_annotation': config.annotation if config else None,
            'vm_tools_status': guest.toolsStatus if guest else None,
            'vm_tools_version': guest.toolsVersion if guest else None,
            'vm_ip_addresses': ip_addresses,
            'vm_hostname': guest.hostName if guest else None,
            'ansible_host': ip_addresses[0] if ip_addresses else None
        }
        
        return vm_info
        
    except Exception as e:
        logger.warning(f"Erro ao processar VM {vm.name}: {str(e)}")
        return None

def get_vmware_inventory():
    """Conecta ao vCenter e retorna inventário das VMs"""
    
    start_time = time.time()
    logger.info("🚀 Iniciando coleta do inventário VMware...")
    
    # Desabilitar verificação SSL
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    try:
        # Conectar ao vCenter
        logger.info(f"🔌 Conectando ao vCenter: {VCENTER_CONFIG['host']}")
        si = SmartConnect(
            host=VCENTER_CONFIG['host'],
            user=VCENTER_CONFIG['user'],
            pwd=VCENTER_CONFIG['pwd'],
            port=VCENTER_CONFIG['port'],
            sslContext=context
        )
        logger.info("✅ Conexão estabelecida com sucesso")
        
        # Obter conteúdo do vCenter
        logger.info("📋 Obtendo conteúdo do vCenter...")
        content = si.RetrieveContent()
        
        # Encontrar o datacenter
        logger.info(f"🏢 Procurando datacenter: {VCENTER_CONFIG['datacenter']}")
        datacenter = None
        for dc in content.rootFolder.childEntity:
            if dc.name == VCENTER_CONFIG['datacenter']:
                datacenter = dc
                break
        
        if not datacenter:
            raise Exception(f"❌ Datacenter {VCENTER_CONFIG['datacenter']} não encontrado")
        
        logger.info(f"✅ Datacenter encontrado: {datacenter.name}")
        
        # Obter todas as VMs
        logger.info("🔍 Criando container view para VMs...")
        container = content.viewManager.CreateContainerView(
            datacenter.vmFolder, [vim.VirtualMachine], True
        )
        
        # Contar VMs primeiro
        total_vms = len(container.view)
        logger.info(f"📊 Total de VMs encontradas: {total_vms}")
        
        # Filtrar templates
        vms_to_process = []
        for vm in container.view:
            if not vm.name.startswith('template') and vm.config is not None:
                vms_to_process.append(vm)
        
        logger.info(f"⚙️  VMs a serem processadas: {len(vms_to_process)} (excluindo templates)")
        
        # Inicializar estrutura do inventário
        inventory = {
            '_meta': {
                'hostvars': {}
            },
            'all': {
                'children': []
            },
            'powered_on': {'hosts': []},
            'powered_off': {'hosts': []},
            'suspended': {'hosts': []},
            'windows': {'hosts': []},
            'linux': {'hosts': []},
            'high_cpu': {'hosts': []},
            'high_memory': {'hosts': []},
            'tools_ok': {'hosts': []},
            'tools_outdated': {'hosts': []},
            'tools_not_installed': {'hosts': []},
            'ungrouped': {'hosts': []}
        }
        
        # Contadores para estatísticas
        stats = {
            'processed': 0,
            'powered_on': 0,
            'powered_off': 0,
            'suspended': 0,
            'windows': 0,
            'linux': 0,
            'errors': 0
        }
        
        print(f"\n📈 Processando {len(vms_to_process)} VMs...", file=sys.stderr)
        
        # Processar cada VM
        for index, vm in enumerate(vms_to_process, 1):
            try:
                vm_info = get_vm_info(vm, index, len(vms_to_process))
                
                if vm_info is None:
                    stats['errors'] += 1
                    continue
                
                vm_name = vm_info['vm_name']
                stats['processed'] += 1
                
                # Adicionar às hostvars
                inventory['_meta']['hostvars'][vm_name] = vm_info
                
                # Agrupar por estado de energia
                power_state = vm_info.get('vm_power_state', '').lower()
                if power_state == 'poweredon':
                    inventory['powered_on']['hosts'].append(vm_name)
                    stats['powered_on'] += 1
                elif power_state == 'poweredoff':
                    inventory['powered_off']['hosts'].append(vm_name)
                    stats['powered_off'] += 1
                elif power_state == 'suspended':
                    inventory['suspended']['hosts'].append(vm_name)
                    stats['suspended'] += 1
                
                # Agrupar por sistema operacional
                guest_os = vm_info.get('vm_guest_os', '').lower()
                if 'windows' in guest_os:
                    inventory['windows']['hosts'].append(vm_name)
                    stats['windows'] += 1
                elif any(linux_os in guest_os for linux_os in ['linux', 'ubuntu', 'centos', 'red hat', 'suse']):
                    inventory['linux']['hosts'].append(vm_name)
                    stats['linux'] += 1
                
                # Agrupar por recursos
                cpu_count = vm_info.get('vm_cpu_count', 0)
                memory_mb = vm_info.get('vm_memory_mb', 0)
                
                if cpu_count >= 4:
                    inventory['high_cpu']['hosts'].append(vm_name)
                if memory_mb >= 8192:
                    inventory['high_memory']['hosts'].append(vm_name)
                
                # Agrupar por VMware Tools
                tools_status = vm_info.get('vm_tools_status', '').lower()
                if tools_status == 'toolsok':
                    inventory['tools_ok']['hosts'].append(vm_name)
                elif tools_status == 'toolsold':
                    inventory['tools_outdated']['hosts'].append(vm_name)
                elif tools_status == 'toolsnotinstalled':
                    inventory['tools_not_installed']['hosts'].append(vm_name)
                
            except Exception as e:
                logger.error(f"Erro ao processar VM {vm.name}: {str(e)}")
                stats['errors'] += 1
                continue
        
        # Limpar barra de progresso
        print("", file=sys.stderr)
        
        # Exibir estatísticas
        elapsed_time = time.time() - start_time
        logger.info("📊 Estatísticas do inventário:")
        logger.info(f"   • VMs processadas: {stats['processed']}")
        logger.info(f"   • VMs ligadas: {stats['powered_on']}")
        logger.info(f"   • VMs desligadas: {stats['powered_off']}")
        logger.info(f"   • VMs suspensas: {stats['suspended']}")
        logger.info(f"   • VMs Windows: {stats['windows']}")
        logger.info(f"   • VMs Linux: {stats['linux']}")
        logger.info(f"   • Erros: {stats['errors']}")
        logger.info(f"   • Tempo total: {elapsed_time:.2f} segundos")
        
        # Limpar grupos vazios
        groups_to_remove = []
        for group_name, group_data in inventory.items():
            if group_name != '_meta' and group_name != 'all':
                if isinstance(group_data, dict) and 'hosts' in group_data:
                    if not group_data['hosts']:
                        groups_to_remove.append(group_name)
        
        for group_name in groups_to_remove:
            del inventory[group_name]
        
        # Adicionar grupos não vazios ao 'all'
        inventory['all']['children'] = [group for group in inventory.keys() 
                                       if group not in ['_meta', 'all', 'ungrouped']]
        
        logger.info(f"📋 Grupos criados: {len(inventory['all']['children'])}")
        
        container.Destroy()
        Disconnect(si)
        
        logger.info("✅ Inventário coletado com sucesso!")
        return inventory
        
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao vCenter: {str(e)}")
        return {}

def main():
    """Função principal"""
    logger.info("🔧 VMware Inventory Script v2.0")
    logger.info("=" * 50)
    
    # Verificar argumentos
    if len(sys.argv) > 1:
        if sys.argv[1] == '--list':
            logger.info("📋 Modo: Listar inventário completo")
        elif sys.argv[1] == '--host':
            if len(sys.argv) > 2:
                logger.info(f"🎯 Modo: Informações do host {sys.argv[2]}")
            else:
                logger.error("❌ Nome do host não fornecido")
                sys.exit(1)
        elif sys.argv[1] == '--help':
            print("Uso: python vmware_inventory.py [--list|--host <hostname>|--help]")
            print("  --list: Lista todo o inventário")
            print("  --host <hostname>: Mostra informações de um host específico")
            print("  --help: Mostra esta ajuda")
            sys.exit(0)
    else:
        logger.info("📋 Modo: Listar inventário completo (padrão)")
    
    try:
        inventory = get_vmware_inventory()
        
        if not inventory:
            logger.error("❌ Falha ao obter inventário")
            sys.exit(1)
        
        # Processar argumentos específicos
        if len(sys.argv) > 1 and sys.argv[1] == '--host':
            hostname = sys.argv[2]
            if hostname in inventory.get('_meta', {}).get('hostvars', {}):
                host_vars = inventory['_meta']['hostvars'][hostname]
                logger.info(f"✅ Informações do host {hostname} encontradas")
                print(json.dumps(host_vars, indent=2))
            else:
                logger.error(f"❌ Host {hostname} não encontrado no inventário")
                print(json.dumps({}))
        else:
            # Modo --list (padrão)
            logger.info("📤 Enviando inventário para stdout...")
            print(json.dumps(inventory, indent=2))
            
    except KeyboardInterrupt:
        logger.info("\n⚠️  Operação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()