# 🚨 Troubleshooting AWX Job Template

## 🔍 Problema: Job falha sem logs

**Sintomas:**
- Job Template falha após 2-3 minutos
- Não aparecem logs detalhados
- Status apenas mostra "Failed"

## 🎯 Diagnóstico Rápido

### **1. Execute o playbook de debug primeiro**

```yaml
Job Template para Debug:
Name: DEBUG - NetBox Sync
Playbook: playbooks/debug_awx_sync.yml
Inventory: VMware Inventory
```

### **2. Principais causas da falha silenciosa**

#### **🔑 A. Credenciais NetBox não configuradas**

**Problema:** Custom Credential Type não existe ou não está associado ao Job Template

**Solução:**
1. Criar Custom Credential Type "NetBox API":

```yaml
Administration → Credential Types → Add

Name: NetBox API
Kind: Cloud

Input Configuration:
fields:
  - id: netbox_api_url
    type: string
    label: NetBox API URL
    help_text: "Ex: https://netbox.example.com"
  - id: netbox_api_token
    type: string
    label: NetBox API Token
    secret: true
required:
  - netbox_api_url
  - netbox_api_token

Injector Configuration:
extra_vars:
  netbox_api_url: "{{ netbox_api_url }}"
  netbox_api_token: "{{ netbox_api_token }}"
```

2. Criar Credential usando o tipo acima:
```yaml
Resources → Credentials → Add

Name: NetBox Production
Credential Type: NetBox API
NetBox API URL: http://177.93.133.239:8000
NetBox API Token: [seu-token-aqui]
```

3. Associar ao Job Template:
```yaml
Templates → [Seu Template] → Edit
Credentials: 
  - VMware vCenter (se existir)
  - NetBox Production  ← ADICIONAR ESTA
```

#### **🏗️ B. Collections não instaladas**

**Problema:** `netbox.netbox` collection não está disponível

**Solução:** O arquivo `requirements.yml` resolve automaticamente, mas pode demorar:

```yaml
# Verifique se requirements.yml está na raiz do projeto
requirements.yml deve conter:
collections:
  - name: netbox.netbox
    version: ">=3.21.0"
```

#### **📋 C. Inventário vazio ou sem VMs válidas**

**Problema:** Inventário VMware não tem hosts ou variáveis `vm_name`

**Solução:**
1. Verificar inventário VMware:
```yaml
Inventories → VMware Inventory → Hosts
- Deve ter 1093+ hosts
- Hosts devem ter variável vm_name
```

2. Testar inventário:
```yaml
Inventories → VMware Inventory → Sources → Sync
```

#### **🌐 D. NetBox inacessível**

**Problema:** AWX não consegue acessar NetBox

**Solução:**
1. Testar conectividade do AWX:
```bash
# No container/host do AWX
curl -H "Authorization: Token SEU_TOKEN" \
     http://177.93.133.239:8000/api/status/
```

2. Verificar firewall/proxy entre AWX e NetBox

## 🚀 Soluções por Etapas

### **Etapa 1: Usar playbook simplificado**

1. Criar novo Job Template:
```yaml
Name: TESTE - NetBox Sync Simples
Inventory: VMware Inventory
Project: AWX to NetBox Sync
Playbook: playbooks/simple_netbox_sync.yml
Credentials: NetBox Production
Extra Variables:
  awx_netbox_debug: true
  awx_netbox_max_vms: 5  # Processar apenas 5 VMs para teste
```

2. Executar e verificar logs detalhados

### **Etapa 2: Verificar configuração**

1. Criar Job Template de debug:
```yaml
Name: DEBUG - Verificar Configuração
Playbook: playbooks/debug_awx_sync.yml
Inventory: VMware Inventory
```

2. Executar e analisar saída

### **Etapa 3: Configurar credenciais corretamente**

**Exemplo de configuração completa:**

```yaml
# 1. Custom Credential Type
Name: NetBox API
Input/Injector: [conforme acima]

# 2. Credential
Name: NetBox ATI
Type: NetBox API
URL: http://177.93.133.239:8000
Token: [token-valido]

# 3. Job Template
Name: Sync VMware to NetBox
Inventory: VMware Inventory
Project: AWX to NetBox Sync
Playbook: playbooks/simple_netbox_sync.yml  # Começar com este
Credentials:
  - NetBox ATI
Extra Variables:
  awx_netbox_debug: true
  awx_netbox_max_vms: 10
  awx_netbox_datacenter: "ATI-SLC-HCI"
  awx_netbox_tenant: "ATI"
```

## 🔍 Checklist de Verificação

### **✅ Pré-requisitos**
- [ ] Custom Credential Type "NetBox API" criado
- [ ] Credential com URL e token NetBox configurada
- [ ] Project sincronizado com repositório Git
- [ ] Inventário VMware populado (1093+ hosts)
- [ ] NetBox acessível da rede AWX

### **✅ Configuração Job Template**
- [ ] Playbook correto selecionado
- [ ] Inventário VMware selecionado
- [ ] Credential NetBox associada
- [ ] Extra Variables configuradas
- [ ] Limite de hosts (opcional para teste)

### **✅ Teste de Conectividade**
- [ ] AWX consegue acessar NetBox via HTTP
- [ ] Token NetBox é válido
- [ ] Inventário VMware tem dados de VMs
- [ ] Variables `vm_name` existem nos hosts

## 🎯 Comandos de Debug

### **1. Verificar token NetBox**
```bash
curl -H "Authorization: Token SEU_TOKEN" \
     http://177.93.133.239:8000/api/status/
```

### **2. Listar VMs no NetBox**
```bash
curl -H "Authorization: Token SEU_TOKEN" \
     http://177.93.133.239:8000/api/virtualization/virtual-machines/
```

### **3. Verificar inventário AWX via API**
```bash
curl -H "Authorization: Bearer AWX_TOKEN" \
     https://awx.example.com/api/v2/inventories/ID/hosts/
```

## 🚨 Problemas Específicos

### **Erro: "No module named netbox"**
**Causa:** Collection não instalada
**Solução:** Aguardar ou forçar reinstalação de requirements.yml

### **Erro: "401 Unauthorized"**
**Causa:** Token NetBox inválido
**Solução:** Gerar novo token no NetBox Admin

### **Erro: "Connection timeout"**
**Causa:** NetBox inacessível
**Solução:** Verificar rede/firewall entre AWX e NetBox

### **Erro: "No hosts matched"**
**Causa:** Inventário vazio ou filtro muito restritivo
**Solução:** Verificar sync do inventário VMware

## 📞 Fluxo de Resolução

```
1. Execute debug_awx_sync.yml
   ↓
2. Identifique problema específico
   ↓
3. Execute simple_netbox_sync.yml com limite baixo
   ↓
4. Se funcionar, aumente limite gradualmente
   ↓
5. Migre para awx_job_template_sync.yml completo
```

## 🎯 Configuração Mínima Funcional

```yaml
# Job Template Mínimo
Name: NetBox Sync Mínimo
Inventory: VMware Inventory
Project: AWX to NetBox Sync
Playbook: playbooks/simple_netbox_sync.yml
Credentials: NetBox ATI
Limit: powered_on[:10]  # Apenas 10 VMs ligadas
Extra Variables:
  awx_netbox_debug: true
  awx_netbox_max_vms: 10
  NETBOX_API: "http://177.93.133.239:8000"
  NETBOX_TOKEN: "seu-token-aqui"
```

Esta configuração deve funcionar mesmo sem Custom Credential Type configurado.