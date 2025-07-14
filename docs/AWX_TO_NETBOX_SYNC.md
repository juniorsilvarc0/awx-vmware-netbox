# 🚀 AWX to NetBox Inventory Sync

## 📋 Overview

This solution provides automated synchronization of VM inventory data from AWX/Ansible Tower to NetBox IPAM. It includes both a Python script for direct API integration and an Ansible playbook for orchestrated synchronization.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   VMware        │    │      AWX        │    │     NetBox      │
│   vCenter       │───▶│   Inventory     │───▶│     IPAM        │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        │              ┌─────────┴─────────┐              │
        │              │                   │              │
        │              │  🔄 Sync Process  │              │
        │              │                   │              │
        │              └─────────┬─────────┘              │
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                    ┌─────────────▼──────────────┐
                    │                            │
                    │    📊 Sync Components     │
                    │                            │
                    │  • Python Script          │
                    │  • Ansible Playbook       │
                    │  • Configuration Files    │
                    │  • Reporting Dashboard     │
                    │                            │
                    └────────────────────────────┘
```

## 📦 Components

### 1. Python Script (`scripts/awx_to_netbox_sync.py`)
- **Purpose**: Direct API integration between AWX and NetBox
- **Features**:
  - Fetches VM data from AWX API
  - Creates/updates NetBox objects (VMs, IPs, clusters, etc.)
  - Comprehensive error handling and logging
  - Configurable field mappings
  - Batch processing support

### 2. Ansible Playbook (`playbooks/vmware_to_netbox.yml`)
- **Purpose**: Orchestrated sync using Ansible modules
- **Features**:
  - Uses NetBox Ansible collection
  - Enhanced reporting with emojis
  - Tag-based VM classification
  - Statistics tracking
  - JSON report generation

### 3. Configuration Files
- **`config/awx_netbox_sync.json`**: Main configuration file
- **`requirements.txt`**: Python dependencies including NetBox libraries

## 🔧 Setup Instructions

### Prerequisites

1. **AWX/Ansible Tower**: Running instance with VMware inventory configured
2. **NetBox**: Running instance with API access
3. **Python 3.8+**: With pip package manager
4. **Ansible**: Version 2.13+ with netbox.netbox collection

### Installation

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
ansible-galaxy collection install netbox.netbox
```

2. **Configure Environment Variables**:
```bash
export AWX_URL="https://your-awx-instance.com"
export AWX_TOKEN="your-awx-api-token"
export AWX_INVENTORY_ID="1"
export NETBOX_URL="https://your-netbox-instance.com"
export NETBOX_TOKEN="your-netbox-api-token"
```

3. **Edit Configuration**:
```bash
cp config/awx_netbox_sync.json config/awx_netbox_sync.json.local
# Edit the local configuration file with your settings
```

## 🚀 Usage

### Using Python Script

```bash
# Basic sync
python3 scripts/awx_to_netbox_sync.py

# With custom config file
python3 scripts/awx_to_netbox_sync.py --config config/awx_netbox_sync.json.local

# Dry run mode
python3 scripts/awx_to_netbox_sync.py --dry-run

# Verbose logging
python3 scripts/awx_to_netbox_sync.py --verbose
```

### Using Ansible Playbook

```bash
# Basic sync
ansible-playbook -i inventory.yml playbooks/vmware_to_netbox.yml

# With specific environment variables
NETBOX_API=https://netbox.example.com \
NETBOX_TOKEN=your-token \
ansible-playbook -i inventory.yml playbooks/vmware_to_netbox.yml

# Limit to specific hosts
ansible-playbook -i inventory.yml playbooks/vmware_to_netbox.yml --limit "powered_on"
```

## 🔄 Synchronization Process

### Data Flow

1. **AWX API Query**: Fetches all hosts from specified inventory
2. **Data Validation**: Filters valid VMs and skips invalid entries
3. **NetBox Object Creation**: Creates/updates required NetBox objects:
   - Tenants
   - Sites
   - Cluster Types
   - Clusters
   - Device Roles
   - Platforms
   - Virtual Machines
   - IP Addresses
   - Interfaces
   - Tags

4. **Reporting**: Generates comprehensive sync reports

### Field Mappings

| AWX Field | NetBox Field | Description |
|-----------|-------------|-------------|
| `vm_name` | `name` | VM name |
| `vm_cpu_count` | `vcpus` | CPU count |
| `vm_memory_mb` | `memory` | Memory in MB |
| `vm_power_state` | `status` | Power state (active/offline) |
| `vm_ip_addresses` | `primary_ip` | IP addresses |
| `vm_guest_os` | `platform` | Operating system |
| `vm_cluster` | `cluster` | VMware cluster |
| `vm_environment` | `tags` | Environment classification |
| `vm_criticality` | `tags` | Criticality level |

## 📊 Reporting Features

### Console Output
- Real-time sync progress with emojis
- Detailed VM processing information
- Final statistics summary

### JSON Reports
- Comprehensive sync statistics
- Configuration details
- Environment and criticality breakdowns
- Exported to `/tmp/awx_netbox_sync_report_*.json`

### Example Report Output

