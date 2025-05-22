from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import atexit
import getpass
import paramiko
import os
from prettytable import PrettyTable
import sys

# Screen clear
os.system('cls' if os.name == 'nt' else 'clear')

# Banner
def show_banner():
    print("=" * 60)
    print("🔧 ESXi DNS Manager".center(60))
    print("=" * 60)

show_banner()

"""
# Get credentials
vcenter_address = input("🌐 vCenter address: ")
vcenter_username = input("👤 vCenter SSO Username: ")
vcenter_password = getpass.getpass("🔐 vCenter SSO Password: ")
#esxi_username = input("ESXi Username: ")
#esxi_password = getpass.getpass("ESXi Password: ")
print()

# vCenter connection
context = ssl._create_unverified_context()
si = SmartConnect(host=vcenter_address, user=vcenter_username, pwd=vcenter_password, sslContext=context)
atexit.register(Disconnect, si)
content = si.RetrieveContent()
"""

# Function: Connect to vCenter
def get_si_instance(vcenter, user, pwd, port=443):
    context = ssl._create_unverified_context()
    try:
        si = SmartConnect(host=vcenter_address, user=vcenter_username, pwd=vcenter_password, port=port, sslContext=context)
        return si
    except vim.fault.InvalidLogin:
        print("❌ Invalid username or password. Please try again.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to connect to vCenter: {e}")
        sys.exit(1)

# Get credentials
vcenter_address = input("🌐 vCenter IP/FQDN: ")
vcenter_username = input("👤 vCenter SSO Username: ")
vcenter_password = getpass.getpass(prompt='🔐 vCenter SSO Password: ')

# Connect to vCenter using the function get_si_instance
si = get_si_instance(vcenter_address, vcenter_username, vcenter_password)
content = si.RetrieveContent()



def get_hosts():
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
    hosts = [host for host in container.view if host.runtime.connectionState == "connected"]
    container.Destroy()
    return hosts


def get_dns_config():
    hosts = get_hosts()

    for host in hosts:
        ip = host.name
        try:
            print("-" * 80)
            print(f"✅ {ip} 📝 DNS Config Content:")
            dt_system = host.configManager.networkSystem
            dns_address = dt_system.dnsConfig.address

            if dns_address:
                for dns_ip in dns_address:
                    print(f" DNS Server Address: {dns_ip}")
            else:
                print(f" DNS Server Address: None")

            dns_domain_name = dt_system.dnsConfig.domainName
            dns_hostname = dt_system.dnsConfig.hostName
            dns_search_domain = dt_system.dnsConfig.searchDomain
            print(f" DNS Domain Name: {dns_domain_name}")
            print(f" DNS Host Name: {dns_hostname}")

            if dns_search_domain:
                for dns_search in dns_search_domain:
                    print(f" DNS Search Domain: {dns_search}")
            else:
                print(f" DNS Search Domain: None")

            print("-" * 80)

        except Exception as e:
            print(f"{ip} ❌ Error retrieving DNS config file: {e}")
    return None


def change_dns_server_config():
    dns_input = input("🔧 Enter new DNS IPs (comma-separated, e.g. 192.168.1.1, 192.168.1.2): ")
    new_dns_servers = [ip.strip() for ip in dns_input.split(',') if ip.strip()]

    if not new_dns_servers:
        print("❌ No valid DNS servers provided. Aborting.")
        return

    hosts = get_hosts()

    for host in hosts:
        ip = host.name
        try:
            print(f"🔄 Updating DNS for {ip} to: {new_dns_servers}")
            network_system = host.configManager.networkSystem
            current_config = network_system.dnsConfig

            from pyVmomi import vim
            dns_config_spec = vim.host.DnsConfig(
                dynamicProperty=None,
                dhcp=current_config.dhcp,
                virtualNicDevice=current_config.virtualNicDevice,
                hostName=current_config.hostName,
                domainName=current_config.domainName,
                searchDomain=current_config.searchDomain,
                address=new_dns_servers
            )

            network_system.UpdateDnsConfig(dns_config_spec)
            print(f"✅ DNS updated successfully for {ip} \n")
            
        except Exception as e:
            print(f"{ip} ❌ Error updating DNS: {e} \n")


