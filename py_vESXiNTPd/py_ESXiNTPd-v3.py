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
    print("🔧 ESXi NTPD Manager".center(100))
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



def get_ntpd_service(host):
    try:
        for service in host.configManager.serviceSystem.serviceInfo.service:
            if service.key == 'ntpd':
                return service
    except Exception as e:
        print(f"[{host.name}] Error: {e}")
    return None


def check_ntpd_running(hosts):
    if not hosts:
        print("⚠️  No ESXi hosts found in the selected cluster.")
        return

    # Calculate the max length of hostnames for alignment
    max_len = max(len(host.name) for host in hosts)

    for host in hosts:
        ip = host.name
        ntpd = get_ntpd_service(host)
        padded_name = f"[{host.name}]".ljust(max_len + 2)  # +2 for the brackets

        if ntpd and ntpd.running:
            print(f"{padded_name} ✅ NTPD is running.")
        elif ntpd:
            print(f"{padded_name} ⚠️  NTPD is not running.")
        else:
            print(f"{padded_name} ❌ NTPD service not found.")


def check_ntpd():
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
    check_ntpd_running(connected_hosts)


def enable_ntpd(host):
    ntpd = get_ntpd_service(host)
    if ntpd and not ntpd.running:
        print(f"[{host.name}] 🔄 Starting NTPD...")
        host.configManager.serviceSystem.StartService(id='ntpd')
        print(f"[{host.name}] ✅ NTPD started.")
    elif ntpd:
        print(f"[{host.name}] ⚠️  NTPD already running.")
    else:
        print(f"[{host.name}] ❌ NTPD service not found.")
    print()

def disable_ntpd(host):
    ntpd = get_ntpd_service(host)
    if ntpd and ntpd.running:
        print(f"[{host.name}] 🔄 Stopping NTPD...")
        host.configManager.serviceSystem.StopService(id='ntpd')
        print(f"[{host.name}] ✅ NTPD stopped.")
    elif ntpd:
        print(f"[{host.name}] ⚠️  NTPD already stopped.")
    else:
        print(f"[{host.name}] ❌ NTPD service not found.")
    print()


def start_ntp_daemon(hosts):
    if not hosts:
        print("⚠️  No ESXi hosts found in the selected cluster.")
        return

    for host in hosts:
        ip = host.name
        max_len = max(len(host.name) for host in hosts)
        ntpd = get_ntpd_service(host)
        padded_name = f"[{host.name}]".ljust(max_len + 2)  # +2 for the brackets
        if ntpd and ntpd.running:
            print(f"{padded_name} ✅ NTPD is running.")
        elif ntpd:
            print(f"{padded_name} ⚠️  NTPD is not running.")
            enable_ntpd(host)
        else:
            print(f"{padded_name} ❌ NTPD service not found.")

def start_ntpd():
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
    start_ntp_daemon(connected_hosts)


def stop_ntp_daemon(hosts):
    if not hosts:
        print("⚠️  No ESXi hosts found in the selected cluster.")
        return

    for host in hosts:
        ip = host.name
        max_len = max(len(host.name) for host in hosts)
        ntpd = get_ntpd_service(host)
        padded_name = f"[{host.name}]".ljust(max_len + 2)  # +2 for the brackets
        if ntpd and ntpd.running:
            print(f"{padded_name} ✅ NTPD is running.")
            disable_ntpd(host)
        elif ntpd:
            print(f"{padded_name} ⚠️  NTPD is not running.")
        else:
            print(f"{padded_name} ❌ NTPD service not found.")


def stop_ntpd():
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
    stop_ntp_daemon(connected_hosts)


def get_ntp_daemon_config(hosts):
    if not hosts:
        print("⚠️  No ESXi hosts found in the selected cluster.")
        return
    
    for host in hosts:
        ip = host.name
        try:
            dt_system = host.configManager.dateTimeSystem
            raw_config = dt_system.dateTimeInfo.ntpConfig.configFile
            print("-" * 80)
            print(f"✅ {ip} 📝 NTP Config File Content:")
            print(raw_config)
            print("-" * 80)
        except Exception as e:
            print(f"{ip} ❌ Error retrieving NTP config file: {e}")
    return None


def get_ntpd_config():
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
    get_ntp_daemon_config(connected_hosts)



def update_ntp_daemon_config(hosts):
    config_file_path = "/root/scripts/py_vESXiNTPd/ntp_config.txt"
    try:
        with open(config_file_path, "r") as f:
            new_config_file = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"❌ Failed to read config file: {e}")
        return

    if not hosts:
        print("⚠️  No ESXi hosts found in the selected cluster.")
        return

    for host in hosts:
        ip = host.name
        try:
            dt_system = host.configManager.dateTimeSystem

            new_cfg = vim.host.NtpConfig()
            new_cfg.configFile = new_config_file

            new_dt_cfg = vim.host.DateTimeConfig()
            new_dt_cfg.ntpConfig = new_cfg

            # Apply the new configuration
            dt_system.UpdateDateTimeConfig(config=new_dt_cfg)

            print(f"[{ip}] ✅ NTP config updated successfully.🔄 Restarting the NTPD service.")
            host.configManager.serviceSystem.RestartService(id='ntpd')
        except Exception as e:
            print(f"[{ip}] ❌ Error updating NTP config: {e}")


