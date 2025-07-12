# 🤖 Claude Code Configuration

Este arquivo configura o Claude Code para auxiliar no desenvolvimento e manutenção do repositório de inventário VMware para AWX.

## 📋 Contexto do Projeto

### 🎯 Objetivo Principal

Este repositório implementa um **inventário dinâmico somente leitura** de VMs VMware para AWX/Ansible Tower, focando exclusivamente em:

- Coleta de informações das VMs via API vCenter
- Geração de relatórios e estatísticas
- Classificação automática de recursos
- Análise de conformidade
- Exportação de dados para análise

### ⚠️ Restrições Críticas

- ❌ **NUNCA** criar código que modifique VMs
- ❌ **NUNCA** incluir tarefas de patch management
- ❌ **NUNCA** adicionar credenciais explícitas nos arquivos
- ❌ **NUNCA** criar playbooks que executem comandos nas VMs
- ✅ **SEMPRE** manter foco em inventário e relatórios

## 🏗️ Arquitetura do Projeto

```
awx-vmware-netbox/
├── 📄 inventory.yml           # Inventário dinâmico principal (raiz)
├── 📁 group_vars/             # Variáveis classificativas
│   ├── all.yml               # Variáveis globais
│   ├── windows.yml           # Classificação Windows
│   └── linux.yml             # Classificação Linux
├── 📁 playbooks/             # Playbooks de relatórios
│   ├── test_inventory.yml    # Teste do inventário
│   └── vm_facts_collection.yml # Coleta de facts
├── 📁 roles/                 # Roles de análise
│   └── vmware_facts/         # Role principal de facts
├── 📁 scripts/              # Scripts auxiliares Python
│   ├── vmware_inventory.py  # Script de inventário standalone
│   └── vmware_monitor.py    # Script de monitoramento
├── 📄 ansible.cfg           # Configuração Ansible
└── 📄 requirements.txt      # Dependências Python
```

### 🔧 Tecnologias Utilizadas

- **Ansible**: Automação e inventário dinâmico
- **VMware vSphere API**: Coleta de dados via vmware.vmware.vms plugin
- **AWX/Tower**: Orquestração e interface web
- **Python**: Scripts auxiliares e monitoramento
- **YAML**: Configuração e estrutura de dados

## 📚 Guias de Desenvolvimento

### 🎯 Criação de Playbooks

**Contexto para Claude Code:**

```
Quando criar playbooks para este projeto:

OBRIGATÓRIO:
- gather_facts: false (sempre)
- ansible_connection: local (para relatórios)
- Foco EXCLUSIVO em relatórios e análise
- Usar apenas dados do inventário dinâmico
- Incluir emojis para melhor visualização
- Formatação clara com debug messages
- Exportação opcional em JSON

PROIBIDO:
- Qualquer task que conecte nas VMs
- win_* modules para Windows
- package, service, command modules
- Qualquer alteração de estado das VMs
- become: true ou escalação de privilégios
- Configurações de conexão SSH/WinRM

ESTRUTURA PADRÃO:
---
- name: 📊 Nome Descritivo do Relatório
  hosts: [grupo_alvo]
  gather_facts: false
  vars:
    ansible_connection: local
  tasks:
    - name: 📋 Descrição da tarefa
      debug:
        msg: |
          Relatório formatado com dados do inventário
```

### 🔍 Desenvolvimento de Inventário

**Contexto para modificações no inventário:**

```
Arquivo: inventory.yml (na raiz do projeto)

PERMITIDO:
- Adicionar novos grupos baseados em propriedades
- Modificar keyed_groups para melhor classificação
- Ajustar compose variables para novos campos
- Melhorar filtros de VMs
- Otimizar cache settings

ESTRUTURA DE GRUPOS:
groups:
  nome_grupo: propriedade_vmware | operador | valor

EXEMPLOS:
  web_servers: name | regex_search("web|www")
  high_memory: summary.config.memorySizeMB >= 32768
  production_vms: config.annotation | regex_search("prod")

VARIÁVEIS COMPOSE:
compose:
  vm_campo_personalizado: fonte.propriedade | filtro

CONFIGURAÇÃO ATUAL:
- Plugin: vmware.vmware.vms
- validate_certs: false
- Cache: habilitado (3600s)
- Filtros: apenas VMs não template
```

