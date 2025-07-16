from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import ssl
import re
import json
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
            # Remove caracteres de controle e caracteres problemáticos
            value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
            
            # Remove sequências problemáticas que podem quebrar JSON
            problematic_patterns = [
                r'"[^"]*"[^"]*"[^"]*"',  # Múltiplas aspas duplas
                r"'[^']*'[^']*'[^']*'",  # Múltiplas aspas simples
                r'\{[^}]*\}[^}]*\}',      # Múltiplas chaves
                r'}}}}',                  # Sequência de chaves problemática
                r'""',                    # Aspas duplas vazias
                r"''"                     # Aspas simples vazias
            ]
            
            for pattern in problematic_patterns:
                value = re.sub(pattern, '', value)
            
            # Sanitização básica
            value = value.replace('"', "'").replace("'", "").replace('\n', ' ').replace('\r', ' ')
            value = value.replace('\\', '/').replace('{', '').replace('}', '')
            
            # Remove espaços múltiplos e caracteres não ASCII problemáticos
            value = re.sub(r'\s+', ' ', value)
            value = re.sub(r'[^\x20-\x7E]', '', value)  # Apenas ASCII printável
            
            # Remove caracteres que podem quebrar parsing JSON/YAML
            value = value.replace(':', '').replace(',', '').replace('[', '').replace(']', '')
            
            return value.strip()
        return value

    def _cleanup_awx_variables(self):
        """Remove variáveis problemáticas que o AWX pode injetar automaticamente"""
        print("🧹 Executando limpeza agressiva de variáveis AWX...")
        
        for host_name in list(self.inventory.hosts.keys()):
            host = self.inventory.hosts[host_name]
            # Criar cópia das variáveis para iteração segura
            vars_to_remove = []
            
            for var_name, var_value in list(host.vars.items()):
                should_remove = False
                
                # 1. Remover qualquer variável que comece com padrões AWX
                if any(var_name.startswith(prefix) for prefix in ['remote_', 'tower_', 'awx_']):
                    should_remove = True
                    print(f"🚫 Removendo variável AWX: {var_name} do host {host_name}")
                
                # 2. Remover variáveis problemáticas específicas
                problematic_vars = [
                    'remote_host_enabled', 'remote_host_id', 'remote_tower_enabled', 'remote_tower_id',
                    'tower_enabled', 'tower_id', 'awx_enabled', 'awx_id', 'ansible_host_key_checking',
                    'ansible_ssh_common_args', 'ansible_ssh_extra_args', 'ansible_connection_timeout'
                ]
                if var_name in problematic_vars:
                    should_remove = True
                    print(f"🚫 Removendo variável problemática: {var_name} do host {host_name}")
                
                # 3. Remover variáveis com valores que contêm caracteres problemáticos
                if isinstance(var_value, str):
                    problematic_patterns = ['"}}}}', '"}', "'}", "{{", "}}", '564dba5b-c886-5576-5ce2-8e7f4889d270']
                    if any(pattern in var_value for pattern in problematic_patterns):
                        should_remove = True
                        print(f"🚫 Removendo variável com padrão problemático: {var_name} do host {host_name}")
                
                # 4. Remover variáveis com IDs suspeitos
                if isinstance(var_value, (int, str)) and str(var_value) in ['1063', '1064']:
                    should_remove = True
                    print(f"🚫 Removendo variável com ID suspeito: {var_name}={var_value} do host {host_name}")
                
                if should_remove:
                    vars_to_remove.append(var_name)
            
            # Remover variáveis identificadas
            for var_name in vars_to_remove:
                if var_name in host.vars:
                    del host.vars[var_name]
        
        print(f"✅ Limpeza concluída para {len(self.inventory.hosts)} hosts")

    def _validate_inventory_json(self):
        """Valida se o inventário pode ser serializado como JSON válido"""
        try:
            # Tenta serializar o inventário como JSON
            inventory_dict = {}
            for host_name in self.inventory.hosts:
                host = self.inventory.hosts[host_name]
                host_vars = {}
                for k, v in host.vars.items():
                    # Garantir que todos os valores são JSON serializáveis
                    if isinstance(v, str):
                        v = self._sanitize_string(v)
                    host_vars[k] = v
                inventory_dict[host_name] = host_vars
            
            # Testa serialização JSON
            json.dumps(inventory_dict)
            
        except (TypeError, ValueError) as e:
            print(f"Aviso: Problema de serialização JSON detectado: {e}")
            # Remove hosts problemáticos se necessário
            self._remove_problematic_hosts()

    def _remove_problematic_hosts(self):
        """Remove hosts que não podem ser serializados como JSON"""
        hosts_to_remove = []
        for host_name in self.inventory.hosts:
            try:
                host = self.inventory.hosts[host_name]
                json.dumps(dict(host.vars))
            except (TypeError, ValueError):
                hosts_to_remove.append(host_name)
                print(f"Removendo host problemático: {host_name}")
        
        for host_name in hosts_to_remove:
            self.inventory.remove_host(host_name)
    
    def _final_cleanup(self):
        """Limpeza final AGRESSIVA para garantir JSON válido"""
        print("🔥 Executando limpeza final agressiva...")
        
        hosts_to_remove = []
        for host_name in list(self.inventory.hosts.keys()):
            host = self.inventory.hosts[host_name]
            vars_to_remove = []
            
            # Lista COMPLETA de todas as variáveis e padrões problemáticos
            for var_name, var_value in list(host.vars.items()):
                should_remove = False
                
                # Remover QUALQUER variável AWX/Tower/Remote
                awx_patterns = ['remote_', 'tower_', 'awx_', 'ansible_host_key', 'ansible_ssh']
                if any(pattern in var_name.lower() for pattern in awx_patterns):
                    should_remove = True
                
                # Remover variáveis com valores suspeitos
                if isinstance(var_value, str):
                    suspicious_content = [
                        '564dba5b-c886-5576-5ce2-8e7f4889d270', '564d8ad9-0b54-c1b0-7658-8a0fd40a73f1',
                        '"remote_host_enabled"', '"remote_tower_enabled"', '}}}}', 'No closing quotation',
                        '"}}', '"}', '{{', '}}'
                    ]
                    if any(content in str(var_value) for content in suspicious_content):
                        should_remove = True
                
                # Remover IDs específicos problemáticos
                if var_name in ['remote_host_id', 'remote_tower_id'] or str(var_value) in ['1063', '1064']:
                    should_remove = True
                
                if should_remove:
                    vars_to_remove.append(var_name)
                    print(f"🔥 REMOVENDO FINAL: {var_name}={var_value} do host {host_name}")
            
            # Aplicar remoções
            for var_name in vars_to_remove:
                if var_name in host.vars:
                    del host.vars[var_name]
            
            # Teste final de serialização JSON
            try:
                test_data = {host_name: dict(host.vars)}
                json.dumps(test_data)
            except (TypeError, ValueError, UnicodeDecodeError) as e:
                print(f"❌ Host {host_name} ainda tem problemas de JSON, removendo completamente: {e}")
                hosts_to_remove.append(host_name)
        
        # Remover hosts que ainda têm problemas
        for host_name in hosts_to_remove:
            self.inventory.remove_host(host_name)
            print(f"🗑️ Removido host problemático: {host_name}")
        
        print(f"✅ Limpeza final concluída. Hosts restantes: {len(self.inventory.hosts)}")

    def _monkey_patch_awx_injection(self):
        """Monkey patch para interceptar injeção de variáveis do AWX"""
        print("🐒 Aplicando monkey patch para bloquear injeção AWX...")
        
        # Salvar referência original do método set_variable
        original_set_variable = self.inventory.set_variable
        
        def blocked_set_variable(host, var, value):
            """Versão bloqueada do set_variable que filtra variáveis AWX"""
            # Lista de variáveis a serem bloqueadas
            blocked_vars = [
                'remote_host_enabled', 'remote_host_id', 'remote_tower_enabled', 'remote_tower_id',
                'tower_enabled', 'tower_id', 'awx_enabled', 'awx_id'
            ]
            
            # Bloquear variáveis problemáticas
            if var in blocked_vars:
                print(f"🚫 BLOQUEADO: Tentativa de injetar {var}={value} no host {host}")
                return  # NÃO adicionar a variável
            
            # Bloquear valores que contenham sequências problemáticas
            if isinstance(value, str) and any(problem in str(value) for problem in ['564dba5b-c886-5576-5ce2-8e7f4889d270', '}}}}', '"remote_']):
                print(f"🚫 BLOQUEADO: Variável {var} com valor suspeito no host {host}")
                return  # NÃO adicionar a variável
            
            # Se passou nos filtros, permitir
            return original_set_variable(host, var, value)
        
        # Aplicar o monkey patch
        self.inventory.set_variable = blocked_set_variable
        print("✅ Monkey patch aplicado com sucesso")

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

                # Calcular capacidade total do disco
                disk_total_gb = 0
                if config and config.hardware and config.hardware.device:
                    for device in config.hardware.device:
                        if hasattr(device, 'capacityInKB') and device.capacityInKB:
                            disk_total_gb += round((device.capacityInKB / 1024 / 1024), 1)

                # Coletar tags atribuídas à VM
                vm_tags = []
                try:
                    if hasattr(vm, 'tag') and vm.tag:
                        for tag in vm.tag:
                            try:
                                tag_info = {
                                    'name': self._sanitize_string(tag.name) if hasattr(tag, 'name') else None,
                                    'category': self._sanitize_string(tag.category.name) if hasattr(tag, 'category') and tag.category and hasattr(tag.category, 'name') else None,
                                    'description': self._sanitize_string(tag.description) if hasattr(tag, 'description') else None
                                }
                                # Apenas adicionar se tem pelo menos o nome
                                if tag_info['name']:
                                    vm_tags.append(tag_info)
                            except Exception as e:
                                print(f"Erro processando tag para VM {name}: {str(e)}")
                                continue
                except Exception as e:
                    print(f"Erro coletando tags para VM {name}: {str(e)}")
                    vm_tags = []

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
                    'vm_memory_category': 'high' if memory_gb >= 16 else 'medium' if memory_gb >= 8 else 'low' if memory_gb >= 4 else 'minimal',
                    'vm_disk_total_gb': disk_total_gb,
                    'vm_disk_category': 'high' if disk_total_gb >= 1000 else 'medium' if disk_total_gb >= 500 else 'low' if disk_total_gb >= 100 else 'minimal',
                    'vm_tags': vm_tags
                }

                # Sanitizar nome do host para evitar problemas
                safe_name = self._sanitize_string(name)
                if not safe_name:
                    safe_name = f"vm_{config.uuid[:8]}" if config and config.uuid else f"unknown_vm_{len(self.inventory.hosts)}"
                
                self.inventory.add_host(safe_name)
                
                # Adicionar APENAS variáveis VMware válidas - BLOQUEAR completamente variáveis AWX
                awx_blocked_vars = [
                    'remote_host_enabled', 'remote_host_id', 'remote_tower_enabled', 'remote_tower_id',
                    'tower_enabled', 'tower_id', 'awx_enabled', 'awx_id', 
                    'ansible_host_key_checking', 'ansible_ssh_common_args'
                ]
                
                # FILTRO RIGOROSO: Apenas variáveis que começam com 'vm_' ou 'ansible_host'
                allowed_prefixes = ['vm_', 'ansible_host']
                
                for k, v in vm_data.items():
                    # Bloquear qualquer variável que não seja explicitamente VMware
                    if k in awx_blocked_vars:
                        print(f"🚫 BLOQUEADO: {k} (variável AWX)")
                        continue
                    
                    # Permitir apenas variáveis com prefixos seguros
                    if not any(k.startswith(prefix) for prefix in allowed_prefixes):
                        print(f"🚫 BLOQUEADO: {k} (prefixo não permitido)")
                        continue
                    
                    # Bloquear se contém padrões AWX no nome
                    if any(blocked in str(k).lower() for blocked in ['remote_', 'tower_', 'awx_']):
                        print(f"🚫 BLOQUEADO: {k} (padrão AWX detectado)")
                        continue
                    
                    if v is not None:
                        # Sanitizar valores que podem conter caracteres especiais
                        if isinstance(v, str):
                            v = self._sanitize_string(v)
                        self.inventory.set_variable(safe_name, k, v)
                        print(f"✅ PERMITIDO: {k}={v}")

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
        
        # Limpar variáveis problemáticas que o AWX pode injetar
        self._cleanup_awx_variables()
        
        # Validação final de integridade JSON
        self._validate_inventory_json()
        
        # Limpeza final - remover qualquer host que ainda tenha problemas
        self._final_cleanup()
        
        # ÚLTIMA tentativa - interceptar método get_option para bloquear injeção AWX
        self._monkey_patch_awx_injection()
