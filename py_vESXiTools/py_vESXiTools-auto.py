#!/usr/bin/env python3

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

# Script banner
print("=" * 100)
print("🔧 VMware Tools ESXi Upgrader".center(100))
print("=" * 100)

# Function to connect to vCenter
def connect_vcenter():
    # Ask user for vCenter connection info
    vcenter = input("🌐 vCenter IP or FQDN: ").strip()
    user = "administrator@vsphere.local"
    user_input = input(f"👤 vCenter SSO Username (default: {user}): ").strip()
    if user_input:
        user = user_input
    pwd = getpass.getpass("🔐 Password: ")

    context = ssl._create_unverified_context()
    try:
        si = SmartConnect(
            host=vcenter,
            user=user,
            pwd=pwd,
            port=443,
            sslContext=context
        )
        print(f"✅ Connected to vCenter {vcenter} successfully!")
        return si, vcenter
    except vim.fault.InvalidLogin:
        print("❌ Invalid username or password.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to connect to vCenter: {e}")
        sys.exit(1)

# Call the function
si, vcenter = connect_vcenter()

# Get ESXi authentication
def esxi_credentials():
    esxi_username = input("ESXi Username: ")
    esxi_password = getpass.getpass("ESXi Password: ")
    return esxi_username, esxi_password

# Function to get all vSphere Clusters
def get_clusters(si):
    content = si.RetrieveContent()
    container = content.rootFolder  # Start from the root folder
    viewType = [vim.ClusterComputeResource]
    recursive = True

    container_view = content.viewManager.CreateContainerView(
        container=container,
        type=viewType,
        recursive=recursive
    )
    clusters = container_view.view
    container_view.Destroy()

    return clusters

# Function to get all connected hosts
def get_hosts():
    content = si.RetrieveContent()
    container = content.rootFolder
    viewType = [vim.HostSystem]
    recursive = True
    
    container_view = content.viewManager.CreateContainerView(
        container=container,
        type=viewType,
        recursive=recursive
    ) 

    hosts = [host for host in container_view.view if host.runtime.connectionState == "connected"]
    container.Destroy()
    return hosts

# Get ESXi hosts in cluster
def get_hosts_in_cluster(si):
    clusters = get_clusters(si)  # Reuse your get_clusters() function

    if not clusters:
        print("No clusters found.")
        return []

    print("\nAvailable Clusters:")
    for i, cluster in enumerate(clusters, start=1):
        print(f"{i}. {cluster.name}")

    while True:
        try:
            choice = int(input("\nEnter the number of the cluster to list its ESXi hosts: "))
            if 1 <= choice <= len(clusters):
                selected_cluster = clusters[choice - 1]
                return selected_cluster.host
                break
            else:
                print("Invalid choice. Try again!")
        except Exception as e:
            print(f"Error {e}")


# Function to get the SSH service
def get_ssh_service(host):
    try:
        for service in host.configManager.serviceSystem.serviceInfo.service:
            if service.key == 'TSM-SSH':
                return service
    except Exception as e:
        print(f"[{host.name}] Error: {e}")
    return None

# Function to enable the SSH service
def enable_ssh(host):
    ssh = get_ssh_service(host)
    if ssh and not ssh.running:
        print(f"[{host.name}] Starting SSH...")
        host.configManager.serviceSystem.StartService(id='TSM-SSH')
        print(f"[{host.name}] ✅ SSH started.")
    elif ssh:
        print(f"[{host.name}] SSH already running.")
    else:
        print(f"[{host.name}] ❌ SSH service not found.")

# Function to disable the SSH service
def disable_ssh(host):
    ssh = get_ssh_service(host)
    if ssh and ssh.running:
        print(f"[{host.name}] Stopping SSH...")
        host.configManager.serviceSystem.StopService(id='TSM-SSH')
        print(f"[{host.name}] ✅ SSH stopped.")
    elif ssh:
        print(f"[{host.name}] SSH already stopped.")
    else:
        print(f"[{host.name}] ❌ SSH service not found.")

