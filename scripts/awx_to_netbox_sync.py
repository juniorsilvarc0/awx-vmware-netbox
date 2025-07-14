#!/usr/bin/env python3
"""
AWX to NetBox Inventory Sync Script
Fetches VM inventory data from AWX API and syncs to NetBox
"""

import os
import sys
import json
import requests
import argparse
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from urllib3.exceptions import InsecureRequestWarning
import logging
from datetime import datetime

# Suppress SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class AWXToNetBoxSync:
    """
    Synchronizes VM inventory data from AWX to NetBox
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the sync client with configuration"""
        self.config = config
        self.session = requests.Session()
        self.session.verify = config.get('verify_ssl', False)
        
        # Configure logging
        self.setup_logging()
        
        # AWX configuration
        self.awx_url = config['awx_url']
        self.awx_token = config['awx_token']
        self.inventory_id = config['inventory_id']
        
        # NetBox configuration
        self.netbox_url = config['netbox_url']
        self.netbox_token = config['netbox_token']
        
        # Default values
        self.default_site = config.get('default_site', 'ATI-SLC-HCI')
        self.default_tenant = config.get('default_tenant', 'ATI')
        self.default_cluster_type = config.get('default_cluster_type', 'VMware vSphere')
        self.default_role = config.get('default_role', 'server')
        
        # Setup session headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def setup_logging(self):
        """Configure logging"""
        log_level = self.config.get('log_level', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('/tmp/awx_netbox_sync.log')
            ]
        )
        self.logger = logging.getLogger('AWXToNetBoxSync')
    
    def get_awx_inventory_hosts(self) -> List[Dict[str, Any]]:
        """Fetch all hosts from AWX inventory"""
        self.logger.info(f"Fetching hosts from AWX inventory ID: {self.inventory_id}")
        
        # Set AWX authentication
        self.session.headers['Authorization'] = f'Bearer {self.awx_token}'
        
        hosts = []
        url = urljoin(self.awx_url, f'/api/v2/inventories/{self.inventory_id}/hosts/')
        
        while url:
            try:
                response = self.session.get(url)
                response.raise_for_status()
                
                data = response.json()
                hosts.extend(data.get('results', []))
                
                # Handle pagination
                url = data.get('next')
                if url and not url.startswith('http'):
                    url = urljoin(self.awx_url, url)
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error fetching AWX inventory: {e}")
                raise
        
        self.logger.info(f"Retrieved {len(hosts)} hosts from AWX")
        return hosts
    
    def get_host_variables(self, host_id: int) -> Dict[str, Any]:
        """Fetch host variables from AWX"""
        url = urljoin(self.awx_url, f'/api/v2/hosts/{host_id}/variable_data/')
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error fetching variables for host {host_id}: {e}")
            return {}
    
    def netbox_request(self, endpoint: str, method: str = 'GET', data: Dict = None) -> Dict:
        """Make a request to NetBox API"""
        url = urljoin(self.netbox_url, f'/api/{endpoint}/')
        
        # Set NetBox authentication
        headers = {
            'Authorization': f'Token {self.netbox_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers)
            elif method == 'POST':
                response = self.session.post(url, headers=headers, json=data)
            elif method == 'PUT':
                response = self.session.put(url, headers=headers, json=data)
            elif method == 'PATCH':
                response = self.session.patch(url, headers=headers, json=data)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"NetBox API error for {endpoint}: {e}")
            if hasattr(e, 'response') and e.response:
                self.logger.error(f"Response: {e.response.text}")
            raise
    
    def create_or_get_tenant(self, name: str) -> Dict:
        """Create or get NetBox tenant"""
        slug = name.lower().replace(' ', '-')
        
        # Try to get existing tenant
        try:
            tenants = self.netbox_request(f'tenancy/tenants/?slug={slug}')
            if tenants.get('results'):
                return tenants['results'][0]
        except:
            pass
        
        # Create new tenant
        tenant_data = {
            'name': name,
            'slug': slug
        }
        
        try:
            return self.netbox_request('tenancy/tenants', 'POST', tenant_data)
        except:
            self.logger.warning(f"Could not create tenant {name}")
            return {}
    
    def create_or_get_site(self, name: str, tenant_id: int = None) -> Dict:
        """Create or get NetBox site"""
        slug = name.lower().replace(' ', '-').replace('_', '-')
        
        # Try to get existing site
        try:
            sites = self.netbox_request(f'dcim/sites/?slug={slug}')
            if sites.get('results'):
                return sites['results'][0]
        except:
            pass
        
        # Create new site
        site_data = {
            'name': name,
            'slug': slug,
            'status': 'active'
        }
        
        if tenant_id:
            site_data['tenant'] = tenant_id
        
        try:
            return self.netbox_request('dcim/sites', 'POST', site_data)
        except:
            self.logger.warning(f"Could not create site {name}")
            return {}
    
    def create_or_get_cluster_type(self, name: str) -> Dict:
        """Create or get NetBox cluster type"""
        slug = name.lower().replace(' ', '-')
        
        # Try to get existing cluster type
        try:
            cluster_types = self.netbox_request(f'virtualization/cluster-types/?slug={slug}')
            if cluster_types.get('results'):
                return cluster_types['results'][0]
        except:
            pass
        
        # Create new cluster type
        cluster_type_data = {
            'name': name,
            'slug': slug
        }
        
        try:
            return self.netbox_request('virtualization/cluster-types', 'POST', cluster_type_data)
        except:
            self.logger.warning(f"Could not create cluster type {name}")
            return {}
    
    def create_or_get_cluster(self, name: str, cluster_type_id: int, site_id: int = None, tenant_id: int = None) -> Dict:
        """Create or get NetBox cluster"""
        # Try to get existing cluster
        try:
            clusters = self.netbox_request(f'virtualization/clusters/?name={name}')
            if clusters.get('results'):
                return clusters['results'][0]
        except:
            pass
        
        # Create new cluster
        cluster_data = {
            'name': name,
            'type': cluster_type_id
        }
        
        if site_id:
            cluster_data['site'] = site_id
        if tenant_id:
            cluster_data['tenant'] = tenant_id
        
        try:
            return self.netbox_request('virtualization/clusters', 'POST', cluster_data)
        except:
            self.logger.warning(f"Could not create cluster {name}")
            return {}
    
    def create_or_get_device_role(self, name: str) -> Dict:
        """Create or get NetBox device role"""
        slug = name.lower().replace(' ', '-')
        
        # Try to get existing role
        try:
            roles = self.netbox_request(f'dcim/device-roles/?slug={slug}')
            if roles.get('results'):
                return roles['results'][0]
        except:
            pass
        
        # Create new role
        role_data = {
            'name': name,
            'slug': slug,
            'color': '2196f3',
            'vm_role': True
        }
        
        try:
            return self.netbox_request('dcim/device-roles', 'POST', role_data)
        except:
            self.logger.warning(f"Could not create device role {name}")
            return {}
    
    def create_or_get_platform(self, name: str) -> Dict:
        """Create or get NetBox platform"""
        slug = name.lower().replace(' ', '-').replace('(', '').replace(')', '')
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        
        # Try to get existing platform
        try:
            platforms = self.netbox_request(f'dcim/platforms/?slug={slug}')
            if platforms.get('results'):
                return platforms['results'][0]
        except:
            pass
        
        # Create new platform
        platform_data = {
            'name': name,
            'slug': slug
        }
        
        try:
            return self.netbox_request('dcim/platforms', 'POST', platform_data)
        except:
            self.logger.warning(f"Could not create platform {name}")
            return {}
    
    def sync_vm_to_netbox(self, vm_data: Dict[str, Any], tenant_id: int, site_id: int, 
                         cluster_id: int, role_id: int, platform_id: int = None) -> bool:
        """Sync a single VM to NetBox"""
        vm_name = vm_data.get('name', vm_data.get('vm_name', 'Unknown'))
        
        # Prepare VM data
        netbox_vm_data = {
            'name': vm_name,
            'cluster': cluster_id,
            'role': role_id,
            'tenant': tenant_id,
            'vcpus': vm_data.get('vm_cpu_count', 1),
            'memory': vm_data.get('vm_memory_mb', 1024),
            'status': 'active' if vm_data.get('vm_power_state') == 'poweredOn' else 'offline',
            'comments': self.generate_vm_comments(vm_data)
        }
        
        if platform_id:
            netbox_vm_data['platform'] = platform_id
        
        try:
            # Check if VM already exists
            existing_vms = self.netbox_request(f'virtualization/virtual-machines/?name={vm_name}')
            
            if existing_vms.get('results'):
                # Update existing VM
                vm_id = existing_vms['results'][0]['id']
                self.netbox_request(f'virtualization/virtual-machines/{vm_id}', 'PATCH', netbox_vm_data)
                self.logger.info(f"Updated VM: {vm_name}")
            else:
                # Create new VM
                created_vm = self.netbox_request('virtualization/virtual-machines', 'POST', netbox_vm_data)
                self.logger.info(f"Created VM: {vm_name}")
            
            # Sync IP addresses if available
            if vm_data.get('vm_ip_addresses'):
                self.sync_vm_ip_addresses(vm_name, vm_data['vm_ip_addresses'], tenant_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error syncing VM {vm_name}: {e}")
            return False
    
    def sync_vm_ip_addresses(self, vm_name: str, ip_addresses: List[str], tenant_id: int):
        """Sync VM IP addresses to NetBox"""
        for ip_address in ip_addresses:
            if not ip_address or ip_address == 'N/A':
                continue
                
            # Add subnet mask if not present
            if '/' not in ip_address:
                ip_address += '/24'
            
            ip_data = {
                'address': ip_address,
                'status': 'active',
                'tenant': tenant_id,
                'description': f'IP address for {vm_name}'
            }
            
            try:
                # Check if IP already exists
                existing_ips = self.netbox_request(f'ipam/ip-addresses/?address={ip_address}')
                
                if not existing_ips.get('results'):
                    self.netbox_request('ipam/ip-addresses', 'POST', ip_data)
                    self.logger.info(f"Created IP address: {ip_address} for VM: {vm_name}")
                    
            except Exception as e:
                self.logger.warning(f"Error syncing IP {ip_address} for VM {vm_name}: {e}")
    
    def generate_vm_comments(self, vm_data: Dict[str, Any]) -> str:
        """Generate comments for NetBox VM"""
        comments = ["Imported from AWX Dynamic Inventory"]
        
        if vm_data.get('vm_uuid'):
            comments.append(f"UUID: {vm_data['vm_uuid']}")
        
        if vm_data.get('vm_folder'):
            comments.append(f"Folder: {vm_data['vm_folder']}")
        
        if vm_data.get('vm_environment'):
            comments.append(f"Environment: {vm_data['vm_environment']}")
        
        if vm_data.get('vm_criticality'):
            comments.append(f"Criticality: {vm_data['vm_criticality']}")
        
        if vm_data.get('vm_guest_family'):
            comments.append(f"Guest Family: {vm_data['vm_guest_family']}")
        
        comments.append(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return '\n'.join(comments)
    
    def sync_inventory(self) -> Dict[str, Any]:
        """Main sync function"""
        self.logger.info("Starting AWX to NetBox inventory sync")
        
        # Get AWX inventory data
        hosts = self.get_awx_inventory_hosts()
        
        # Create required NetBox objects
        tenant = self.create_or_get_tenant(self.default_tenant)
        site = self.create_or_get_site(self.default_site, tenant.get('id'))
        cluster_type = self.create_or_get_cluster_type(self.default_cluster_type)
        role = self.create_or_get_device_role(self.default_role)
        
        # Statistics
        stats = {
            'total_hosts': len(hosts),
            'synced_vms': 0,
            'failed_vms': 0,
            'skipped_hosts': 0,
            'start_time': datetime.now()
        }
        
        for host in hosts:
            # Get host variables
            host_vars = self.get_host_variables(host['id'])
            
            # Merge host data with variables
            vm_data = {**host, **host_vars}
            
            # Skip if not a valid VM
            if not self.is_valid_vm(vm_data):
                stats['skipped_hosts'] += 1
                continue
            
            # Get or create cluster for this VM
            cluster_name = vm_data.get('vm_cluster', 'Default Cluster')
            cluster = self.create_or_get_cluster(
                cluster_name, 
                cluster_type['id'], 
                site.get('id'), 
                tenant.get('id')
            )
            
            # Get or create platform if available
            platform_id = None
            if vm_data.get('vm_guest_os'):
                platform = self.create_or_get_platform(vm_data['vm_guest_os'])
                platform_id = platform.get('id')
            
            # Sync VM to NetBox
            success = self.sync_vm_to_netbox(
                vm_data, 
                tenant.get('id'), 
                site.get('id'), 
                cluster.get('id'), 
                role.get('id'), 
                platform_id
            )
            
            if success:
                stats['synced_vms'] += 1
            else:
                stats['failed_vms'] += 1
        
        stats['end_time'] = datetime.now()
        stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()
        
        self.logger.info(f"Sync completed: {stats}")
        return stats
    
    def is_valid_vm(self, vm_data: Dict[str, Any]) -> bool:
        """Check if host data represents a valid VM"""
        name = vm_data.get('name', vm_data.get('vm_name', ''))
        
        # Skip localhost and invalid names
        if not name or name in ['localhost', 'N/A']:
            return False
        
        # Must have vm_name variable
        if not vm_data.get('vm_name'):
            return False
        
        return True


def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables and config file"""
    config = {
        # AWX configuration
        'awx_url': os.getenv('AWX_URL', 'https://localhost'),
        'awx_token': os.getenv('AWX_TOKEN', ''),
        'inventory_id': int(os.getenv('AWX_INVENTORY_ID', '1')),
        
        # NetBox configuration
        'netbox_url': os.getenv('NETBOX_URL', 'https://localhost'),
        'netbox_token': os.getenv('NETBOX_TOKEN', ''),
        
        # Default values
        'default_site': os.getenv('DEFAULT_SITE', 'ATI-SLC-HCI'),
        'default_tenant': os.getenv('DEFAULT_TENANT', 'ATI'),
        'default_cluster_type': os.getenv('DEFAULT_CLUSTER_TYPE', 'VMware vSphere'),
        'default_role': os.getenv('DEFAULT_ROLE', 'server'),
        
        # Options
        'verify_ssl': os.getenv('VERIFY_SSL', 'false').lower() == 'true',
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
    }
    
    # Load config file if exists
    config_file = os.getenv('CONFIG_FILE', 'config.json')
    if os.path.exists(config_file):
        with open(config_file) as f:
            file_config = json.load(f)
            config.update(file_config)
    
    return config


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Sync AWX inventory to NetBox')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    if args.config:
        with open(args.config) as f:
            config.update(json.load(f))
    
    if args.verbose:
        config['log_level'] = 'DEBUG'
    
    # Validate required configuration
    required_vars = ['awx_url', 'awx_token', 'netbox_url', 'netbox_token']
    missing_vars = [var for var in required_vars if not config.get(var)]
    
    if missing_vars:
        print(f"Missing required configuration: {', '.join(missing_vars)}")
        print("Set environment variables or use config file")
        sys.exit(1)
    
    # Run sync
    try:
        sync_client = AWXToNetBoxSync(config)
        
        if args.dry_run:
            print("Dry run mode - no changes will be made")
            hosts = sync_client.get_awx_inventory_hosts()
            print(f"Found {len(hosts)} hosts in AWX inventory")
            return
        
        stats = sync_client.sync_inventory()
        
        print(f"\nSync Summary:")
        print(f"Total hosts: {stats['total_hosts']}")
        print(f"Synced VMs: {stats['synced_vms']}")
        print(f"Failed VMs: {stats['failed_vms']}")
        print(f"Skipped hosts: {stats['skipped_hosts']}")
        print(f"Duration: {stats['duration']:.2f} seconds")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()