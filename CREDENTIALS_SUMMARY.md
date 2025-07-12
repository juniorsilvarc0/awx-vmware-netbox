# 🔐 Resumo de Credenciais AWX

Este documento consolida todos os Custom Credential Types necessários para o projeto.

## 📋 Custom Credential Types Necessários

### 1. **VCenter-vars** (Para vCenter/VMware)

#### Input Configuration:
```yaml
fields:
  - id: VCENTER_HOST
    type: string
    label: vCenter Hostname
  - id: VCENTER_USER
    type: string
    label: vCenter Username
  - id: VCENTER_PASSWORD
    type: string
    label: vCenter Password
    secret: true
  - id: DATACENTER_NAME
    type: string
    label: Datacenter Name
```

#### Injector Configuration:
```yaml
env:
  VCENTER_HOST: '{{ VCENTER_HOST }}'
  VCENTER_USER: '{{ VCENTER_USER }}'
  DATACENTER_NAME: '{{ DATACENTER_NAME }}'
  VCENTER_PASSWORD: '{{ VCENTER_PASSWORD }}'
```

### 2. **Netbox Credentials** (Para NetBox API)

#### Input Configuration:
```yaml
fields:
  - id: NETBOX_API
    type: string
    label: NetBox Host URL
  - id: NETBOX_TOKEN
    type: string
    label: NetBox API Token
    secret: true
required:
  - NETBOX_API
  - NETBOX_TOKEN
```

#### Injector Configuration:
```yaml
env:
  NETBOX_API: '{{ NETBOX_API }}'
  NETBOX_TOKEN: '{{ NETBOX_TOKEN }}'
```

## 🔗 Correspondência Code ↔️ AWX

### VMware Plugin (inventory_plugins/vmware_dynamic.py)
| Variável Python | Custom Credential Field | Environment Variable |
|----------------|-------------------------|----------------------|
| `os.environ.get('VCENTER_HOST')` | VCENTER_HOST | VCENTER_HOST |
| `os.environ.get('VCENTER_USER')` | VCENTER_USER | VCENTER_USER |
| `os.environ.get('VCENTER_PASSWORD')` | VCENTER_PASSWORD | VCENTER_PASSWORD |
| `os.environ.get('DATACENTER_NAME')` | DATACENTER_NAME | DATACENTER_NAME |

### NetBox Playbook (playbooks/vmware_to_netbox.yml)
| Variável Ansible | Custom Credential Field | Environment Variable |
|-----------------|-------------------------|----------------------|
| `{{ lookup('env', 'NETBOX_API') }}` | NETBOX_API | NETBOX_API |
| `{{ lookup('env', 'NETBOX_TOKEN') }}` | NETBOX_TOKEN | NETBOX_TOKEN |

## 📊 Credenciais a Criar no AWX

### 1. Credencial vCenter
```
Name: vCenter ATI Production
Credential Type: VCenter-vars
Fields:
  VCENTER_HOST: vcsa04.ati.pi.gov.br
  VCENTER_USER: netbox-ro@VSPHERE.LOCAL
  VCENTER_PASSWORD: [senha_real]
  DATACENTER_NAME: ATI-SLC-HCI
```

### 2. Credencial NetBox
```
Name: NetBox ATI API
Credential Type: Netbox Credentials
Fields:
  NETBOX_API: http://177.93.133.239:8000
  NETBOX_TOKEN: [token_real]
```

## 🎯 Uso nas Templates

### Inventory Source
- **Credential**: `vCenter ATI Production` (VCenter-vars)
- **Arquivo**: `inventory.yml`

### Job Template - Inventário
- **Playbook**: `playbooks/test_inventory.yml`
- **Credentials**: `vCenter ATI Production`

### Job Template - Sincronização NetBox
- **Playbook**: `playbooks/vmware_to_netbox.yml`
- **Credentials**: 
  - `vCenter ATI Production` (para inventário)
  - `NetBox ATI API` (para sincronização)

## ✅ Verificação

### Como Testar se Está Funcionando

#### 1. Inventário VMware
```bash
# No AWX, verificar se a inventory source sincroniza sem erros
# Deve aparecer lista de VMs nos grupos:
# - powered_on, powered_off
# - windows, linux
# - high_cpu, high_memory, etc.
```

#### 2. Sincronização NetBox
```bash
# Job Template deve executar sem erros de autenticação
# Verificar no NetBox se:
# - Sites são criados automaticamente
# - Devices (VMs) aparecem corretamente
# - IPs são atribuídos
```

## 🔒 Segurança Garantida

### ✅ Pontos de Segurança
- **Nenhuma credencial hardcoded** no repositório
- **Passwords marcados como secret** nos credential types
- **Tokens criptografados** pelo AWX
- **Separação de responsabilidades** (vCenter vs NetBox)
- **Auditoria completa** no AWX
- **Rotação fácil** das credenciais

### 📋 Checklist de Segurança
- [ ] Custom Credential Types criados
- [ ] Credenciais preenchidas com dados reais
- [ ] Passwords/Tokens marcados como secret
- [ ] Testado em ambiente de desenvolvimento
- [ ] Documentação atualizada
- [ ] Backup das configurações AWX

---

**🚀 RESULTADO**: Sistema totalmente integrado e seguro para coleta de VMs VMware e sincronização com NetBox via AWX!