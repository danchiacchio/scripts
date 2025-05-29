#!/bin/python
#
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import getpass
import os
import paramiko
import sys

# Screen clear
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')
clear_screen()

# Banner
def show_banner():
    print("=" * 100)
    print("🔧 ESXi DNS Manager".center(100))
    print("=" * 100)
show_banner()


# Function: Connect to vCenter
def get_si_instance(vcenter, user, pwd, port=443):
    context = ssl._create_unverified_context()
    try:
        si = SmartConnect(host=vcenter, user=user, pwd=pwd, port=port, sslContext=context)
        return si
    except vim.fault.InvalidLogin:
        print("❌ Invalid username or password. Please try again.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to connect to vCenter: {e}")
        sys.exit(1)


# Get credentials
vcenter = input("🌐 vCenter IP/FQDN: ")
user = "administrator@vsphere.local"
user_input = input(f"👤 vCenter SSO Username (default: {user}): ")
if user_input:
    user = user_input
pwd = getpass.getpass(prompt='🔐 vCenter SSO Password: ')

# Connect to vCenter using the function get_si_instance
si = get_si_instance(vcenter, user, pwd)


# Function: Get all clusters
def get_all_clusters(si):
    content = si.RetrieveContent()
    container_view = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.ClusterComputeResource], True
    )
    clusters = {}
    for cluster in container_view.view:
        clusters[cluster.name] = cluster
    container_view.Destroy()
    return clusters


def get_connected_hosts_in_cluster(cluster):
    """
    Returns a list of connected ESXi host objects within the given cluster.

    :param cluster: vim.ClusterComputeResource
    :return: List of vim.HostSystem objects
    """
    connected_hosts = []
    for host in cluster.host:
        if host.runtime.connectionState == "connected":
            connected_hosts.append(host)
    return connected_hosts


# Get all clusters and show them
def get_clusters():
    clusters_dict = get_all_clusters(si)
    cluster_names = list(clusters_dict.keys())
    
    print("\n" + "="*60)
    print("📝 Available Clusters:")
    
    for idx, name in enumerate(cluster_names, 1):
        print(f"{idx}. {name}")
    print("=" * 60)

    return cluster_names, clusters_dict


"""
When you present the user with a numbered menu, you usually number from 1:
1) Cluster-A
2) Cluster-B
3) Cluster-C

But in Python, lists are zero-indexed:

cluster_names = ["Cluster-A", "Cluster-B", "Cluster-C"]
# Indexes are     [     0     ,     1     ,     2     ]

So, if the user enters 2, they mean the second cluster — Cluster-B.
But in Python, to get the second element, you have to use cluster_names[1].

selection - 1
We subtract 1 to convert the user's input to a valid Python index.

This means:
User types 1 → Python gets index 0
User types 2 → Python gets index 1
"""

def get_hosts_specific_cluster(cluster_names, clusters_dict):
    try:
        selection = int(input("\nEnter the number of the cluster to list all ESXi hosts: "))
        selected_name = cluster_names[selection - 1]
        selected_cluster = clusters_dict[selected_name]
    except (ValueError, IndexError):
        print("❌ Invalid selection.")
        Disconnect(si)
        exit(1)

    connected_hosts = get_connected_hosts_in_cluster(selected_cluster)

    if not connected_hosts:
        print("⚠️ No connected hosts found in the selected cluster.")
        return    

    print(f"\n✅ Connected hosts in cluster '{selected_cluster.name}':")
    for host in connected_hosts:
        print(f"{host.name}")



def get_dns_config_for_hosts(hosts):
    if not hosts:
        print("⚠️  No ESXi hosts found in the selected cluster.")
        return

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


def show_dns_config_for_cluster():
    cluster_names, clusters_dict = get_clusters()
    try:
        selection = int(input("\nEnter the number of the cluster: "))
        selected_name = cluster_names[selection - 1]
        selected_cluster = clusters_dict[selected_name]
    except (ValueError, IndexError):
        print("❌ Invalid selection.")
        Disconnect(si)
        exit(1)

    connected_hosts = get_connected_hosts_in_cluster(selected_cluster)
    #get_dns_config_for_hosts(connected_hosts)

    # Display sub-menu
    print("\n📋 Sub-Menu:")
    print("1. Run command on all hosts")
    print("2. Run command on a specific host")
    print("0. Back to the Main Menu")
    try:
        sub_option = int(input("Choose an option: "))
    except ValueError:
        print("❌ Invalid input.")
        return

    if sub_option == 1:
        get_dns_config_for_hosts(connected_hosts)
        return

    elif sub_option == 0:
        main_menu()

    elif sub_option == 2:
        print("\n🖥️  Available Hosts:")

        for idx, host in enumerate(connected_hosts, start=1):
            print(f"{idx}. {host.name}")

        try:
            host_selection = int(input("Select a host number: "))
            selected_host = connected_hosts[host_selection - 1]
            get_dns_config_for_hosts([selected_host])
            return

        except (ValueError, IndexError):
            print("❌ Invalid host selection.")
            return

    else:
        print("❌ Invalid option.")




