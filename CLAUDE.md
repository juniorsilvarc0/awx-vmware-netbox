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
vmware-inventory-awx/
├── inventories/vmware/     # Inventário dinâmico VMware
├── playbooks/             # Playbooks de relatórios
├── roles/                 # Roles de coleta de facts
├── scripts/              # Scripts auxiliares Python
└── group_vars/           # Variáveis classificativas
```

### 🔧 Tecnologias Utilizadas

- **Ansible**: Automação e inventário dinâmico
- **VMware vSphere API**: Coleta de dados via pyvmomi
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
Arquivo: inventories/vmware/vmware.yml

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

FORMATO PADRÃO:
variavel_categoria:
  subcategoria:
    item: "valor"
```

## 🚀 Comandos Úteis do Claude Code

### 📋 Comandos Específicos do Projeto

```bash
# Gerar novo playbook de relatório
claude create playbook --type report --name "nome_relatorio" --target "grupo_vms"

# Adicionar novo grupo ao inventário
claude add inventory-group --name "nome_grupo" --condition "propriedade | operador | valor"

# Criar role de análise
claude create role --name "analise_personalizada" --focus "readonly-facts"

# Gerar script Python de monitoramento
claude create script --type monitoring --output "scripts/monitor_custom.py"

# Validar configuração YAML
claude validate --file "inventories/vmware/vmware.yml"
```

### 🔧 Prompts Contextuais

```bash
# Para desenvolvimento de playbooks
claude --context="vmware-inventory-readonly" create playbook

# Para análise de performance
claude --context="vm-performance-analysis" enhance playbook

# Para relatórios executivos
claude --context="executive-reporting" format output

# Para troubleshooting
claude --context="awx-vmware-debug" analyze logs
```

## 📖 Prompts de Engenharia Avançada

### 🎯 Prompt para Criação de Playbooks

```
Crie um playbook Ansible para inventário VMware com as seguintes especificações:

CONTEXTO:
- Projeto: Inventário somente leitura de VMs VMware
- Plataforma: AWX/Ansible Tower
- Restrição: NUNCA modificar VMs, apenas coletar dados

REQUISITOS:
1. gather_facts: false (obrigatório)
2. ansible_connection: local (obrigatório)
3. Usar apenas dados do inventário dinâmico
4. Foco em: [especificar: relatório/análise/exportação]
5. Target: [especificar grupo de VMs]

FORMATO DE SAÍDA:
- Debug messages com formatação ASCII
- Emojis para categorização visual
- Estatísticas quantitativas
- Exportação JSON opcional

EXEMPLO DE USO:
- hosts: [grupo_alvo]
- Análise de: [métricas específicas]
- Saída: [formato desejado]

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
- Arquivo: inventories/vmware/vmware.yml
- Foco: Otimização de grupos e classificação
- Objetivo: Melhor organização para relatórios

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

SAÍDA ESPERADA:
- Inventário otimizado
- Documentação das mudanças
- Justificativa técnica
- Impacto nos relatórios

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

ESTRUTURA DO RELATÓRIO:
1. Header com informações gerais
2. Estatísticas por categoria
3. Análise de conformidade
4. Alertas e recomendações
5. Dados para exportação

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
# File: inventories/vmware/group_vars/{{ group_name }}.yml

# Classification variables
{{ group_name }}_classification:
  # Add classification data here

# Metadata for reporting
{{ group_name }}_metadata:
  purpose: "Classification and reporting"
  last_updated: "{{ ansible_date_time.date }}"
```

## 🎯 Exemplos de Uso Prático

### 💼 Cenário 1: Novo Relatório de Compliance

```bash
claude create compliance-report \
  --scope "production VMs" \
  --criteria "vmware-tools,resources,naming" \
  --output "playbooks/compliance_report.yml" \
  --format "executive-summary"
```

### 📊 Cenário 2: Análise de Recursos

```bash
claude analyze resource-utilization \
  --focus "cpu,memory,storage" \
  --grouping "environment,criticality" \
  --threshold "high-usage" \
  --recommendations "optimization"
```

### 🔍 Cenário 3: Debug de Inventário

```bash
claude debug inventory-sync \
  --check "group-creation,variable-assignment" \
  --validate "yaml-syntax,awx-compatibility" \
  --report "troubleshooting-guide"
```

## 📚 Recursos de Referência

### 🔗 Links Importantes

- [Ansible VMware Guide](https://docs.ansible.com/ansible/latest/collections/community/vmware/)
- [AWX Inventory Sources](https://docs.ansible.com/ansible-tower/latest/html/userguide/inventories.html)
- [PyVmomi Documentation](https://github.com/vmware/pyvmomi)

### 📖 Padrões de Código

- **YAML**: Indentação 2 espaços, sem tabs
- **Python**: PEP 8, type hints quando possível
- **Jinja2**: Formatação clara, escape quando necessário
- **Markdown**: Headers consistentes, emojis para categorização

### 🎯 Melhores Práticas

1. **Sempre valide YAML** antes de commit
2. **Teste playbooks** em ambiente isolado
3. **Documente mudanças** no CHANGELOG
4. **Use versionamento semântico** para releases
5. **Mantenha backward compatibility** sempre que possível

---

**Configurado para:** ATI Piauí - Inventário VMware AWX  
**Última atualização:** {{ ansible_date_time.iso8601 }}  
**Modo de operação:** Somente Leitura 🔒