### 📊 Criação de Relatórios

**Padrões para relatórios eficazes:**

```
FORMATO DE SAÍDA:
- Use tabelas ASCII art para resumos executivos
- Inclua estatísticas quantitativas
- Adicione emojis para identificação rápida
- Formate dados complexos em JSON para exportação
- Agrupe informações por categorias lógicas

EXEMPLO DE FORMATAÇÃO:
╔════════════════════════════════════════╗
║        TÍTULO DO RELATÓRIO             ║
╠════════════════════════════════════════╣
║ 📊 Métrica 1: {{ valor }}              ║
║ 📈 Métrica 2: {{ valor }}              ║
╚════════════════════════════════════════╝

DADOS DISPONÍVEIS NO INVENTÁRIO:
- vm_name: Nome da VM
- vm_power_state: Estado de energia
- vm_cpu_count: Número de CPUs
- vm_memory_mb: Memória em MB
- ansible_host: IP da VM
- Grupos automáticos: powered_on, powered_off, windows, linux
```

### 🏷️ Sistema de Variáveis

**Convenções para group_vars:**

```
ESTRUTURA OBRIGATÓRIA:
- Apenas variáveis classificativas
- Sem configurações de conexão
- Focado em metadados e análise
- Compatível com template Jinja2

CATEGORIAS DE VARIÁVEIS:
- Classificação: vm_environment, vm_criticality
- Recursos: resource_categories, performance_thresholds
- Metadados: inventory_metadata, audit_info
- Tags: computed_tags, classification_tags

ARQUIVOS EXISTENTES:
- group_vars/all.yml: Variáveis globais
- group_vars/windows.yml: Específico para Windows
- group_vars/linux.yml: Específico para Linux

FORMATO PADRÃO:
variavel_categoria:
  subcategoria:
    item: "valor"
```

## 🚀 Comandos de Desenvolvimento

### 📋 Comandos Específicos do Projeto

```bash
# Validar inventário YAML
ansible-inventory -i inventory.yml --list

# Testar playbook de relatório
ansible-playbook -i inventory.yml playbooks/test_inventory.yml

# Executar coleta de facts
ansible-playbook -i inventory.yml playbooks/vm_facts_collection.yml

# Verificar grupos dinâmicos
ansible-inventory -i inventory.yml --graph

# Validar sintaxe YAML
ansible-playbook --syntax-check playbooks/[playbook].yml
```

### 🔧 Prompts Contextuais para Claude Code

```bash
# Para desenvolvimento de playbooks
"Criar playbook de relatório VMware somente leitura"

# Para análise de inventário
"Analisar e otimizar grupos do inventário VMware"

# Para troubleshooting
"Debug do inventário dinâmico VMware no AWX"

# Para melhorias
"Melhorar classificação de VMs no group_vars"
```

## 📖 Prompts de Engenharia Avançada

### 🎯 Prompt para Criação de Playbooks

```
Crie um playbook Ansible para inventário VMware com as seguintes especificações:

CONTEXTO:
- Projeto: Inventário somente leitura de VMs VMware
- Plataforma: AWX/Ansible Tower
- Restrição: NUNCA modificar VMs, apenas coletar dados

REQUISITOS OBRIGATÓRIOS:
1. gather_facts: false
2. ansible_connection: local
3. Usar apenas dados do inventário dinâmico
4. Foco em: [especificar: relatório/análise/exportação]
5. Target: [especificar grupo de VMs]

DADOS DISPONÍVEIS:
- vm_name, vm_power_state, vm_cpu_count, vm_memory_mb
- ansible_host, grupos automáticos (powered_on, windows, linux)
- Propriedades VMware via hostvars

FORMATO DE SAÍDA:
- Debug messages com formatação ASCII
- Emojis para categorização visual
- Estatísticas quantitativas
- Exportação JSON opcional

VALIDAÇÕES:
✅ Sem conexão direta às VMs
✅ Sem modificação de estado
✅ Dados apenas do inventário
✅ Compatível com AWX
```