def change_dns_server_config(hosts):
    dns_input = input("🔧 Enter new DNS IPs (comma-separated, e.g. 192.168.1.1, 192.168.1.2): ")
    new_dns_servers = [ip.strip() for ip in dns_input.split(',') if ip.strip()]

    if not new_dns_servers:
        print("❌ No valid DNS servers provided. Aborting.")
        return

    if not hosts:
        print("⚠️  No ESXi hosts found in the selected cluster.")
        return

    for host in hosts:
        ip = host.name
        try:
            print(f"🔄 Updating DNS for {ip} to: {new_dns_servers}")
            network_system = host.configManager.networkSystem
            current_config = network_system.dnsConfig

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
            
        
def change_dns_server():
    cluster_names, clusters_dict = get_clusters()
    try:
        selection = int(input("\nEnter the number of the cluster: "))
        selected_name = cluster_names[selection - 1]
        selected_cluster = clusters_dict[selected_name]
    except (ValueError, IndexError):
        print("❌ Invalid selection.")
        Disconnect(si)
        exit(1)
    
    connected_hosts = get_connected_hosts_in_cluster(selected_cluster)
    #change_dns_server_config(connected_hosts)

    # Display sub-menu
    print("\n📋 Sub-Menu:")
    print("1. Run command on all hosts")
    print("2. Run command on a specific host")
    print("0. Back to the Main Menu")
    try:
        sub_option = int(input("Choose an option: "))
    except ValueError:
        print("❌ Invalid input.")
        return

    if sub_option == 1:
        change_dns_server_config(connected_hosts)
        return

    elif sub_option == 0:
        main_menu()

    elif sub_option == 2:
        print("\n🖥️  Available Hosts:")

        for idx, host in enumerate(connected_hosts, start=1):
            print(f"{idx}. {host.name}")

        try:
            host_selection = int(input("Select a host number: "))
            selected_host = connected_hosts[host_selection - 1]
            change_dns_server_config([selected_host])
            return

        except (ValueError, IndexError):
            print("❌ Invalid host selection.")
            return

    else:
        print("❌ Invalid option.")




def change_dns_domain_config(hosts):
    dns_domain_input = input("🔧 Enter new DNS Domain: ")

    if not dns_domain_input:
        print("❌ No valid DNS domain provided. Aborting.")
        return
    
    if not hosts:
        print("⚠️  No ESXi hosts found in the selected cluster.")
        return
    
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


def change_dns_domain():
    cluster_names, clusters_dict = get_clusters()
    try:
        selection = int(input("\nEnter the number of the cluster: "))
        selected_name = cluster_names[selection - 1]
        selected_cluster = clusters_dict[selected_name]
    except (ValueError, IndexError):
        print("❌ Invalid selection.")
        Disconnect(si)
        exit(1)

    connected_hosts = get_connected_hosts_in_cluster(selected_cluster)
    #change_dns_domain_config(connected_hosts)

    # Display sub-menu
    print("\n📋 Sub-Menu:")
    print("1. Run command on all hosts")
    print("2. Run command on a specific host")
    print("0. Back to the Main Menu")
    try:
        sub_option = int(input("Choose an option: "))
    except ValueError:
        print("❌ Invalid input.")
        return

    if sub_option == 1:
        change_dns_domain_config(connected_hosts)
        return

    elif sub_option == 0:
        main_menu()

    elif sub_option == 2:
        print("\n🖥️  Available Hosts:")

        for idx, host in enumerate(connected_hosts, start=1):
            print(f"{idx}. {host.name}")

        try:
            host_selection = int(input("Select a host number: "))
            selected_host = connected_hosts[host_selection - 1]
            change_dns_domain_config([selected_host])
            return

        except (ValueError, IndexError):
            print("❌ Invalid host selection.")
            return

    else:
        print("❌ Invalid option.")



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


def flush_esxi_dns_cache(hosts):
    esxi_username = input("👤 ESXi Username: ")
    esxi_password = getpass.getpass("🔐 ESXi Password: ")
    esxi_command = "/etc/init.d/nscd restart"
    print()

    if not hosts:
        print("⚠️  No ESXi hosts found in the selected cluster.")
        return

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
            print(f"❌ Failed to connect to {ip}")
    print()


