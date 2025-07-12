#!/usr/bin/env python3
"""
Script de teste para validar se o inventário gera JSON válido
"""
import sys
import json
import os

# Configurar variáveis de ambiente de teste
os.environ['VCENTER_HOST'] = 'test-host'
os.environ['VCENTER_USER'] = 'test-user'  
os.environ['VCENTER_PASSWORD'] = 'test-pass'
os.environ['DATACENTER_NAME'] = 'test-dc'

def test_json_serialization():
    """Testa se dados problemáticos podem ser sanitizados"""
    
    # Importar a função de sanitização
    sys.path.insert(0, 'inventory_plugins')
    from vmware_dynamic import InventoryModule
    
    plugin = InventoryModule()
    
    # Testar strings problemáticas
    test_strings = [
        'VM com "aspas duplas"',
        "VM com 'aspas simples'",
        'VM com\nquebra de linha',
        'VM com\rcarriage return',
        'VM com caracteres especiais: çãéíóú',
        'VM com {chaves}',
        'VM com barra\\invertida',
        None,
        '',
        'VM normal',
    ]
    
    print("🧪 Testando sanitização de strings...")
    for test_str in test_strings:
        sanitized = plugin._sanitize_string(test_str)
        print(f"  Input:  {repr(test_str)}")
        print(f"  Output: {repr(sanitized)}")
        
        # Testar se pode ser serializado em JSON
        try:
            json.dumps(sanitized)
            print(f"  JSON:   ✅ Válido")
        except Exception as e:
            print(f"  JSON:   ❌ Erro: {e}")
        print()
    
    # Testar dados simulados de VM
    print("🖥️  Testando dados simulados de VM...")
    vm_data = {
        'vm_name': 'TEST-VM"problematica',
        'vm_guest_os': 'Ubuntu Linux (64-bit)',
        'vm_uuid': '12345-67890-abcdef',
        'vm_power_state': 'poweredOn',
        'vm_ip_addresses': ['10.0.0.1', '10.0.0.2'],
        'vm_cpu_count': 4,
        'vm_memory_gb': 8.0,
        'vm_tools_status': 'toolsOk'
    }
    
    # Sanitizar todos os valores string
    sanitized_data = {}
    for k, v in vm_data.items():
        if isinstance(v, str):
            sanitized_data[k] = plugin._sanitize_string(v)
        else:
            sanitized_data[k] = v
    
    try:
        json_output = json.dumps(sanitized_data, indent=2)
        print("✅ Dados de VM serializados com sucesso:")
        print(json_output)
    except Exception as e:
        print(f"❌ Erro na serialização: {e}")

if __name__ == '__main__':
    test_json_serialization()