### 🔍 Prompt para Análise de Inventário

```
Analise e melhore o inventário VMware seguindo estas diretrizes:

ESCOPO DE ANÁLISE:
- Arquivo: inventory.yml (raiz do projeto)
- Plugin atual: vmware.vmware.vms
- Foco: Otimização de grupos e classificação

CONFIGURAÇÃO ATUAL:
- Propriedades coletadas: name, config.uuid, runtime.powerState, etc.
- Grupos existentes: powered_on, powered_off, windows, linux
- Compose variables: vm_name, vm_power_state, vm_cpu_count, vm_memory_mb
- Cache: habilitado (3600s)

ÁREAS DE MELHORIA:
1. Grupos dinâmicos mais específicos
2. Variáveis compose mais úteis
3. Filtros otimizados
4. Performance de cache

CRITÉRIOS DE QUALIDADE:
- Grupos logicamente organizados
- Nomenclatura consistente
- Performance otimizada
- Facilidade de manutenção

RESTRIÇÕES:
❌ Não adicionar credenciais
❌ Não incluir configurações de conexão
✅ Manter compatibilidade AWX
✅ Preservar funcionalidade existente
```

### 📊 Prompt para Geração de Relatórios

```
Desenvolva um sistema de relatórios avançado para inventário VMware:

OBJETIVO:
Criar relatórios executivos detalhados para gestão de infraestrutura

DADOS DISPONÍVEIS:
- Inventário: vm_name, vm_power_state, vm_cpu_count, vm_memory_mb
- Grupos: powered_on, powered_off, windows, linux
- Hostvars: todas as propriedades VMware coletadas
- Group_vars: variáveis classificativas em all.yml, windows.yml, linux.yml

COMPONENTES NECESSÁRIOS:
1. Resumo executivo visual
2. Análise de recursos e performance
3. Identificação de problemas
4. Recomendações automatizadas
5. Exportação para análise externa

FORMATO DE DADOS:
- Entrada: Variáveis do inventário dinâmico
- Processamento: Ansible facts e group_vars
- Saída: Debug formatado + JSON estruturado

CRITÉRIOS DE QUALIDADE:
📊 Métricas quantitativas precisas
🎨 Visualização clara e profissional
⚡ Performance otimizada
📈 Insights acionáveis
🔍 Detalhamento configurável

VALIDAÇÃO:
✅ Funciona com inventário atual
✅ Performance aceitável (< 5min)
✅ Saída legível para humanos
✅ Dados estruturados para máquinas
```

## 🔧 Configurações Específicas

### 🎯 Variáveis de Ambiente para Claude Code

```bash
# Configurar contexto do projeto
export CLAUDE_PROJECT_TYPE="vmware-inventory"
export CLAUDE_RESTRICTION_MODE="readonly"
export CLAUDE_TARGET_PLATFORM="awx"

# Configurar preferências de código
export CLAUDE_ANSIBLE_VERSION="2.13+"
export CLAUDE_PYTHON_VERSION="3.8+"
export CLAUDE_YAML_STYLE="standard"

# Configurar padrões de saída
export CLAUDE_OUTPUT_FORMAT="yaml+debug"
export CLAUDE_DOCUMENTATION_LEVEL="detailed"
export CLAUDE_EMOJI_MODE="enabled"
```

### 📋 Templates de Arquivos

