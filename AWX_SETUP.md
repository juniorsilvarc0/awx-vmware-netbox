# 🚀 Configuração do AWX para Inventário VMware

Este documento descreve como configurar o inventário VMware no AWX/Ansible Tower.

## 📋 Pré-requisitos

- AWX/Ansible Tower instalado e funcionando
- Acesso ao vCenter Server com credenciais de leitura
- Collections Ansible instaladas: `community.vmware`, `vmware.vmware`

## 🔧 Configuração Passo a Passo

### 1. 📥 Importar o Projeto

1. Acesse **AWX → Projects**
2. Clique em **Add** (➕)
3. Configure:
   - **Name**: `VMware Inventory - ATI`
   - **SCM Type**: `Git`
   - **SCM URL**: `[URL_DO_SEU_REPOSITORIO]`
   - **SCM Branch**: `main`
   - **Update Revision on Launch**: ✅ Habilitado

### 2. 🔐 Criar Credenciais

#### Credencial VMware
1. Acesse **AWX → Credentials**
2. Clique em **Add** (➕)
3. Configure:
   - **Name**: `vCenter ATI Credentials`
   - **Credential Type**: `VCenter-vars` (Custom Type)
   - **Fields**:
     ```
     VCENTER_HOST: vcsa04.ati.pi.gov.br
     VCENTER_USER: netbox-ro@VSPHERE.LOCAL
     VCENTER_PASSWORD: [SUA_SENHA_AQUI]
     DATACENTER_NAME: ATI-SLC-HCI
     ```

#### Credencial NetBox (Para Sincronização)
1. Criar outra credencial:
   - **Name**: `NetBox ATI API`
   - **Credential Type**: `Netbox Credentials` (Custom Type)
   - **Fields**:
     ```
     NetBox Host URL: http://177.93.133.239:8000
     NetBox API Token: [SEU_TOKEN_NETBOX]
     ```

### 3. 📊 Configurar Inventário

1. Acesse **AWX → Inventories**
2. Clique em **Add** (➕)
3. Configure:
   - **Name**: `VMware VMs - ATI`
   - **Description**: `Inventário dinâmico das VMs VMware`

### 4. 🔗 Adicionar Source de Inventário

1. No inventário criado, vá para **Sources**
2. Clique em **Add** (➕)
3. Configure:
   - **Name**: `VMware Dynamic Source`
   - **Source**: `Sourced from a Project`
   - **Project**: `VMware Inventory - ATI`
   - **Inventory File**: `inventory.yml`
   - **Credential**: `vCenter ATI Credentials`
   - **Update on Launch**: ✅ Habilitado
   - **Cache Timeout**: `3600` (1 hora)

### 5. 🎯 Criar Job Templates

#### Template de Teste do Inventário
1. Acesse **AWX → Templates**
2. Clique em **Add** → **Job Template**
3. Configure:
   - **Name**: `VMware Inventory Test`
   - **Project**: `VMware Inventory - ATI`
   - **Playbook**: `playbooks/test_inventory.yml`
   - **Inventory**: `VMware VMs - ATI`
   - **Credentials**: `vCenter ATI Credentials`
   - **Variables**:
     ```yaml
     debug_facts_collection: true
     ```

#### Template de Relatório Completo
1. Criar outro Job Template:
   - **Name**: `VMware Inventory Report`
   - **Playbook**: `playbooks/vm_facts_collection.yml`
   - **Mesmas configurações do template anterior**

## 🔄 Sincronização e Teste

### 1. Sincronizar Projeto
1. Vá para **Projects** → `VMware Inventory - ATI`
2. Clique no ícone de sincronização (🔄)
3. Aguarde conclusão

### 2. Sincronizar Inventário
1. Vá para **Inventories** → `VMware VMs - ATI` → **Sources**
2. Clique no ícone de sincronização da source
3. Aguarde coleta das VMs

### 3. Executar Teste
1. Vá para **Templates** → `VMware Inventory Test`
2. Clique em **Launch** (🚀)
3. Verifique os resultados

## 📊 Grupos Criados Automaticamente

O inventário criará automaticamente os seguintes grupos:

### 🔋 Por Estado
- `powered_on` - VMs ligadas
- `powered_off` - VMs desligadas
- `suspended` - VMs suspensas

### 💻 Por Sistema Operacional
- `windows` - VMs Windows
- `linux` - VMs Linux

### ⚡ Por Performance
- `high_cpu` - VMs com 8+ CPUs
- `high_memory` - VMs com 16+ GB RAM
- `high_performance` - VMs com alto desempenho

### 🌍 Por Ambiente
- `production` - VMs de produção
- `development` - VMs de desenvolvimento
- `testing` - VMs de teste
- `staging` - VMs de staging

### 🛠️ Por Status
- `tools_ok` - VMware Tools funcionando
- `tools_outdated` - VMware Tools desatualizadas
- `needs_attention` - VMs que precisam atenção

## 🔧 Troubleshooting

### Problemas Comuns

#### ❌ Erro de Conexão vCenter
```
Solução: Verificar credenciais e conectividade de rede
```

#### ❌ Timeout na Coleta
```
Solução: Aumentar cache_timeout ou reduzir número de propriedades coletadas
```

#### ❌ VMs Não Aparecem
```
Soluções:
- Verificar filtros no inventory.yml
- Confirmar que VMs não são templates
- Verificar permissões do usuário no vCenter
```

### Logs e Debug

#### Verificar Logs do AWX
```bash
# No container do AWX
docker logs awx_task
```

#### Debug do Inventário
- Habilitar `debug_facts_collection: true` no Job Template
- Verificar output detalhado dos playbooks

## 🔄 Manutenção

### Atualização Automática
- Configure sincronização automática do inventário
- Agende execução periódica dos relatórios
- Configure notificações para falhas

### Monitoramento
- Monitor VMs que precisam atenção
- Acompanhar alterações de estado
- Verificar VMware Tools desatualizadas

## 📚 Recursos Adicionais

- [Documentação AWX](https://docs.ansible.com/ansible-tower/)
- [VMware Collection](https://docs.ansible.com/ansible/latest/collections/community/vmware/)
- [Ansible Inventory](https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html)

---

**📅 Última atualização**: 2025-07-12  
**🏢 Organização**: ATI Piauí  
**🔒 Modo**: Somente Leitura