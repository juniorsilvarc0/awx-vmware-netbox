# 🔐 Custom Credential Type para vCenter

Este documento mostra como criar o Custom Credential Type "VCenter-vars" no AWX.

## 📋 Criação do Custom Credential Type

### 1. Acessar Credential Types
1. Faça login no AWX
2. Vá para **Administration** → **Credential Types**
3. Clique em **Add** (➕)

### 2. Configurar o Credential Type

#### 📝 Basic Information
```
Name: VCenter-vars
Description: Custom credential type for VMware vCenter connection
```

#### 🔧 Input Configuration
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

#### 💉 Injector Configuration
```yaml
env:
  VCENTER_HOST: '{{ VCENTER_HOST }}'
  VCENTER_USER: '{{ VCENTER_USER }}'
  DATACENTER_NAME: '{{ DATACENTER_NAME }}'
  VCENTER_PASSWORD: '{{ VCENTER_PASSWORD }}'
```

### 3. Salvar o Credential Type
- Clique em **Save** para criar o custom credential type

## 🔗 Usando o Custom Credential Type

### 1. Criar Credencial
1. Vá para **Resources** → **Credentials**
2. Clique em **Add** (➕)
3. Configure:
   - **Name**: `vCenter ATI Production`
   - **Organization**: Sua organização
   - **Credential Type**: `VCenter-vars` (o tipo que você criou)

### 2. Preencher os Campos
```
vCenter Hostname: vcsa04.ati.pi.gov.br
vCenter Username: netbox-ro@VSPHERE.LOCAL
vCenter Password: [sua_senha_real]
Datacenter Name: ATI-SLC-HCI
```

### 3. Usar na Inventory Source
1. Vá para seu inventário → **Sources**
2. Edite a source do inventário
3. Em **Credentials**, selecione `vCenter ATI Production`
4. Salve e sincronize

## ✅ Verificação

### Como Confirmar que Está Funcionando
1. **Sync da Inventory Source**: Deve executar sem erros
2. **Logs da Source**: Não deve mostrar erros de autenticação
3. **VMs Coletadas**: Deve aparecer a lista de VMs do vCenter

### Debug de Problemas
```bash
# No container AWX, verificar se as variáveis estão sendo injetadas
echo $VCENTER_HOST
echo $VCENTER_USER
echo $DATACENTER_NAME
# VCENTER_PASSWORD não aparece por segurança
```

## 🔒 Segurança

### Vantagens do Custom Credential Type
- ✅ **Campos específicos**: Apenas os dados necessários
- ✅ **Password oculto**: Campo senha marcado como `secret: true`
- ✅ **Reutilizável**: Pode ser usado em múltiplos inventários
- ✅ **Auditável**: AWX registra uso das credenciais
- ✅ **Criptografado**: AWX encrypta automaticamente

### Melhores Práticas
- 🔐 Use contas de serviço dedicadas no vCenter
- 🔄 Rotacione senhas periodicamente
- 👥 Limite permissões apenas ao necessário (read-only)
- 📊 Monitor o uso das credenciais
- 🚫 Nunca compartilhe credenciais fora do AWX

---

**📋 Correspondência Exata**: Este custom credential type corresponde exatamente às variáveis de ambiente que o plugin `vmware_dynamic.py` espera:

- `VCENTER_HOST` → `os.environ.get('VCENTER_HOST')`
- `VCENTER_USER` → `os.environ.get('VCENTER_USER')`  
- `VCENTER_PASSWORD` → `os.environ.get('VCENTER_PASSWORD')`
- `DATACENTER_NAME` → `os.environ.get('DATACENTER_NAME')`

**🚀 Status**: ✅ Pronto para produção!