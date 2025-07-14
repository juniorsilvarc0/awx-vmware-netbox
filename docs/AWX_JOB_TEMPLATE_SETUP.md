# 🚀 Configuração do Job Template no AWX

## 📋 Visão Geral

Este guia explica como configurar um Job Template no AWX para sincronizar o inventário VMware com o NetBox de forma automatizada.

## 🔧 Pré-requisitos

### 1. Repositório Git
- Projeto disponível em repositório Git (GitHub, GitLab, etc.)
- Acesso de leitura configurado no AWX

### 2. Credenciais Necessárias

#### **NetBox API Credential**
Você precisa criar um **Custom Credential Type** no AWX:

**Configuração do Custom Credential Type:**

```yaml
# INPUT CONFIGURATION
fields:
  - id: netbox_api_url
    type: string
    label: NetBox API URL
    help_text: "URL da API do NetBox (ex: https://netbox.example.com)"
  - id: netbox_api_token
    type: string
    label: NetBox API Token
    secret: true
    help_text: "Token de acesso à API do NetBox"
required:
  - netbox_api_url
  - netbox_api_token

# INJECTOR CONFIGURATION
extra_vars:
  netbox_api_url: "{{ netbox_api_url }}"
  netbox_api_token: "{{ netbox_api_token }}"
```

## 📦 Configuração Passo a Passo

### 1. **Criar Project**

```yaml
Name: AWX to NetBox Sync
Description: Sincronização do inventário VMware para NetBox
Organization: Default
SCM Type: Git
SCM URL: https://github.com/seu-usuario/awx-vmware-netbox.git
SCM Branch/Tag/Commit: main
SCM Update Options:
  ✅ Clean
  ✅ Delete on Update
  ✅ Update Revision on Launch
```

### 2. **Criar Custom Credential Type**

```yaml
Name: NetBox API
Description: Credenciais para API do NetBox
Kind: Cloud
Input Configuration: [Cole o YAML acima]
Injector Configuration: [Cole o YAML acima]
```

### 3. **Criar Credential**

```yaml
Name: NetBox Production
Description: Credenciais do NetBox de produção
Organization: Default
Credential Type: NetBox API
Details:
  NetBox API URL: https://seu-netbox.com
  NetBox API Token: [seu-token-aqui]
```

### 4. **Criar Job Template**

```yaml
Name: Sync VMware to NetBox
Description: Sincronização automática do inventário VMware para NetBox
Job Type: Run
Inventory: VMware Inventory  # Seu inventário VMware existente
Project: AWX to NetBox Sync
Playbook: playbooks/awx_job_template_sync.yml
Credentials:
  - NetBox Production
Extra Variables:
  awx_netbox_datacenter: "ATI-SLC-HCI"
  awx_netbox_tenant: "ATI"
  awx_netbox_vm_role: "server"
  awx_netbox_subnet: "24"
  awx_netbox_debug: false
  awx_netbox_create_objects: true
  awx_netbox_update_vms: true
  awx_netbox_sync_ips: true
  awx_netbox_sync_interfaces: true
  awx_netbox_add_tags: true
  awx_netbox_enable_reporting: true
Options:
  ✅ Enable Privilege Escalation
  ✅ Enable Fact Storage
  ✅ Ask Variables on Launch (opcional)
```

## 🎯 Variáveis Configuráveis

### **Variáveis Padrão (Extra Variables)**

```yaml
# Configurações do NetBox
awx_netbox_datacenter: "ATI-SLC-HCI"    # Nome do site no NetBox
awx_netbox_tenant: "ATI"                # Nome do tenant
awx_netbox_vm_role: "server"            # Role padrão das VMs
awx_netbox_subnet: "24"                 # Máscara de subnet padrão

# Opções de sincronização
awx_netbox_create_objects: true         # Criar objetos faltantes
awx_netbox_update_vms: true             # Atualizar VMs existentes
awx_netbox_sync_ips: true               # Sincronizar IPs
awx_netbox_sync_interfaces: true        # Sincronizar interfaces
awx_netbox_add_tags: true               # Adicionar tags
awx_netbox_enable_reporting: true       # Habilitar relatórios
awx_netbox_debug: false                 # Habilitar debug
```

### **Variáveis de Ambiente Automáticas**

O AWX injeta automaticamente:

```yaml
awx_job_id: "{{ tower_job_id }}"
awx_job_template_name: "{{ tower_job_template_name }}"
awx_user_name: "{{ tower_user_name }}"
awx_project_name: "{{ tower_project_name }}"
```

## 🔄 Execução do Job Template

### **Execução Manual**

1. Navegue para **Templates** no AWX
2. Clique no ícone 🚀 do template "Sync VMware to NetBox"
3. Ajuste variáveis se necessário
4. Clique em **Launch**

