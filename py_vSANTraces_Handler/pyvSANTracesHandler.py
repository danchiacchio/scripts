from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import getpass
import os
import paramiko
import sys

# Screen clear
os.system('cls' if os.name == 'nt' else 'clear')

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

# Banner
def show_banner():
    print("=" * 60)
    print("🔧 ESXi vSAN Traces Handler".center(60))
    print("=" * 60)
show_banner()

# Get credentials
vcenter = input("🌐 vCenter IP/FQDN: ")
user = input("👤 vCenter SSO Username: ")
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
    print(f"\n✅ Connected hosts in cluster '{selected_cluster.name}':")
    for host in connected_hosts:
        print(f"{host.name}")


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


def get_vsan_traces_details(hosts):
    esxi_username = input("👤 ESXi Username: ")
    esxi_password = getpass.getpass("🔐 ESXi Password: ")
    esxi_command = "esxcli vsan trace get"
    print()

    for host in hosts:
        ip = host.name
        host.configManager.serviceSystem.RestartService(id='TSM-SSH')
        ssh = connect_ssh(ip, esxi_username, esxi_password)
        print("-"*60)
        print(f"🔄 Getting vSAN Traces details on {ip}")
        if ssh:
            cmd = f"{esxi_command}"
            output = run_command(ssh, cmd)
            print(f" {output} \n")
            ssh.close()
        else:
            print(f"❌ Failed to connect to {ip}")
    print()


def get_vsan_traces():
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
    get_vsan_traces_details(connected_hosts)



def get_vsan_traces_usage_details(hosts):
    esxi_username = input("👤 ESXi Username: ")
    esxi_password = getpass.getpass("🔐 ESXi Password: ")
    esxi_command = 'vdf -h | grep -i -E "Ramdisk|vsantraces"'
    print()

    for host in hosts:
        ip = host.name
        host.configManager.serviceSystem.RestartService(id='TSM-SSH')
        ssh = connect_ssh(ip, esxi_username, esxi_password)
        print("-"*80)
        print(f"🔄 Getting vSAN Traces usage on {ip}")
        if ssh:
            cmd = f"{esxi_command}"
            output = run_command(ssh, cmd)
            print(f" {output} \n")
            ssh.close()
        else:
            print(f"❌ Failed to connect to {ip}")
    print()


def get_vsan_traces_usage():
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
    get_vsan_traces_usage_details(connected_hosts)



def change_vsan_traces_dir(hosts):
    esxi_username = input("👤 ESXi Username: ")
    esxi_password = getpass.getpass("🔐 ESXi Password: ")
    new_dir_name = "new_vsantraces"
    os_partial_data_path = input("📝 Type part of the volume path: ")
    print()

    for host in hosts:
        ip = host.name
        
        print("=" * 110)
        print(f"Connection to ESXi host: {ip}")
        try:
            # Enable SSH first via vCenter API
            host.configManager.serviceSystem.RestartService(id='TSM-SSH')

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=esxi_username, password=esxi_password)

            # Identify osdata volume
            stdin, stdout, stderr = ssh.exec_command(f"ls /vmfs/volumes | grep -i {os_partial_data_path}")
            osdata = stdout.read().decode().strip().splitlines()
            if not osdata:
                print(f"  ❌ {os_partial_data_path} volume not found on {ip}")
                ssh.close()
                continue

            osdata_path = f"/vmfs/volumes/{osdata[0]}/{new_dir_name}"
            print(f"🔄 Creating the new dir for vSAN Traces: {new_dir_name}")
            ssh.exec_command(f"mkdir -p {osdata_path}")
            print(f"✅ New dir created successfully: {osdata_path}")

            print(f"🔄 Changing the vSAN Traces dir to: {osdata_path}")
            ssh.exec_command(f"esxcli vsan trace set -p {osdata_path}")
            print(f"✅ Done!")

            ssh.close()
        except Exception as e:
            print(f"  ❌ Error on {ip}: {e}")



def change_vsan_traces():
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
    change_vsan_traces_dir(connected_hosts)



def get_vsan_traces_files_details(hosts):
    esxi_username = input("👤 ESXi Username: ")
    esxi_password = getpass.getpass("🔐 ESXi Password: ")
    print()

    for host in hosts:
        ip = host.name
        print("-" * 60)
        print(f"🔄 Getting the most recent vSAN Traces files on {ip}")

        # Restart SSH service
        host.configManager.serviceSystem.RestartService(id='TSM-SSH')

        ssh = connect_ssh(ip, esxi_username, esxi_password)

        if ssh:
            # STEP 1: Get the vSAN traces directory from the host
            get_dir_cmd = "esxcli vsan trace get | grep -i dir | awk -F':' '{gsub(/^ +/, \"\", $2); print $2}'"
            get_esxi_date = "date"
            vsan_dir = run_command(ssh, get_dir_cmd).strip()
            esxi_date = run_command(ssh, get_esxi_date).strip()

            if vsan_dir:
                # STEP 2: List files in that directory
                print(f"⚠️  The following vSAN Traces files are on {vsan_dir}")
                print(f"🕒 The date info on ESXi is: {esxi_date}")
                list_cmd = f"ls -lht {vsan_dir} | head"
                output = run_command(ssh, list_cmd)
                print(f"{output}\n")
            else:
                print("❌ Could not retrieve vSAN traces directory.")

            ssh.close()
        else:
            print(f"❌ Failed to connect to {ip}")
    print()



def get_vsan_traces_files():
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
    get_vsan_traces_files_details(connected_hosts)



def get_all_mount_point_usage_details(hosts):
    esxi_username = input("👤 ESXi Username: ")
    esxi_password = getpass.getpass("🔐 ESXi Password: ")
    esxi_command = "df -h"
    print()

    for host in hosts:
        ip = host.name
        host.configManager.serviceSystem.RestartService(id='TSM-SSH')
        ssh = connect_ssh(ip, esxi_username, esxi_password)
        print("-"*80)
        print(f"🔄 Getting all Mount Point details on {ip}")
        if ssh:
            cmd = f"{esxi_command}"
            output = run_command(ssh, cmd)
            print(f" {output} \n")
            ssh.close()
        else:
            print(f"❌ Failed to connect to {ip}")
    print()


def get_all_mount_points():
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
    get_all_mount_point_usage_details(connected_hosts)



def main_menu():
    while True:
        print()
        print("-"*60)
        print("📝 ESXi vSAN Traces Handler")
        print("-"*60)
        print("1. Get vSAN Traces Details on all ESXi hosts")
        print("2. Get vSAN Traces Usage on all ESXi hosts")
        print("3. Change vSAN Traces Dir")
        print("4. List files on the vSAN Traces Dir")
        print("5. Get Mount Point usage on all ESXi hosts")
        print("0. Exit")
        choice = input("Enter your choice: ")

        if choice == "1":
            get_vsan_traces()
        elif choice == "2":
            get_vsan_traces_usage()
        elif choice == "3":
            change_vsan_traces()
        elif choice == "4":
            get_vsan_traces_files() 
        elif choice == "5":
            get_all_mount_points()
        elif choice == "0":
            print("👋 Exiting.")
            break
        else:
            print("❌ Invalid choice. Try again.")

if __name__ == "__main__":
    main_menu()