def flush_esxi_dns():
    cluster_names, clusters_dict = get_clusters()
    try:
        selection = int(input("\nEnter the number of the cluster: "))
        selected_name = cluster_names[selection - 1]
        selected_cluster = clusters_dict[selected_name]
    except (ValueError, IndexError):
        print("❌ Invalid selection.")
        Disconnect(si)
        exit(1)

    connected_hosts = get_connected_hosts_in_cluster(selected_cluster)
    #flush_esxi_dns_cache(connected_hosts)

    # Display sub-menu
    print("\n📋 Sub-Menu:")
    print("1. Run command on all hosts")
    print("2. Run command on a specific host")
    print("0. Back to the Main Menu")
    try:
        sub_option = int(input("Choose an option: "))
    except ValueError:
        print("❌ Invalid input.")
        return

    if sub_option == 1:
        flush_esxi_dns_cache(connected_hosts)
        return

    elif sub_option == 0:
        main_menu()

    elif sub_option == 2:
        print("\n🖥️  Available Hosts:")

        for idx, host in enumerate(connected_hosts, start=1):
            print(f"{idx}. {host.name}")

        try:
            host_selection = int(input("Select a host number: "))
            selected_host = connected_hosts[host_selection - 1]
            flush_esxi_dns_cache([selected_host])
            return

        except (ValueError, IndexError):
            print("❌ Invalid host selection.")
            return

    else:
        print("❌ Invalid option.")


def run_esxi_command(hosts):
    esxi_username = input("👤 ESXi Username: ")
    esxi_password = getpass.getpass("🔐 ESXi Password: ")
    esxi_command = input("⚙️  ESXi command: ")
    print()

    if not hosts:
        print("⚠️  No ESXi hosts found in the selected cluster.")
        return

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
            print(f"❌ Failed to connect to {ip}")
    print()


def run_esxi_cmd():
    cluster_names, clusters_dict = get_clusters()
    try:
        selection = int(input("\nEnter the number of the cluster: "))
        selected_name = cluster_names[selection - 1]
        selected_cluster = clusters_dict[selected_name]
    except (ValueError, IndexError):
        print("❌ Invalid selection.")
        Disconnect(si)
        exit(1)

    connected_hosts = get_connected_hosts_in_cluster(selected_cluster)
    #run_esxi_command(connected_hosts)

    # Display sub-menu
    print("\n📋 Sub-Menu:")
    print("1. Run command on all hosts")
    print("2. Run command on a specific host")
    print("0. Back to the Main Menu")
    try:
        sub_option = int(input("Choose an option: "))
    except ValueError:
        print("❌ Invalid input.")
        return

    if sub_option == 1:
        run_esxi_command(connected_hosts)
        return

    elif sub_option == 0:
        main_menu()

    elif sub_option == 2:
        print("\n🖥️  Available Hosts:")

        for idx, host in enumerate(connected_hosts, start=1):
            print(f"{idx}. {host.name}")

        try:
            host_selection = int(input("Select a host number: "))
            selected_host = connected_hosts[host_selection - 1]
            run_esxi_command([selected_host])
            return

        except (ValueError, IndexError):
            print("❌ Invalid host selection.")
            return

    else:
        print("❌ Invalid option.")



def main_menu():
    print()
    print("="*100)
    print(" 📝 ESXi DNS Manager Menu:")
    print("="*100)
    left_column = [
        f"1. Check DNS config on ESXi hosts",
        f"2. Change DNS Servers on ESXi hosts",
        f"3. Change DNS Domain on ESXi hosts",
        f"4. Flush DNS Cache on ESXi hosts",
        f"5. Run a command on ESXi hosts"
    ]

    right_column = [
        f"6. Get all clusters in the vCenter Server",
        f"7. Get all ESXi hosts in a Cluster",
        f"8. TBD",
        f"9. TBD",
        f"0. Exit"
    ]

    for left, right in zip(left_column, right_column):
        print(f"{left:<45} {right}")

    while True:
        print("-"*100)
        choice = input('Enter your choice or "m" to show the Main Menu or "q" to exit: ').strip().lower()
        
        if choice == "m":
            clear_screen()
            main_menu()
        elif choice == "q":
            print("👋 Exiting.")
            exit(0)
        elif choice == "1": show_dns_config_for_cluster()
        elif choice == "2": change_dns_server()
        elif choice == "3": change_dns_domain()
        elif choice == "4": flush_esxi_dns()
        elif choice == "5": run_esxi_cmd()
        elif choice == "6": cluster_names, clusters_dict = get_clusters()
        elif choice == "7":
            cluster_names, clusters_dict = get_clusters() 
            get_hosts_specific_cluster(cluster_names, clusters_dict)
        elif choice == "0":
            print("👋 Exiting.")
            break
        else:
            print("❌ Invalid choice. Try again.")

if __name__ == "__main__":
    main_menu()


# Disconnect from vCenter
Disconnect(si)