```
╔════════════════════════════════════════════════════════════════╗
║                   🚀 AWX → NetBox Sync Report                 ║
╠════════════════════════════════════════════════════════════════╣
║ 📊 Total Hosts Processed: 1093                                ║
║ ✅ Valid VMs Found: 1087                                       ║
║ ⏱️  Sync Duration: 245 seconds                                ║
║ 🕐 Completed At: 2025-07-14T10:30:00Z                        ║
║                                                                ║
║ 🏷️  Environment Categories:                                   ║
║    production, development, testing, unknown                  ║
║                                                                ║
║ 🔴 Criticality Levels:                                        ║
║    high, medium, low                                          ║
║                                                                ║
║ 🎯 NetBox Instance: https://netbox.example.com               ║
║ 🏢 Tenant: ATI                                               ║
║ 🏗️  Site: ATI-SLC-HCI                                        ║
╚════════════════════════════════════════════════════════════════╝
```

## 🏷️ Tagging System

### Automatic Tags

The sync process automatically creates and applies tags based on VM properties:

| Tag Category | Pattern | Colors |
|-------------|---------|---------|
| Environment | `env-{environment}` | Production: Red, Development: Green, Testing: Orange |
| Criticality | `criticality-{level}` | High: Red, Medium: Orange, Low: Green |
| Management | `awx-managed` | Blue |
| Platform | `vmware-vm` | Blue Grey |

### Tag Color Scheme

```yaml
tag_colors:
  env-production: "f44336"    # Red
  env-development: "4caf50"   # Green
  env-testing: "ff9800"       # Orange
  env-unknown: "9e9e9e"       # Grey
  criticality-high: "f44336"  # Red
  criticality-medium: "ff9800" # Orange
  criticality-low: "4caf50"   # Green
  awx-managed: "2196f3"       # Blue
  vmware-vm: "607d8b"         # Blue Grey
```

## ⚙️ Configuration Options

### Python Script Configuration

```json
{
  "sync_options": {
    "create_missing_objects": true,
    "update_existing_vms": true,
    "sync_ip_addresses": true,
    "sync_interfaces": true,
    "batch_size": 50
  },
  "filters": {
    "skip_templates": true,
    "skip_localhost": true,
    "required_fields": ["vm_name"]
  },
  "status_mappings": {
    "poweredOn": "active",
    "poweredOff": "offline",
    "suspended": "staged"
  }
}
```

### Ansible Playbook Variables

```yaml
sync_options:
  create_missing_objects: true
  update_existing_vms: true
  sync_ip_addresses: true
  sync_interfaces: true
  add_tags: true
  enable_reporting: true
```

## 🔍 Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Verify AWX and NetBox tokens
   - Check URL endpoints
   - Ensure API permissions

2. **SSL Certificate Issues**
   - Set `verify_ssl: false` in configuration
   - Or configure proper SSL certificates

3. **Missing Dependencies**
   - Install required Python packages
   - Install NetBox Ansible collection

4. **AWX Inventory Not Found**
   - Verify inventory ID
   - Check AWX permissions
   - Ensure dynamic inventory is working

### Debug Commands

```bash
# Test AWX API connection
curl -H "Authorization: Bearer $AWX_TOKEN" \
     "$AWX_URL/api/v2/inventories/$AWX_INVENTORY_ID/hosts/"

# Test NetBox API connection
curl -H "Authorization: Token $NETBOX_TOKEN" \
     "$NETBOX_URL/api/virtualization/virtual-machines/"

# Validate Ansible inventory
ansible-inventory -i inventory.yml --list

# Check NetBox collection
ansible-galaxy collection list netbox.netbox
```

## 📈 Performance Considerations

### Optimization Tips

1. **Batch Processing**: Use appropriate batch sizes for large inventories
2. **Caching**: Enable caching for AWX inventory
3. **Filtering**: Use filters to exclude unnecessary hosts
4. **Parallel Processing**: Consider running sync in parallel for large environments

### Monitoring

- Check sync logs in `/tmp/awx_netbox_sync.log`
- Monitor API response times
- Track sync duration and success rates
- Review error patterns in logs

## 🔒 Security Considerations

### API Tokens
- Use dedicated service accounts
- Implement token rotation
- Store tokens securely (AWX credentials, environment variables)

### Network Security
- Use HTTPS for all API communications
- Implement proper firewall rules
- Consider VPN for cross-datacenter sync

### Data Privacy
- Review data being synchronized
- Ensure compliance with data protection regulations
- Implement appropriate access controls

## 📚 References

- [NetBox API Documentation](https://netbox.readthedocs.io/en/stable/rest-api/)
- [AWX API Documentation](https://docs.ansible.com/ansible-tower/latest/html/towerapi/)
- [NetBox Ansible Collection](https://docs.ansible.com/ansible/latest/collections/netbox/netbox/)
- [VMware Dynamic Inventory](https://docs.ansible.com/ansible/latest/collections/community/vmware/vmware_vm_inventory_inventory.html)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Last Updated**: 2025-07-14  
**Version**: 1.0.0  
**Author**: ATI Piauí Infrastructure Team