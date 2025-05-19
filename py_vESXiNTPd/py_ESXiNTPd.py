from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import atexit
import getpass
import paramiko
import os
from prettytable import PrettyTable

# Screen clear
os.system('cls' if os.name == 'nt' else 'clear')

# Banner
def show_banner():
    print("=" * 60)
    print("🔧 ESXi NTPD Manager".center(60))
    print("=" * 60)

show_banner()

# Get credentials
vcenter_address = input("vCenter address: ")
vcenter_username = input("vCenter Username: ")
vcenter_password = getpass.getpass("vCenter Password: ")
#esxi_username = input("ESXi Username: ")
#esxi_password = getpass.getpass("ESXi Password: ")
print()

# vCenter connection
context = ssl._create_unverified_context()
si = SmartConnect(host=vcenter_address, user=vcenter_username, pwd=vcenter_password, sslContext=context)
atexit.register(Disconnect, si)
content = si.RetrieveContent()

def get_hosts():
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
    hosts = [host for host in container.view if host.runtime.connectionState == "connected"]
    container.Destroy()
    return hosts


def get_ntpd_service(host):
    try:
        for service in host.configManager.serviceSystem.serviceInfo.service:
            if service.key == 'ntpd':
                return service
    except Exception as e:
        print(f"[{host.name}] Error: {e}")
    return None


def check_ntpd_running():
    hosts = get_hosts()

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

def start_ntpd():
    hosts = get_hosts()
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
			
def stop_ntpd():
    hosts = get_hosts()
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



def get_ntpd_config():
    hosts = get_hosts()

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



def update_ntpd_config():
    hosts = get_hosts()

    config_file_path = "/root/scripts/py_vESXiNTPd/ntp_config.txt"
    try:
        with open(config_file_path, "r") as f:
            new_config_file = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"❌ Failed to read config file: {e}")
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


def run_esxi_command():
    esxi_username = input("ESXi Username: ")
    esxi_password = getpass.getpass("ESXi Password: ")
    esxi_command = input("ESXi command: ")
    hosts = get_hosts()
    for host in hosts:
        ip = host.name
        host.configManager.serviceSystem.RestartService(id='TSM-SSH')
        ssh = connect_ssh(ip, esxi_username, esxi_password)
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
        print("\n===== ESXi NTPD Manager =====")
        print("1. Check if ntpd is running on all ESXi hosts")
        print("2. Start NTPD on all ESXi hosts")
        print("3. Stop NTPD on all ESXi hosts")
        print("4. Get NTPD config on all ESXi hosts")
        print("5. Update NTPD config on all ESXi hosts")
        print("6. Run a command on all ESXi hosts")
        print("0. Exit")
        choice = input("Enter your choice: ")

        if choice == "1":
            check_ntpd_running()
        elif choice == "2":
            start_ntpd()
        elif choice == "3":
            stop_ntpd()
        elif choice == "4":
            get_ntpd_config()
        elif choice == "5":
            update_ntpd_config()
        elif choice == "6":
            run_esxi_command()
        elif choice == "7":
            print()
        elif choice == "0":
            print("👋 Exiting.")
            break
        else:
            print("❌ Invalid choice. Try again.")

if __name__ == "__main__":
    main_menu()