# Function to stop the SSH service on all ESXi hosts
def stop_ssh_selected():
    hosts = get_hosts_in_cluster(si)
    if not hosts:
        print("No hosts found.")
        return

    print("\nAvailable Hosts in Cluster:")
    hosts_sorted = sorted(hosts, key=lambda host: host.name.lower())
    for idx, host in enumerate(hosts, start=1):
        print(f"{idx}. {host.name}")

    selection = input("\nEnter host number (e.g., 2), range (e.g., 1-3), or 'all': ").strip().lower()

    selected_hosts = []

    if selection == "all":
        selected_hosts = hosts_sorted
    else:
        try:
            parts = selection.split(",")
            indices = set()

            for part in parts:
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    if start < 1 or end > len(hosts_sorted) or start > end:
                        print(f"❌ Invalid range: {part}")
                        return
                    indices.update(range(start - 1, end))
                else:
                    index = int(part)
                    if index < 1 or index > len(hosts_sorted):
                        print(f"❌ Invalid index: {index}")
                        return
                    indices.add(index - 1)

            selected_hosts = [hosts_sorted[i] for i in sorted(indices)]

        except Exception as e:
            print(f"❌ Invalid input format: {e}")
            return

    for i, host in enumerate(selected_hosts, start=1):
        ip = host.name
        try:
            print(f"🔄 Stopping SSH on {ip}...")
            disable_ssh(host)
            print(f"✅ SSH stopped on {ip}")
        except Exception as e:
            print(f"❌ Error stopping SSH on {ip}: {e}")


# Function to list all ESXi hosts and print them in a table format
def list_esxi_hosts():
    hosts = get_hosts_in_cluster(si)    
    
    if not hosts:
        print("No hosts found or invalid cluster selection.")
        return    

    table = PrettyTable(["ESXi Host Name", "Model", "Vendor", "ESXi Version", "ESXi Build", "Member Of", "Uptime (d hh:mm)", "Management IP"])
    for host in hosts:
        uptime_seconds = host.summary.quickStats.uptime
        uptime_days = uptime_seconds // 86400
        uptime_hours = (uptime_seconds % 86400) // 3600
        uptime_minutes = (uptime_seconds % 3600) // 60
        host_uptime = f"{uptime_days}d {uptime_hours:02}:{uptime_minutes:02}" #format as d hh:mm
        management_ip = get_management_ip(host)
        table.add_row([
            host.name,
            host.hardware.systemInfo.model,
            host.hardware.systemInfo.vendor,
            host.config.product.version,
            host.config.product.build,
            host.parent.name,
            host_uptime,
            management_ip
        ])
    print(table)


# Function to get the IP address of the Management VMKernel Interface
def get_management_ip(host):
    for netConfig in host.config.virtualNicManagerInfo.netConfig:
        if netConfig.nicType == "management":
            for vnic in netConfig.candidateVnic:
                device = vnic.device  # e.g., 'vmk0'
                # Find matching vNIC in host.config.network.vnic
                for nic in host.config.network.vnic:
                    if nic.device == device:
                        ip = nic.spec.ip.ipAddress
                        return ip
    return "N/A"


# Function to connect on each ESXi host and get the VMware Tools version
def get_vmware_tools_version():
    hosts = get_hosts_in_cluster(si)
    
    if not hosts:
        print("No hosts found.")
        return

    print("\nAvailable Hosts in Cluster:")
    hosts_sorted = sorted(hosts, key=lambda host: host.name.lower())
    for idx, host in enumerate(hosts_sorted, start=1):
        print(f"{idx}. {host.name}")

    selection = input("\nEnter host number (e.g., 2), range (e.g., 1-3), or 'all': ").strip().lower()

    selected_hosts = []

    if selection == "all":
        selected_hosts = hosts_sorted
    else:
        try:
            parts = selection.split(",")
            indices = set()

            for part in parts:
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    if start < 1 or end > len(hosts_sorted) or start > end:
                        print(f"❌ Invalid range: {part}")
                        return
                    indices.update(range(start - 1, end))
                else:
                    index = int(part)
                    if index < 1 or index > len(hosts_sorted):
                        print(f"❌ Invalid index: {index}")
                        return
                    indices.add(index - 1)

            selected_hosts = [hosts_sorted[i] for i in sorted(indices)]

        except Exception as e:
            print(f"❌ Invalid input format: {e}")
            return

    # Call the function to enter ESXi username and password
    esxi_username, esxi_password = esxi_credentials()

    table = PrettyTable(["ESXi Host", "VMware Tools VIB Version"])
    
    for i, host in enumerate(selected_hosts, start=1):
        ip = host.name
        try:
            print(f"\n🔄 Connecting to {ip} via SSH...")
            # Ensure SSH is enabled using vCenter API
            enable_ssh(host)
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=esxi_username, password=esxi_password, timeout=10)

            print("     🔄 Getting the VMware Tools version...")
            stdin, stdout, stderr = ssh.exec_command("esxcli software vib list | grep -i tools | awk '{print $2}'")
            version = stdout.read().decode().strip()
            if not version:
                version = "Not Found"
            table.add_row([ip, version])
            ssh.close()
        except Exception as e:
            table.add_row([ip, f"Error: {str(e)}"])
    print(table)

