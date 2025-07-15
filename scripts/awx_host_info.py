#!/usr/bin/env python3
"""
Script para consulta de informações de host via API do AWX
Similar ao teste.sh, mas em Python com melhor tratamento de erros
"""

import json
import requests
import sys
from typing import Dict, Any, Optional


class AWXHostInfo:
    def __init__(self, awx_url: str, username: str, password: str, inventory_id: int):
        self.awx_url = awx_url.rstrip('/')
        self.username = username
        self.password = password
        self.inventory_id = inventory_id
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def awx_api(self, endpoint: str) -> Dict[str, Any]:
        """Faz requisição para API do AWX"""
        try:
            url = f"{self.awx_url}/api/v2/{endpoint}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro na requisição: {e}")
            return {}
    
    def find_host(self, host_name: str) -> Optional[Dict[str, Any]]:
        """Busca host no inventário"""
        print(f"🔍 Buscando host: {host_name}")
        print(f"📦 Inventário ID: {self.inventory_id} (VMware Inventory)")
        print("=" * 50)
        
        print("1️⃣ Buscando host no inventário...")
        response = self.awx_api(f"inventories/{self.inventory_id}/hosts/?name={host_name}")
        
        if not response or response.get('count', 0) == 0:
            print(f"❌ Host '{host_name}' não encontrado")
            self.list_available_hosts()
            return None
        
        host = response['results'][0]
        print("✅ Host encontrado:")
        print(f"   ID: {host['id']}")
        print(f"   Nome: {host['name']}")
        
        return host
    
    def get_host_details(self, host_id: int) -> Dict[str, Any]:
        """Obtém detalhes completos do host"""
        print("\n2️⃣ Obtendo variáveis do host...")
        host_details = self.awx_api(f"hosts/{host_id}/")
        
        if host_details:
            print("📋 Detalhes do host:")
            details = {
                'id': host_details.get('id'),
                'name': host_details.get('name'),
                'description': host_details.get('description'),
                'enabled': host_details.get('enabled'),
                'variables': host_details.get('variables', {})
            }
            print(json.dumps(details, indent=2, ensure_ascii=False))
            
            # Mostrar variáveis
            print("\n🔧 Variáveis do host:")
            variables = host_details.get('variables', {})
            if variables:
                print(json.dumps(variables, indent=2, ensure_ascii=False))
            else:
                print("ℹ️ Nenhuma variável definida no host")
        
        return host_details
    
    def get_ansible_facts(self, host_id: int) -> Dict[str, Any]:
        """Obtém facts do Ansible"""
        print("\n3️⃣ Verificando Ansible Facts...")
        facts = self.awx_api(f"hosts/{host_id}/ansible_facts/")
        
        if facts:
            facts_count = len(facts)
            print(f"✅ Facts disponíveis ({facts_count} chaves)")
            
            # Mostrar facts importantes
            print("\n🖥️ Informações do sistema:")
            system_info = {
                'hostname': facts.get('ansible_hostname'),
                'fqdn': facts.get('ansible_fqdn'),
                'os_family': facts.get('ansible_os_family'),
                'distribution': facts.get('ansible_distribution'),
                'version': facts.get('ansible_distribution_version'),
                'architecture': facts.get('ansible_architecture'),
                'cores': facts.get('ansible_processor_cores'),
                'memory_mb': facts.get('ansible_memtotal_mb'),
                'ip_address': facts.get('ansible_default_ipv4', {}).get('address')
            }
            print(json.dumps(system_info, indent=2, ensure_ascii=False))
            
            # IPs das interfaces
            print("\n🌐 Interfaces de rede:")
            interfaces = facts.get('ansible_interfaces', [])
            for interface in interfaces:
                interface_data = facts.get(f'ansible_{interface}', {})
                if 'ipv4' in interface_data:
                    ip = interface_data['ipv4'].get('address', 'sem IP')
                    print(f"   {interface}: {ip}")
        else:
            print("ℹ️ Facts não disponíveis")
        
        return facts
    
    def get_host_groups(self, host_id: int) -> Dict[str, Any]:
        """Obtém grupos do host"""
        print("\n4️⃣ Grupos do host...")
        groups = self.awx_api(f"hosts/{host_id}/groups/")
        
        if groups and groups.get('count', 0) > 0:
            group_count = groups['count']
            print(f"✅ Host pertence a {group_count} grupo(s):")
            for group in groups.get('results', []):
                print(f"   👥 {group['name']} (ID: {group['id']})")
        else:
            print("ℹ️ Host não pertence a nenhum grupo")
        
        return groups
    
    def list_available_hosts(self):
        """Lista hosts disponíveis no inventário"""
        print("\n🖥️ Hosts disponíveis no inventário VMware Inventory:")
        response = self.awx_api(f"inventories/{self.inventory_id}/hosts/")
        
        if response and response.get('results'):
            for host in response['results']:
                print(f"   • {host['name']} (ID: {host['id']})")
    
    def print_useful_commands(self, host_id: int):
        """Imprime comandos úteis para consulta"""
        print("\n" + "=" * 50)
        print("🎯 Comandos úteis:")
        print()
        print("# Variáveis do host")
        print(f"curl -u '{self.username}:{self.password}' '{self.awx_url}/api/v2/hosts/{host_id}/' | jq '.variables'")
        print()
        print("# Facts do host")
        print(f"curl -u '{self.username}:{self.password}' '{self.awx_url}/api/v2/hosts/{host_id}/ansible_facts/'")
    
    def get_host_info(self, host_name: str):
        """Método principal para obter informações do host"""
        host = self.find_host(host_name)
        if not host:
            return
        
        host_id = host['id']
        
        # Obter informações detalhadas
        self.get_host_details(host_id)
        self.get_ansible_facts(host_id)
        self.get_host_groups(host_id)
        self.print_useful_commands(host_id)


def main():
    # Configurações (devem ser passadas como variáveis de ambiente ou argumentos)
    AWX_URL = "http://10.0.100.159:8013"
    USERNAME = "junior"
    PASSWORD = "JR83silV@83"
    INVENTORY_ID = 3  # VMware Inventory
    
    # Host a ser consultado
    if len(sys.argv) > 1:
        HOST_NAME = sys.argv[1]
    else:
        HOST_NAME = "ADAASD-SIDAPI01"
    
    # Criar instância e executar consulta
    awx_client = AWXHostInfo(AWX_URL, USERNAME, PASSWORD, INVENTORY_ID)
    awx_client.get_host_info(HOST_NAME)


if __name__ == "__main__":
    main()