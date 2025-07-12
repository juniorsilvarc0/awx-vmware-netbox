# 🔐 Custom Credential Type para NetBox

Este documento mostra como criar o Custom Credential Type "NetBox-API" no AWX para integração segura com NetBox.

## 📋 Criação do Custom Credential Type NetBox

### 1. Acessar Credential Types
1. Faça login no AWX
2. Vá para **Administration** → **Credential Types**
3. Clique em **Add** (➕)

### 2. Configurar o NetBox Credential Type

#### 📝 Basic Information
```
Name: NetBox-API
Description: Custom credential type for NetBox API connection
```

#### 🔧 Input Configuration
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

#### 💉 Injector Configuration
```yaml
env:
  NETBOX_API: '{{ NETBOX_API }}'
  NETBOX_TOKEN: '{{ NETBOX_TOKEN }}'
```

### 3. Salvar o Credential Type
- Clique em **Save** para criar o custom credential type

## 🔗 Usando o NetBox Custom Credential Type

### 1. Criar Credencial NetBox
1. Vá para **Resources** → **Credentials**
2. Clique em **Add** (➕)
3. Configure:
   - **Name**: `NetBox ATI Production`
   - **Organization**: Sua organização
   - **Credential Type**: `NetBox-API` (o tipo que você criou)

### 2. Preencher os Campos
```
NetBox Host URL: http://177.93.133.239:8000
NetBox API Token: [seu_token_real_aqui]
```

### 3. Usar no Job Template
1. Crie um Job Template para sincronização
2. Em **Credentials**, adicione:
   - `vCenter ATI Production` (tipo VCenter-vars)
   - `NetBox ATI Production` (tipo NetBox-API)
3. Selecione o playbook `vmware_to_netbox.yml`

## ✅ Job Template Completo

### Configuração Recomendada
```
Name: VMware to NetBox Sync
Job Type: Run
Inventory: VMware VMs - ATI
Project: VMware Inventory - ATI
Playbook: playbooks/vmware_to_netbox.yml
Credentials: 
  - vCenter ATI Production (VCenter-vars)
  - NetBox ATI Production (NetBox-API)
Variables:
  dry_run: false
  batch_size: 50
  create_missing_objects: true
  update_existing: true
```

## 🔒 Segurança NetBox

### Boas Práticas para Token API
1. **Criar usuário dedicado** no NetBox para AWX
2. **Permissões mínimas necessárias**:
   - `dcim.add_device`
   - `dcim.change_device`
   - `dcim.view_device`
   - `dcim.add_site`
   - `dcim.view_site`
3. **Rotacionar tokens periodicamente**
4. **Monitor uso da API** nos logs do NetBox

### Token NetBox
Para obter o token:
1. Acesse NetBox → **Admin** → **Users**
2. Edite o usuário AWX
3. Vá para **API Tokens**
4. Clique em **Add Token**
5. Copie o token gerado

## 🔧 Verificação

### Como Confirmar Integração
1. **Job Template executa sem erros**
2. **VMs aparecem no NetBox** como devices
3. **Sites são criados automaticamente**
4. **Dados sincronizados corretamente**

### Debug de Problemas
```bash
# Verificar conectividade com NetBox
curl -H "Authorization: Token SEU_TOKEN" \
     http://177.93.133.239:8000/api/dcim/sites/

# Verificar se variáveis estão sendo injetadas no AWX
echo $NETBOX_API_URL
echo $NETBOX_API_TOKEN
```

## 📊 Dados Sincronizados

### Informações VMware → NetBox
- **VM Name** → **Device Name**
- **vCenter Datacenter** → **NetBox Site**
- **VM Cluster** → **NetBox Cluster**
- **IP Addresses** → **NetBox IP Addresses**
- **CPU/Memory** → **Custom Fields**
- **Power State** → **Device Status**

### 🔄 Mapeamento de Status (TODAS as VMs são sincronizadas)
| Estado VMware | Status NetBox | Descrição |
|---------------|---------------|-----------|
| `poweredOn` | `active` | ✅ VMs ligadas ficam como Ativo |
| `poweredOff` | `offline` | ❌ VMs desligadas ficam como Offline |
| `suspended` | `staged` | ⏸️ VMs suspensas ficam como Staged |

**IMPORTANTE**: O playbook sincroniza **TODAS** as VMs do inventário VMware (ligadas, desligadas e suspensas) para o NetBox com o status correto.

---

**🔐 SEGURANÇA GARANTIDA**: 
- ✅ Nenhuma credencial no código
- ✅ Tokens criptografados no AWX
- ✅ Conexões autenticadas
- ✅ Auditoria completa

**🚀 PRONTO PARA PRODUÇÃO**: Configure os dois credential types (VCenter-vars + NetBox-API) e execute a sincronização!