def update_ntpd_config():
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
    update_ntp_daemon_config(connected_hosts)



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
    return stdout.read().decode().strip()


def run_esxi_cmd(hosts):
    esxi_username = input("👤 ESXi Username: ")
    esxi_password = getpass.getpass("🔐 ESXi Password: ")
    esxi_command = input("⚙️  ESXi command: ")

    if not hosts:
        print("⚠️  No ESXi hosts found in the selected cluster.")
        return

    for host in hosts:
        ip = host.name
        host.configManager.serviceSystem.RestartService(id='TSM-SSH')
        ssh = connect_ssh(ip, esxi_username, esxi_password)
        print("-"*60)
        print(f"🔄 Executing the command on {ip}")
        if ssh:
            cmd = f"{esxi_command}"
            output = run_command(ssh, cmd)
            print(f" {output} \n")
            ssh.close()
        else:
            print(f"Failed to connect to {ip}")
    print()


def run_esxi_command():
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

    if not connected_hosts:
        print("⚠️ No connected hosts found in the selected cluster.")
        return

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
        run_esxi_cmd(connected_hosts)
        exit(0)

    elif sub_option == 0:
        main_menu()        

    elif sub_option == 2:
        print("\n🖥️  Available Hosts:")

        for idx, host in enumerate(connected_hosts, start=1):
            print(f"{idx}. {host.name}")

        try:
            host_selection = int(input("Select a host number: "))
            selected_host = connected_hosts[host_selection - 1]
            run_esxi_cmd([selected_host])
            exit(0)

        except (ValueError, IndexError):
            print("❌ Invalid host selection.")
            return

    else:
        print("❌ Invalid option.")




def get_vc_ntp_config():
    vc_username = "root"
    user_input = input(f"👤 vCenter Username (default: {vc_username}): ")
    if user_input:
        vc_username = user_input
    vc_password = getpass.getpass("🔐 Password: ")
    vc_command = "cat /etc/ntp.conf"
    ip = vcenter
    ssh = connect_ssh(ip, vc_username, vc_password)    
    if ssh:
        cmd = f"{vc_command}"
        output = run_command(ssh, cmd)
        print()
        print("-"*60)
        print(f"📝 vCenter Server /etc/ntp.conf content is:")
        print("-"*60)
        print(f"{output} \n")
        ssh.close()
    else:
        print(f"❌ Failed to connect to {ip}")


def run_vc_cmd():
    vc_username = "root"
    user_input = input(f"👤 vCenter Username (default: {vc_username}): ")
    if user_input:
        vc_username = user_input
    vc_password = getpass.getpass("🔐 Password: ")
    vc_command = input(f"⚙️  Command: ")
    ip = vcenter
    ssh = connect_ssh(ip, vc_username, vc_password)
    if ssh:
        cmd = f"{vc_command}"
        output = run_command(ssh, cmd)
        print()
        print("-"*60)
        print(f"🔄 Executing the command on the vCenter Server: ")
        print("-"*60)
        print(f"{output} \n")
        ssh.close
    else:
         print(f"❌ Failed to connect to {ip}")




def main_menu():
    print()
    print("="*100)
    print("ESXi NTPD Manager Menu:")
    print("="*100)
    
    left_column = [
        f"1. Check if ntpd is running on ESXi hosts",
        f"2. Start NTPD on all ESXi hosts",
        f"3. Stop NTPD on all ESXi hosts",
        f"4. Get NTPD config on all ESXi hosts",
        f"5. Update NTPD config on all ESXi hosts"
    ]

    right_column = [
        f"6. Run a command on ESXi hosts",
        f"7. Get vCenter NTP Config",
        f"8. Run a command on the vCenter Server",
        f"9. TBD",
        f"0. Exit"
    ]

    for left, right in zip(left_column, right_column):
        print(f"{left:<45} {right}")
    

    while True:
        print("-"*100)
        choice = input('Enter your choice or "m" to show the Main Menu: ').strip().lower()

        if choice == "m":
            clear_screen()
            main_menu()
        elif choice == "1": check_ntpd()
        elif choice == "2": start_ntpd()
        elif choice == "3": stop_ntpd()
        elif choice == "4": get_ntpd_config()
        elif choice == "5": update_ntpd_config()
        elif choice == "6": run_esxi_command()
        elif choice == "7": get_vc_ntp_config()
        elif choice == "8": run_vc_cmd()
        elif choice == "0":
            print("👋 Exiting.")
            #break
            exit(0)
        else:
            print("❌ Invalid choice. Try again.")

if __name__ == "__main__":
    main_menu()