```yaml
# Template para novos playbooks
---
- name: 📊 {{ playbook_name }}
  hosts: {{ target_group | default('all') }}
  gather_facts: false
  vars:
    ansible_connection: local

  tasks:
    - name: 📋 {{ task_description }}
      debug:
        msg: |
          {{ formatted_output }}

# Template para group_vars
---
# {{ group_name }} specific variables - READ ONLY
# File: group_vars/{{ group_name }}.yml

# Classification variables
{{ group_name }}_classification:
  # Add classification data here

# Metadata for reporting
{{ group_name }}_metadata:
  purpose: "Classification and reporting"
  last_updated: "{{ ansible_date_time.date }}"
```

## 🎯 Estrutura de Arquivos Atual

### 📄 Inventário Principal (inventory.yml)

```yaml
# Configuração do plugin VMware
plugin: vmware.vmware.vms
validate_certs: false
gather_tags: true

# Propriedades coletadas
properties:
  - name, config.uuid, config.guestFullName
  - runtime.powerState, summary.config.numCpu
  - summary.config.memorySizeMB, guest.*
  - cluster, datacenter

# Filtros e grupos automáticos
filter_expressions:
  - "config.template == false"

groups:
  powered_on: summary.runtime.powerState == "poweredOn"
  powered_off: summary.runtime.powerState == "poweredOff"
  windows: config.guestFullName | regex_search("Windows")
  linux: config.guestFullName | regex_search("Linux")
```

### 📁 Playbooks Disponíveis

1. **test_inventory.yml**: Teste e relatório básico do inventário
2. **vm_facts_collection.yml**: Coleta detalhada de facts das VMs

### 📁 Group_vars Existentes

1. **all.yml**: Variáveis globais para todas as VMs
2. **windows.yml**: Variáveis específicas para VMs Windows
3. **linux.yml**: Variáveis específicas para VMs Linux

### 📁 Scripts Python

1. **vmware_inventory.py**: Script standalone para teste do inventário
2. **vmware_monitor.py**: Script de monitoramento e métricas

## 📚 Recursos de Referência

### 🔗 Links Importantes

- [Ansible VMware Guide](https://docs.ansible.com/ansible/latest/collections/community/vmware/)
- [VMware vSphere Plugin](https://docs.ansible.com/ansible/latest/collections/vmware/vmware/vms_inventory.html)
- [AWX Inventory Sources](https://docs.ansible.com/ansible-tower/latest/html/userguide/inventories.html)

### 📖 Padrões de Código

- **YAML**: Indentação 2 espaços, sem tabs
- **Python**: PEP 8, type hints quando possível
- **Jinja2**: Formatação clara, escape quando necessário
- **Markdown**: Headers consistentes, emojis para categorização

### 🎯 Melhores Práticas

1. **Sempre valide YAML** antes de commit
2. **Teste playbooks** em ambiente isolado
3. **Use ansible-inventory --list** para validar inventário
4. **Mantenha cache otimizado** para performance
5. **Documente mudanças** nos comentários YAML

## 🛠️ Troubleshooting Comum

### ❌ Problemas Frequentes

1. **Credenciais VMware**: Configurar no AWX, não nos arquivos
2. **Timeout de inventário**: Ajustar cache_timeout no inventory.yml
3. **Grupos não criados**: Verificar expressões em groups
4. **Performance lenta**: Otimizar propriedades coletadas

### ✅ Comandos de Validação

```bash
# Testar inventário localmente
ansible-inventory -i inventory.yml --list

# Verificar sintaxe do playbook
ansible-playbook --syntax-check playbooks/test_inventory.yml

# Debug do inventário
ansible-inventory -i inventory.yml --graph --vars
```

---

**Configurado para:** ATI Piauí - Inventário VMware AWX  
**Última atualização:** 2025-07-12  
**Modo de operação:** Somente Leitura 🔒  
**Arquitetura:** AWX + VMware vSphere API + Ansible 🏗️