def change_dns_domain_config():
    dns_domain_input = input("🔧 Enter new DNS Domain: ")
    
    if not dns_domain_input:
        print("❌ No valid DNS domain provided. Aborting.")
        return

    hosts = get_hosts()

    for host in hosts:
        ip = host.name
        try:
            print(f"🔄 Updating DNS domain for {ip} to: {dns_domain_input}")
            network_system = host.configManager.networkSystem
            current_config = network_system.dnsConfig

            from pyVmomi import vim
            dns_config_spec = vim.host.DnsConfig(
                dynamicProperty=None,
                dhcp=current_config.dhcp,
                virtualNicDevice=current_config.virtualNicDevice,
                hostName=current_config.hostName,
                domainName=dns_domain_input,
                searchDomain=dns_domain_input,
                address=current_config.address
            )

            network_system.UpdateDnsConfig(dns_config_spec)
            print(f"✅ DNS domain updated successfully for {ip} \n")

        except Exception as e:
            print(f"{ip} ❌ Error updating DNS domain: {e} \n")



def connect_ssh(host, esxi_username, esxi_password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=esxi_username, password=esxi_password, timeout=10)
        return ssh
    except Exception as e:
        print(f"❌ Connection to {host} failed: {e}")
        return None


def run_command(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode().strip()
    error = stderr.read().decode().strip()
    return output if output else error


def flush_esxi_dns_cache():
    esxi_username = input("👤 ESXi Username: ")
    esxi_password = getpass.getpass("🔐 ESXi Password: ")
    esxi_command = "/etc/init.d/nscd restart"
    print()

    hosts = get_hosts()
    for host in hosts:
        ip = host.name
        host.configManager.serviceSystem.RestartService(id='TSM-SSH')
        ssh = connect_ssh(ip, esxi_username, esxi_password)
        print(f"🔄 Flushing the DNS cache on {ip}")
        if ssh:
            cmd = f"{esxi_command}"
            output = run_command(ssh, cmd)
            print(f" {output} \n")
            ssh.close()
        else:
            print(f"Failed to connect to {ip}")
    print()



def run_esxi_command():
    esxi_username = input("👤 ESXi Username: ")
    esxi_password = getpass.getpass("🔐 ESXi Password: ")
    esxi_command = input("⚙️  ESXi command: ")
    print()
    
    hosts = get_hosts()
    for host in hosts:
        ip = host.name
        host.configManager.serviceSystem.RestartService(id='TSM-SSH')
        ssh = connect_ssh(ip, esxi_username, esxi_password)
        print("-" * 80)
        print(f"🔄 Executing the command on {ip}")
        if ssh:
            cmd = f"{esxi_command}"
            output = run_command(ssh, cmd)
            print(f" {output} \n")
            ssh.close()
        else:
            print(f"Failed to connect to {ip}")
    print()




def main_menu():
    while True:
        print("\n===== ESXi DNS Manager =====")
        print("1. Check DNS config on all connected ESXi hosts")
        print("2. Change DNS Servers for all connected ESXi hosts")
        print("3. Change DNS Domain for all connected ESXi hosts")
        print("4. Flush DNS Cache on all connected ESXi hosts")
        print("5. Run a command on all connected ESXi hosts")
        print("6. TBD")
        print("0. Exit")
        choice = input("Enter your choice: ")

        if choice == "1":
            get_dns_config()
        elif choice == "2":
            change_dns_server_config()
        elif choice == "3":
            change_dns_domain_config()
        elif choice == "4":
            flush_esxi_dns_cache()
        elif choice == "5":
            run_esxi_command()
        elif choice == "6":
            print("TBD")
        elif choice == "7":
            print("TBD")
        elif choice == "0":
            print("👋 Exiting.")
            break
        else:
            print("❌ Invalid choice. Try again.")

if __name__ == "__main__":
    main_menu()