### **Execução Programada**

```yaml
Name: Daily NetBox Sync
Description: Sincronização diária do inventário
Job Template: Sync VMware to NetBox
Schedule Type: Run
Start Date/Time: 2025-07-15 02:00:00
Repeat Frequency: Daily
Time Zone: America/Sao_Paulo
```

### **Execução via API**

```bash
# Lançar job via API
curl -X POST \
  -H "Authorization: Bearer YOUR_AWX_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"extra_vars": {"awx_netbox_debug": true}}' \
  https://your-awx.com/api/v2/job_templates/ID/launch/
```

## 📊 Monitoramento e Logs

### **Visualização de Logs**

Durante a execução, você verá:

```
🚀 AWX → NetBox Sync Job
═══════════════════════════
🏢 Tenant: ATI
🏗️ Site: ATI-SLC-HCI
📊 Total Hosts: 1093
🕐 Started: 2025-07-15T02:00:00Z
🎯 NetBox URL: https://netbox.example.com
```

### **Relatórios Gerados**

- **Console Output**: Progresso em tempo real
- **Job Stats**: Estatísticas do AWX
- **JSON Report**: `/tmp/awx_job_ID_netbox_sync.json`

### **Métricas Importantes**

- **Duração**: Tempo total de execução
- **VMs Processadas**: Número de VMs sincronizadas
- **Taxa de Sucesso**: Percentual de sincronização bem-sucedida
- **Objetos Criados**: Novos objetos no NetBox

## 🔧 Configurações Avançadas

### **Filtros de Inventário**

Para limitar a sincronização a hosts específicos:

```yaml
# No Job Template, usar Limit:
powered_on         # Apenas VMs ligadas
production         # Apenas VMs de produção
windows           # Apenas VMs Windows
linux             # Apenas VMs Linux
```

### **Configuração de Timeout**

```yaml
# Extra Variables
ansible_timeout: 300
ansible_connection_timeout: 30
```

### **Configuração de Paralelo**

```yaml
# Extra Variables
ansible_forks: 10
ansible_serial: 50
```

## 🚨 Troubleshooting

### **Problemas Comuns**

#### **1. Falha na Autenticação NetBox**
```
ERRO: 401 Unauthorized
SOLUÇÃO: Verificar token e URL da API
```

#### **2. Collection não encontrada**
```
ERRO: netbox.netbox collection not found
SOLUÇÃO: Aguardar instalação automática do requirements.yml
```

#### **3. Timeout na sincronização**
```
ERRO: Task timeout
SOLUÇÃO: Aumentar ansible_timeout ou usar limit
```

#### **4. Objetos duplicados**
```
ERRO: Object already exists
SOLUÇÃO: Habilitar awx_netbox_update_vms: true
```

### **Debug Avançado**

```yaml
# Extra Variables para debug
awx_netbox_debug: true
ansible_verbose: true
ansible_verbosity: 3
```

### **Comandos de Verificação**

```bash
# Verificar status do NetBox
curl -H "Authorization: Token TOKEN" \
     https://netbox.example.com/api/status/

# Verificar inventário AWX
awx-cli inventory list
awx-cli host list --inventory ID
```

## 🔄 Workflow de Automação

### **Workflow Template Sugerido**

```yaml
1. Update Project (SCM Sync)
   ↓
2. Sync VMware to NetBox
   ↓
3. Generate Reports
   ↓
4. Send Notifications
```

### **Integração com Webhooks**

```yaml
# NetBox Webhook para mudanças
URL: https://awx.example.com/api/v2/job_templates/ID/launch/
Method: POST
Headers:
  Authorization: Bearer AWX_TOKEN
  Content-Type: application/json
```

## 📚 Referências

- [AWX Job Templates](https://docs.ansible.com/ansible-tower/latest/html/userguide/job_templates.html)
- [AWX Custom Credentials](https://docs.ansible.com/ansible-tower/latest/html/userguide/credentials.html)
- [NetBox API](https://netbox.readthedocs.io/en/stable/rest-api/)
- [Ansible Collections](https://docs.ansible.com/ansible/latest/user_guide/collections_using.html)

## 🎯 Resumo de Configuração

**Para colocar em produção:**

1. ✅ Criar Custom Credential Type "NetBox API"
2. ✅ Criar Credential com URL e Token do NetBox
3. ✅ Criar Project apontando para o repositório Git
4. ✅ Criar Job Template com o playbook `awx_job_template_sync.yml`
5. ✅ Configurar variáveis e credenciais
6. ✅ Testar execução
7. ✅ Configurar schedule para execução automática

**O Job Template está pronto para uso em produção!** 🚀