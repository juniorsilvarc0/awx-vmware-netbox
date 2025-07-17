from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import ssl
import re
import json
import requests
from ansible.plugins.inventory import BaseInventoryPlugin
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

"""
VMware Dynamic Inventory Plugin com Suporte a Tags

IMPORTANTE - Permissões necessárias no vCenter:
Para que as tags funcionem corretamente, o usuário precisa das seguintes permissões:
- System.View (no nível global)
- System.Read (no nível global)
- Global.GlobalTag ou "vSphere Tagging" > "Assign or Unassign vSphere Tag"

Se você estiver recebendo erro 403 ao buscar tags, verifique:
1. No vCenter, vá em Administration > Access Control > Roles
2. Edite o role do usuário ou crie um novo role
3. Adicione as permissões: Global > System > View e Read
4. Em vSphere Tagging, marque "Assign or Unassign vSphere Tag"
5. Aplique o role ao usuário no nível do vCenter (root)
"""

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

    def _get_vcenter_rest_session(self, vcenter_host, username, password):
        """Cria uma sessão REST autenticada com o vCenter"""
        try:
            session = requests.Session()
            session.verify = False
            
            # Desabilitar avisos SSL
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Autenticar - tentar diferentes endpoints
            auth_endpoints = [
                f"https://{vcenter_host}/rest/com/vmware/cis/session",
                f"https://{vcenter_host}/api/session"
            ]
            
            for auth_url in auth_endpoints:
                try:
                    auth_response = session.post(auth_url, auth=(username, password))
                    
                    if auth_response.status_code == 200:
                        # Diferentes versões do vCenter retornam a sessão de formas diferentes
                        if 'value' in auth_response.json():
                            session_id = auth_response.json()['value']
                            session.headers.update({'vmware-api-session-id': session_id})
                        else:
                            session_id = auth_response.json()
                            session.headers.update({'x-vmware-api-session-id': session_id})
                        
                        print(f"✅ Sessão REST criada com sucesso usando {auth_url}")
                        return session
                except Exception as e:
                    print(f"⚠️  Tentativa falhou em {auth_url}: {str(e)}")
                    continue
                    
            print(f"❌ Não foi possível autenticar na API REST")
            return None
            
        except Exception as e:
            print(f"❌ Erro ao criar sessão REST: {str(e)}")
            return None

    def _get_vm_tags_via_rest(self, session, vcenter_host, vm_id):
        """Busca tags de uma VM usando a API REST do vCenter"""
        if not session:
            return []
            
        try:
            # Usar endpoint correto conforme documentação
            tags_url = f"https://{vcenter_host}/rest/vcenter/vm/{vm_id}/tags"
            
            print(f"   🔍 Buscando tags em: {tags_url}")
            response = session.get(tags_url)
            
            if response.status_code == 200:
                tag_ids = response.json().get('value', [])
                print(f"   ✅ Resposta da API: {len(tag_ids)} tag IDs encontrados")
                
                if not tag_ids:
                    print(f"   ℹ️  VM não possui tags atribuídas")
                    return []
                
                tags = []
                # Para cada tag ID, buscar detalhes usando a API CIS
                for tag_id in tag_ids:
                    print(f"   🔍 Buscando detalhes da tag: {tag_id}")
                    
                    # Endpoints para detalhes da tag
                    tag_detail_endpoints = [
                        f"https://{vcenter_host}/rest/com/vmware/cis/tagging/tag/id:{tag_id}",
                        f"https://{vcenter_host}/api/cis/tagging/tag/id:{tag_id}",
                        f"https://{vcenter_host}/rest/com/vmware/cis/tagging/tag/{tag_id}",
                        f"https://{vcenter_host}/api/cis/tagging/tag/{tag_id}"
                    ]
                    
                    tag_found = False
                    for tag_details_url in tag_detail_endpoints:
                        try:
                            print(f"     🔍 Tentando: {tag_details_url}")
                            tag_response = session.get(tag_details_url)
                            
                            if tag_response.status_code == 200:
                                tag_data = tag_response.json().get('value', {})
                                print(f"     ✅ Tag encontrada: {tag_data}")
                                
                                # Buscar detalhes da categoria
                                category_id = tag_data.get('category_id')
                                category_name = None
                                
                                if category_id:
                                    category_endpoints = [
                                        f"https://{vcenter_host}/rest/com/vmware/cis/tagging/category/id:{category_id}",
                                        f"https://{vcenter_host}/api/cis/tagging/category/id:{category_id}",
                                        f"https://{vcenter_host}/rest/com/vmware/cis/tagging/category/{category_id}",
                                        f"https://{vcenter_host}/api/cis/tagging/category/{category_id}"
                                    ]
                                    
                                    for category_url in category_endpoints:
                                        try:
                                            category_response = session.get(category_url)
                                            if category_response.status_code == 200:
                                                category_data = category_response.json().get('value', {})
                                                category_name = category_data.get('name')
                                                print(f"     ✅ Categoria encontrada: {category_name}")
                                                break
                                        except Exception as cat_e:
                                            print(f"     ⚠️  Erro na categoria: {str(cat_e)}")
                                            continue
                                
                                tag_info = {
                                    'name': self._sanitize_string(tag_data.get('name')),
                                    'category': self._sanitize_string(category_name),
                                    'description': self._sanitize_string(tag_data.get('description'))
                                }
                                
                                if tag_info['name']:
                                    tags.append(tag_info)
                                    print(f"   ✅ Tag processada: {tag_info['name']} (categoria: {tag_info['category']})")
                                
                                tag_found = True
                                break
                                
                            elif tag_response.status_code == 403:
                                print(f"     ⚠️  Erro 403: Sem permissão para acessar detalhes da tag")
                            elif tag_response.status_code == 404:
                                print(f"     ⚠️  Tag {tag_id} não encontrada")
                            else:
                                print(f"     ⚠️  Status {tag_response.status_code}: {tag_response.text}")
                                
                        except Exception as e:
                            print(f"     ❌ Erro ao buscar tag: {str(e)}")
                            continue
                    
                    if not tag_found:
                        print(f"   ⚠️  Não foi possível obter detalhes da tag {tag_id}")
                
                return tags
                
            elif response.status_code == 403:
                print(f"   ❌ Erro 403: Usuário sem permissão. Verifique permissões 'System.View' no vCenter")
            elif response.status_code == 404:
                print(f"   ❌ Erro 404: VM {vm_id} não encontrada")
            else:
                print(f"   ❌ Erro {response.status_code}: {response.text}")
            
            return []
            
        except Exception as e:
            print(f"❌ Erro geral ao buscar tags via REST: {str(e)}")
            return []

    def _get_vm_tags_via_pyvmomi(self, content, vm):
        """Busca tags de uma VM usando pyVmomi como alternativa"""
        try:
            # Obter o gerenciador de tags
            tag_manager = content.tagging.TagManager if hasattr(content, 'tagging') else None
            if not tag_manager:
                # Tentar método alternativo
                tag_manager = content.tagManager if hasattr(content, 'tagManager') else None
            
            if not tag_manager:
                print("   ⚠️  Tag Manager não disponível nesta versão do vCenter")
                return []
            
            # Obter tags associadas à VM
            tags = []
            vm_tags = tag_manager.ListAttachedTags(vm)
            
            for tag_id in vm_tags:
                try:
                    tag = tag_manager.GetTag(tag_id)
                    category = tag_manager.GetCategory(tag.categoryId)
                    
                    tag_info = {
                        'name': self._sanitize_string(tag.name),
                        'category': self._sanitize_string(category.name),
                        'description': self._sanitize_string(tag.description)
                    }
                    
                    if tag_info['name']:
                        tags.append(tag_info)
                        print(f"   ✅ Tag encontrada via pyVmomi: {tag_info['name']} ({tag_info['category']})")
                        
                except Exception as e:
                    print(f"   ⚠️  Erro ao processar tag {tag_id}: {str(e)}")
                    continue
                    
            return tags
            
        except AttributeError:
            print("   ℹ️  API de tags não disponível via pyVmomi nesta versão")
            return []
        except Exception as e:
            print(f"   ⚠️  Erro ao buscar tags via pyVmomi: {str(e)}")
            return []

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

        # Criar sessão REST para buscar tags
        print("🔑 Criando sessão REST com vCenter...")
        rest_session = self._get_vcenter_rest_session(
            vcenter_config['host'],
            vcenter_config['user'],
            vcenter_config['pwd']
        )
        
        if not rest_session:
            print("""
⚠️  AVISO: Não foi possível criar sessão REST. As tags não serão coletadas.
   
   Se você precisa das tags, verifique:
   1. Permissões do usuário no vCenter (precisa de System.View e Global.GlobalTag)
   2. Versão do vCenter (6.5 ou superior para API REST)
   3. Conectividade com a porta 443 do vCenter
   
   O inventário continuará sem as tags...
""")

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

                # Buscar tags via API REST
                vm_tags = []
                if rest_session and hasattr(vm, '_moId'):
                    print(f"🔍 Buscando tags para VM: {name} (ID: {vm._moId})")
                    vm_tags = self._get_vm_tags_via_rest(rest_session, vcenter_config['host'], vm._moId)
                    
                    # Se falhar via REST, tentar via pyVmomi
                    if not vm_tags:
                        print("   🔄 Tentando método alternativo via pyVmomi...")
                        vm_tags = self._get_vm_tags_via_pyvmomi(content, vm)
                    
                    print(f"✅ VM {name}: {len(vm_tags)} tags encontradas")

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
                
                # Criar grupos por tags
                for tag in vm_tags:
                    if tag.get('name'):
                        # Criar nome de grupo baseado na tag
                        tag_group_name = f"tag_{self._sanitize_string(tag['name']).lower().replace(' ', '_')}"
                        self.inventory.add_group(tag_group_name)
                        self.inventory.add_child(tag_group_name, safe_name)
                        
                        # Se houver categoria, criar grupo por categoria também
                        if tag.get('category'):
                            category_group_name = f"category_{self._sanitize_string(tag['category']).lower().replace(' ', '_')}"
                            self.inventory.add_group(category_group_name)
                            self.inventory.add_child(category_group_name, safe_name)
            
            except Exception as e:
                # Log do erro mas continua processando outras VMs
                print(f"Erro processando VM {getattr(vm, 'name', 'unknown')}: {str(e)}")
                continue

        container.Destroy()
        Disconnect(si)
        
        # Fechar sessão REST
        if rest_session:
            try:
                rest_session.delete(f"https://{vcenter_config['host']}/rest/com/vmware/cis/session")
            except:
                pass
        
        # Limpar variáveis problemáticas que o AWX pode injetar
        self._cleanup_awx_variables()
        
        # Validação final de integridade JSON
        self._validate_inventory_json()
        
        # Limpeza final - remover qualquer host que ainda tenha problemas
        self._final_cleanup()