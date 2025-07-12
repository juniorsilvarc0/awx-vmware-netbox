# 🏗️ VMware Inventory AWX Project - SOMENTE LEITURA

Este repositório contém a configuração completa para criar um **inventário dinâmico somente leitura** de VMs VMware no AWX/Ansible Tower.

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Pré-requisitos](#pré-requisitos)
- [Configuração no AWX](#configuração-no-awx)
- [Uso](#uso)
- [Playbooks Disponíveis](#playbooks-disponíveis)
- [Personalização](#personalização)
- [Troubleshooting](#troubleshooting)

## 🎯 Visão Geral

Este projeto **NÃO FAZ ALTERAÇÕES** nas VMs VMware. É exclusivamente para **inventariar e gerar relatórios** através do AWX, criando grupos dinâmicos baseados em:

- **Estado de energia**: `powered_on`, `powered_off`, `suspended`
- **Sistema operacional**: `windows`, `linux`, distribuições específicas
- **Recursos**: `high_cpu`, `high_memory`, `high_performance`
- **VMware Tools**: `tools_ok`, `tools_outdated`, `tools_not_installed`
- **Ambiente**: `production`, `development`, `testing`, `staging`
- **Snapshots**: `has_snapshots`, `multiple_snapshots`

## 📁 Estrutura do Projeto

```
vmware-inventory-awx/
├── 📄 README.md                    # Este arquivo
├── 📄 requirements.txt             # Dependências Python
├── ⚙️  ansible.cfg                 # Configuração do Ansible
│
├── 📁 inventories/vmware/
│   ├── 📄 vmware.yml              # Inventário dinâmico (credenciais via AWX)
│   └── 📁 group_vars/
│       ├── 📄 all.yml             # Variáveis globais (somente classificação)
│       ├── 📄 windows.yml         # Informações classificativas Windows
│       └── 📄 linux.yml           # Informações classificativas Linux
│
├── 📁 scripts/
│   ├── 📄 vmware_inventory.py     # Script Python para teste local
│   └── 📄 vmware_monitor.py       # Script de monitoramento
│
├── 📁 playbooks/
│   ├── 📄 inventory_report.yml    # Relatórios do inventário
│   └── 📄 vm_facts_collection.yml # Coleta detalhada de facts
│
└── 📁 roles/
    └── 📁 vmware_facts/
        ├── 📁 tasks/
        │   └── 📄 main.yml
        └── 📁 vars/
            └── 📄 main.yml
```

## 🔧 Pré-requisitos

### No AWX/Ansible Tower:

- AWX 21.0+ ou Ansible Tower 3.8+
- Python 3.8+
- Acesso ao vCenter Server (somente leitura)

### Dependências Python:

```bash
pip install -r requirements.txt
```

### Credenciais necessárias (configuradas no AWX):

- **vCenter**: Usuário com permissões de **somente leitura**

## ⚙️ Configuração no AWX

### 1. 📦 Criar Projeto

1. Acesse **Projects** → **Add**
2. Configure:
   ```yaml
   Name: VMware Inventory Project
   SCM Type: Git
   SCM URL: https://github.com/seu-usuario/vmware-inventory-awx.git
   SCM Branch: main
   Update Revision on Launch: ✅
   Clean: ✅
   ```

### 2. 🔐 Criar Credencial VMware (SOMENTE LEITURA)

1. Acesse **Credentials** → **Add**
2. Configure:
   ```yaml
   Name: VMware vCenter Read-Only Credential
   Type: VMware vCenter
   vCenter Host: vcsa04.ati.pi.gov.br
   Username: netbox-ro@VSPHERE.LOCAL
   Password: [sua_senha_readonly]
   ```

### 3. 📋 Criar Inventário

1. Acesse **Inventories** → **Add**
2. Configure:
   ```yaml
   Name: VMware Inventory (Read-Only)
   Description: Inventário dinâmico das VMs do vCenter - SOMENTE LEITURA
   ```

### 4. 🔄 Adicionar Source

1. No inventário, vá para **Sources** → **Add**
2. Configure:
   ```yaml
   Name: VMware vCenter Source
   Source: Sourced from a Project
   Project: VMware Inventory Project
   Inventory File: inventories/vmware/vmware.yml
   Credential: VMware vCenter Read-Only Credential
   Update on Launch: ✅
   Overwrite: ✅
   Cache Timeout: 3600
   ```

### 5. ✅ Sincronizar

1. Clique em **Sync** na source
2. Aguarde a sincronização completar
3. Verifique os hosts e grupos criados

## 🚀 Uso

### Relatório do Inventário

Crie um **Job Template**:

```yaml
Name: VMware Inventory Report
Job Type: Run
Inventory: VMware Inventory (Read-Only)
Project: VMware Inventory Project
Playbook: playbooks/inventory_report.yml
```

### Coleta Detalhada de Facts

```yaml
Name: VMware Facts Collection
Job Type: Run
Inventory: VMware Inventory (Read-Only)
Project: VMware Inventory Project
Playbook: playbooks/vm_facts_collection.yml
```

## 📚 Playbooks Disponíveis

### 🔍 inventory_report.yml

**Gera relatório completo do inventário** com:

- Estatísticas por grupo (SO, recursos, estado)
- Status das VMs e VMware Tools
- Análise de snapshots
- Relatório executivo em formato texto
- Exportação de dados em JSON

### 📊 vm_facts_collection.yml

**Coleta facts detalhados** incluindo:

- Análise de performance com scoring
- Classificação automática com tags
- Verificação de conformidade
- Recomendações de melhoria
- Relatório consolidado

## 🎨 Personalização

### Modificar Agrupamentos

Edite `inventories/vmware/vmware.yml`:

```yaml
groups:
  # Grupo personalizado baseado em anotações
  custom_environment: config.annotation | regex_search("prod")

  # Grupo por naming convention
  web_servers: name | regex_search("web|www")

  # Grupo por recursos específicos
  memory_intensive: summary.config.memorySizeMB >= 32768
```

### Adicionar Variáveis de Classificação

Em `inventories/vmware/group_vars/all.yml`:

```yaml
# Suas classificações customizadas
vm_tier: "{{ 'tier1' if vm_criticality == 'high' else 'tier2' if vm_criticality == 'medium' else 'tier3' }}"
backup_required: "{{ vm_environment == 'production' }}"
```

### Criar Novos Relatórios

Exemplo de playbook personalizado:

```yaml
---
- name: Relatório Personalizado
  hosts: production:&powered_on
  gather_facts: false
  vars:
    ansible_connection: local

  tasks:
    - name: Listar VMs de produção ativas
      debug:
        msg: "VM de Produção: {{ vm_name }} - {{ vm_ip_addresses }}"
```

## 🔒 Segurança e Limitações

### ✅ O que este projeto FAZ:

- ✅ Coleta informações das VMs (somente leitura)
- ✅ Gera relatórios e estatísticas
- ✅ Classifica VMs automaticamente
- ✅ Cria grupos dinâmicos
- ✅ Exporta dados para análise

### ❌ O que este projeto NÃO FAZ:

- ❌ **NÃO** modifica configurações de VMs
- ❌ **NÃO** instala ou atualiza software
- ❌ **NÃO** reinicia ou desliga VMs
- ❌ **NÃO** altera recursos (CPU/memória)
- ❌ **NÃO** modifica redes ou storage
- ❌ **NÃO** executa comandos nas VMs

## 🛠️ Troubleshooting

### Problemas Comuns

#### ❌ Erro de Credenciais

- Verifique se a credencial VMware está configurada corretamente no AWX
- Confirme se o usuário tem permissões de leitura no vCenter

#### ⏰ Timeout de Sincronização

- Aumente o cache timeout para datacenters grandes
- Verifique conectividade entre AWX e vCenter

#### 🔍 Debug Detalhado

```yaml
# No Job Template, adicione em Extra Variables:
ansible_verbosity: 3
```

### Validação Manual

Teste o script Python localmente:

```bash
cd scripts/
python3 vmware_inventory.py --list
```

## 📞 Suporte

Para problemas específicos:

1. Verifique os logs do AWX
2. Teste conectividade com vCenter
3. Valide credenciais de somente leitura
4. Confirme permissões no vCenter
5. Verifique versões das dependências

## 📝 Licença

Este projeto está sob licença MIT. Veja o arquivo LICENSE para detalhes.

## 🤝 Contribuição

1. Fork o projeto
2. Crie sua feature branch (`git checkout -b feature/ReportFeature`)
3. Commit suas mudanças (`git commit -m 'Add some ReportFeature'`)
4. Push para a branch (`git push origin feature/ReportFeature`)
5. Abra um Pull Request

---

**Desenvolvido para ATI Piauí** 🏛️

_Inventário VMware automatizado com AWX - Somente Leitura_ 🔒not_installed`

- **Ambiente**: `production`, `development`, `testing`, `staging`
- **Snapshots**: `has_snapshots`, `multiple_snapshots`

## 📁 Estrutura do Projeto

```
vmware-inventory-awx/
├── 📄 README.md                    # Este arquivo
├── 📄 requirements.txt             # Dependências Python
├── ⚙️  ansible.cfg                 # Configuração do Ansible
│
├── 📁 inventories/vmware/
│   ├── 📄 vmware.yml              # Configuração do inventário dinâmico
│   └── 📁 group_vars/
│       ├── 📄 all.yml             # Variáveis globais
│       ├── 📄 windows.yml         # Variáveis específicas Windows
│       └── 📄 linux.yml           # Variáveis específicas Linux
│
├── 📁 scripts/
│   ├── 📄 vmware_inventory.py     # Script Python para teste local
│   └── 📄 vmware_monitor.py       # Script de monitoramento
│
├── 📁 playbooks/
│   ├── 📄 test_inventory.yml      # Teste e relatório do inventário
│   ├── 📄 windows_patch.yml       # Patch management Windows
│   └── 📄 linux_patch.yml         # Patch management Linux
│
└── 📁 roles/
    └── 📁 vmware_facts/
        ├── 📁 tasks/
        │   └── 📄 main.yml
        └── 📁 vars/
            └── 📄 main.yml
```

## 🔧 Pré-requisitos

### No AWX/Ansible Tower:

- AWX 21.0+ ou Ansible Tower 3.8+
- Python 3.8+
- Acesso ao vCenter Server

### Dependências Python:

```bash
pip install -r requirements.txt
```

### Credenciais necessárias:

- **vCenter**: Usuário com permissões de leitura
- **VMs Windows**: Usuário com acesso WinRM
- **VMs Linux**: Usuário SSH com sudo

## ⚙️ Configuração no AWX

### 1. 📦 Criar Projeto

1. Acesse **Projects** → **Add**
2. Configure:
   ```yaml
   Name: VMware Inventory Project
   SCM Type: Git
   SCM URL: https://github.com/seu-usuario/vmware-inventory-awx.git
   SCM Branch: main
   Update Revision on Launch: ✅
   Clean: ✅
   ```

### 2. 🔐 Criar Credenciais

#### Credencial VMware vCenter:

```yaml
Name: VMware vCenter Credential
Type: VMware vCenter
vCenter Host: vcsa04.ati.pi.gov.br
Username: netbox-ro@VSPHERE.LOCAL
Password: 9i7j&BtSzwZ]
```

#### Credencial Windows (opcional):

```yaml
Name: Windows Credential
Type: Machine
Username: Administrator
Password: sua_senha_windows
```

#### Credencial Linux (opcional):

```yaml
Name: Linux SSH Credential
Type: Machine
Username: ansible
SSH Private Key: sua_chave_ssh
Privilege Escalation Method: sudo
```

### 3. 📋 Criar Inventário

1. Acesse **Inventories** → **Add**
2. Configure:
   ```yaml
   Name: VMware Production Inventory
   Description: Inventário dinâmico das VMs do vCenter ATI
   ```

### 4. 🔄 Adicionar Source

1. No inventário, vá para **Sources** → **Add**
2. Configure:
   ```yaml
   Name: VMware vCenter Source
   Source: Sourced from a Project
   Project: VMware Inventory Project
   Inventory File: inventories/vmware/vmware.yml
   Credential: VMware vCenter Credential
   Update on Launch: ✅
   Overwrite: ✅
   Cache Timeout: 3600
   ```

### 5. ✅ Sincronizar

1. Clique em **Sync** na source
2. Aguarde a sincronização completar
3. Verifique os hosts e grupos criados

## 🚀 Uso

### Teste do Inventário

Crie um **Job Template**:

```yaml
Name: Test VMware Inventory
Job Type: Run
Inventory: VMware Production Inventory
Project: VMware Inventory Project
Playbook: playbooks/test_inventory.yml
```

### Patch Management Windows

```yaml
Name: Windows Patch Management
Inventory: VMware Production Inventory
Project: VMware Inventory Project
Playbook: playbooks/windows_patch.yml
Limit: windows:&powered_on
Extra Variables:
  patch_serial: "25%"
  excluded_updates: []
```

### Patch Management Linux

```yaml
Name: Linux Patch Management
Inventory: VMware Production Inventory
Project: VMware Inventory Project
Playbook: playbooks/linux_patch.yml
Limit: linux:&powered_on
Extra Variables:
  security_only: false
  auto_reboot: true
```

## 📚 Playbooks Disponíveis

### 🔍 test_inventory.yml

Gera relatório completo do inventário com:

- Estatísticas por grupo
- Status das VMs
- Informações de recursos
- Relatório executivo

### 🪟 windows_patch.yml

Patch management para Windows:

- Verifica atualizações disponíveis
- Cria ponto de restauração
- Instala atualizações
- Reinicia se necessário
- Valida serviços críticos

### 🐧 linux_patch.yml

Patch management para Linux:

- Suporte para apt, yum, dnf
- Atualizações de segurança
- Verificação de reboot
- Limpeza pós-patch
- Validação de serviços

## 🎨 Personalização

### Modificar Agrupamentos

Edite `inventories/vmware/vmware.yml`:

```yaml
groups:
  # Grupo personalizado baseado em CPU
  high_performance_cpu: summary.config.numCpu >= 16

  # Grupo por localização
  datacenter_primary: datacenter == "ATI-SLC-HCI"

  # Grupo por ambiente (baseado em anotação)
  production_env: config.annotation | regex_search("prod")
```

### Adicionar Variáveis Personalizadas

Em `inventories/vmware/group_vars/all.yml`:

```yaml
# Suas variáveis customizadas
company_name: "ATI Piauí"
backup_schedule: "daily"
monitoring_enabled: true
```

### Criar Novos Playbooks

Exemplo de playbook personalizado:

```yaml
---
- name: Meu Playbook Personalizado
  hosts: windows:&production
  gather_facts: false

  tasks:
    - name: Tarefa específica
      debug:
        msg: "Executando em {{ vm_name }}"
```

## 🛠️ Troubleshooting

### Problemas Comuns

#### ❌ Erro de SSL

```yaml
# Em vmware.yml, adicione:
validate_certs: false
```

#### ⏰ Timeout de Conexão

```yaml
# Em vmware.yml, adicione:
timeout: 60
```

#### 🔍 Debug Detalhado

```yaml
# No Job Template, adicione em Extra Variables:
ansible_verbosity: 3
```

### Logs Importantes

- **AWX**: `/var/log/tower/`
- **Inventory Sync**: Interface do AWX → Jobs
- **Ansible**: `/tmp/ansible.log`

### Validação Manual

Teste o script Python localmente:

```bash
cd scripts/
python3 vmware_inventory.py --list
```

## 📞 Suporte

Para problemas específicos:

1. Verifique os logs do AWX
2. Teste conectividade com vCenter
3. Valide credenciais
4. Confirme permissões no vCenter
5. Verifique versões das dependências

## 📝 Licença

Este projeto está sob licença MIT. Veja o arquivo LICENSE para detalhes.

## 🤝 Contribuição

1. Fork o projeto
2. Crie sua feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

---

**Desenvolvido para ATI Piauí** 🏛️

_Automatizando a gestão de infraestrutura VMware com Ansible AWX_