# Function to run a command through SSH session
def run_command(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(command)
    return stdout.read().decode().strip()

# Function to start the VMware Tools installation
def install_vmware_tools(ssh, remote_file_path):
    cmd = f"esxcli software vib install --depot=file:{remote_file_path}"
    return run_command(ssh, cmd)

# Function to clean the VMware Tools offline bundle after installation
def cleanup_temp_files(ssh, osdata_path):
    cleanup_cmd = f"rm -rf {osdata_path}"
    run_command(ssh, cleanup_cmd)

# Function to upgrade the VMware Tools version
def upgrade_vmware_tools():
    hosts = get_hosts_in_cluster(si)
    
    if not hosts:
        print("No hosts found.")
        return

    print("\nAvailable Hosts in Cluster:")
    hosts_sorted = sorted(hosts, key=lambda host: host.name.lower())
    for idx, host in enumerate(hosts_sorted, start=1):
        print(f"{idx}. {host.name}")

    selection = input("\nEnter host number (e.g., 2), range (e.g., 1-3), or 'all': ").strip().lower()

    selected_hosts = []

    if selection == "all":
        selected_hosts = hosts_sorted
    else:
        try:
            parts = selection.split(",")
            indices = set()

            for part in parts:
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    if start < 1 or end > len(hosts_sorted) or start > end:
                        print(f"❌ Invalid range: {part}")
                        return
                    indices.update(range(start - 1, end))
                else:
                    index = int(part)
                    if index < 1 or index > len(hosts_sorted):
                        print(f"❌ Invalid index: {index}")
                        return
                    indices.add(index - 1)

            selected_hosts = [hosts_sorted[i] for i in sorted(indices)]

        except Exception as e:
            print(f"❌ Invalid input format: {e}")
            return

    # Call the function to enter ESXi username and password
    esxi_username, esxi_password = esxi_credentials()
    
    local_file_path = input("Type the path to the VMware Tools file e.g. /tmp/VMware-Tools-12.5.2-core-offline-depot-ESXi-all-24697584.zip: ")
    file_name = os.path.basename(local_file_path)
    temp_dir_name = "vmware-tools-temp"

    for i, host in enumerate(selected_hosts, start=1):
        ip = host.name
        print("=" * 80)
        print(f"Connection to ESXi host: {ip}")
        try:
            # Enable SSH first via vCenter API
            enable_ssh(host)

            print(f"▶ Uploading to host: {ip}")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=esxi_username, password=esxi_password)

            # Identify osdata volume
            stdin, stdout, stderr = ssh.exec_command("ls /vmfs/volumes | grep -i osdata")
            osdata = stdout.read().decode().strip().splitlines()
            if not osdata:
                print(f"  ❌ OSDATA volume not found on {ip}")
                ssh.close()
                continue
            osdata_path = f"/vmfs/volumes/{osdata[0]}/{temp_dir_name}"
            ssh.exec_command(f"mkdir -p {osdata_path}")

            # Upload using SFTP and install
            sftp = ssh.open_sftp()
            remote_file_path = os.path.join(osdata_path, file_name)
            
            print(f"  ⏫ Uploading {file_name} to {remote_file_path}")
            sftp.put(local_file_path, remote_file_path)
            print(f"  ✅ Upload complete on {ip}")
            print()
            
            print(f"⚙️  Installing VMware Tools VIB...")
            result = install_vmware_tools(ssh, remote_file_path)
            print(result)
            print(f"  ✅ Installation finish on {ip}")
            print()

            # 🧹 Clean up temp files and directory
            print(f"🧹 Cleaning up temporary files on {ip}...")
            cleanup_temp_files(ssh, osdata_path)
            print(f"  ✅ Cleaning finish on {ip}")
            print()
            
            sftp.close()
            ssh.close()
        
        except Exception as e:
            print(f"  ❌ Error on {ip}: {e}")



while True:
    print("\n===== VMware Tools ESXi Manager =====")
    print("1. List all connected ESXi hosts")
    print("2. Get VMware Tools version of all connected ESXi hosts")
    print("3. Upgrade VMware Tools on all connected ESXi hosts")
    print("4. Disable SSH service on all ESXi hosts")
    print("0. Exit")
    choice = input("Enter your choice: ")

    if choice == "1":
        list_esxi_hosts()

    elif choice == "2":
        get_vmware_tools_version()

    elif choice == "3":
        upgrade_vmware_tools()

    elif choice == "4":
        stop_ssh_selected()

    elif choice == "0":
        print("👋 Exiting.")
        break

    else:
        print("❌ Invalid choice. Try again.")


# Disconnect properly
Disconnect(si)
print(f"🔌 Disconnected from vCenter {vcenter} successfully.")

