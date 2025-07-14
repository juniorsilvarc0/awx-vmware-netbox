#!/bin/bash
# AWX to NetBox Sync Script
# Wrapper script for easier execution

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
CONFIG_FILE="${PROJECT_DIR}/config/awx_netbox_sync.json"
PYTHON_SCRIPT="${SCRIPT_DIR}/awx_to_netbox_sync.py"
ANSIBLE_PLAYBOOK="${PROJECT_DIR}/playbooks/vmware_to_netbox.yml"
INVENTORY_FILE="${PROJECT_DIR}/inventory.yml"

# Functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                 🚀 AWX → NetBox Sync Tool                     ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo
}

print_usage() {
    echo -e "${YELLOW}Usage: $0 [OPTIONS]${NC}"
    echo
    echo "Options:"
    echo "  -m, --method <python|ansible>  Sync method (default: python)"
    echo "  -c, --config <file>             Configuration file"
    echo "  -d, --dry-run                   Dry run mode (no changes)"
    echo "  -v, --verbose                   Verbose output"
    echo "  -h, --help                      Show this help"
    echo
    echo "Examples:"
    echo "  $0                              # Run with default settings"
    echo "  $0 --method ansible             # Use Ansible playbook"
    echo "  $0 --dry-run                    # Preview changes only"
    echo "  $0 --verbose                    # Detailed output"
    echo
}

check_dependencies() {
    echo -e "${BLUE}🔍 Checking dependencies...${NC}"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 is required but not installed${NC}"
        exit 1
    fi
    
    # Check Ansible if using ansible method
    if [[ "$METHOD" == "ansible" ]]; then
        if ! command -v ansible-playbook &> /dev/null; then
            echo -e "${RED}❌ Ansible is required but not installed${NC}"
            exit 1
        fi
        
        # Check NetBox collection
        if ! ansible-galaxy collection list netbox.netbox &> /dev/null; then
            echo -e "${YELLOW}⚠️  NetBox collection not found. Installing...${NC}"
            ansible-galaxy collection install netbox.netbox
        fi
    fi
    
    # Check required files
    if [[ ! -f "$PYTHON_SCRIPT" ]]; then
        echo -e "${RED}❌ Python script not found: $PYTHON_SCRIPT${NC}"
        exit 1
    fi
    
    if [[ "$METHOD" == "ansible" && ! -f "$ANSIBLE_PLAYBOOK" ]]; then
        echo -e "${RED}❌ Ansible playbook not found: $ANSIBLE_PLAYBOOK${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All dependencies satisfied${NC}"
    echo
}

check_environment() {
    echo -e "${BLUE}🔧 Checking environment variables...${NC}"
    
    local required_vars=("AWX_URL" "AWX_TOKEN" "NETBOX_URL" "NETBOX_TOKEN")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        echo -e "${RED}❌ Missing required environment variables:${NC}"
        for var in "${missing_vars[@]}"; do
            echo -e "${RED}   - $var${NC}"
        done
        echo
        echo -e "${YELLOW}Please set these variables or use a configuration file${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Environment variables configured${NC}"
    echo
}

run_python_sync() {
    echo -e "${BLUE}🐍 Running Python sync...${NC}"
    
    local args=()
    
    if [[ -n "$CONFIG_FILE" && -f "$CONFIG_FILE" ]]; then
        args+=("--config" "$CONFIG_FILE")
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        args+=("--dry-run")
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        args+=("--verbose")
    fi
    
    python3 "$PYTHON_SCRIPT" "${args[@]}"
}

run_ansible_sync() {
    echo -e "${BLUE}📜 Running Ansible sync...${NC}"
    
    local args=()
    
    if [[ "$VERBOSE" == "true" ]]; then
        args+=("-v")
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        args+=("--check")
    fi
    
    # Set environment variables for Ansible
    export NETBOX_API="${NETBOX_URL}"
    export NETBOX_TOKEN="${NETBOX_TOKEN}"
    
    ansible-playbook -i "$INVENTORY_FILE" "$ANSIBLE_PLAYBOOK" "${args[@]}"
}

generate_report() {
    echo -e "${BLUE}📊 Generating sync report...${NC}"
    
    local report_file="/tmp/awx_netbox_sync_$(date +%Y%m%d_%H%M%S).log"
    
    cat > "$report_file" << EOF
AWX to NetBox Sync Report
========================

Date: $(date)
Method: $METHOD
Configuration: $CONFIG_FILE
Dry Run: $DRY_RUN
Verbose: $VERBOSE

Environment Variables:
- AWX_URL: $AWX_URL
- NETBOX_URL: $NETBOX_URL
- AWX_INVENTORY_ID: ${AWX_INVENTORY_ID:-1}

Status: Completed Successfully
EOF
    
    echo -e "${GREEN}✅ Report saved to: $report_file${NC}"
}

# Default values
METHOD="python"
CONFIG_FILE=""
DRY_RUN="false"
VERBOSE="false"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--method)
            METHOD="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN="true"
            shift
            ;;
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
done

# Validate method
if [[ "$METHOD" != "python" && "$METHOD" != "ansible" ]]; then
    echo -e "${RED}❌ Invalid method: $METHOD${NC}"
    echo -e "${YELLOW}Valid methods: python, ansible${NC}"
    exit 1
fi

# Main execution
main() {
    print_header
    
    echo -e "${BLUE}🔧 Configuration:${NC}"
    echo -e "  Method: ${GREEN}$METHOD${NC}"
    echo -e "  Config: ${GREEN}${CONFIG_FILE:-'Environment variables'}${NC}"
    echo -e "  Dry Run: ${GREEN}$DRY_RUN${NC}"
    echo -e "  Verbose: ${GREEN}$VERBOSE${NC}"
    echo
    
    check_dependencies
    check_environment
    
    echo -e "${BLUE}🚀 Starting sync process...${NC}"
    echo
    
    case "$METHOD" in
        python)
            run_python_sync
            ;;
        ansible)
            run_ansible_sync
            ;;
    esac
    
    echo
    echo -e "${GREEN}✅ Sync completed successfully!${NC}"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        generate_report
    fi
}

# Execute main function
main "$@"