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
    print("🔧 VMware Tools ESXi Upgrader".center(60))
    print("=" * 60)

show_banner()

# Local file to upload
local_file_path = "VMware-Tools-12.5.2-core-offline-depot-ESXi-all-24697584.zip"
file_name = os.path.basename(local_file_path)
temp_dir_name = "vmware-tools-temp"

# Get credentials
vcenter_address = input("vCenter address: ")
vcenter_username = input("vCenter Username: ")
vcenter_password = getpass.getpass("vCenter Password: ")
esxi_username = input("ESXi Username: ")
esxi_password = getpass.getpass("ESXi Password: ")
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

def get_ssh_service(host):
    try:
        for service in host.configManager.serviceSystem.serviceInfo.service:
            if service.key == 'TSM-SSH':
                return service
    except Exception as e:
        print(f"[{host.name}] Error: {e}")
    return None


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
		
		
def stop_ssh_all():
    hosts = get_hosts()
    for host in hosts:
        ip = host.name
        try:
            print(f"🔄 Stopping SSH on {ip}...")
            disable_ssh(host)
            print()

        except Exception as e:
            print(f"❌ Stopping SSH error on {i}: {e}")



def list_esxi_hosts():
    hosts = get_hosts()
    table = PrettyTable(["ESXi Host Name"])
    for host in hosts:
        table.add_row([host.name])
    print(table)


def get_vmware_tools_version():
    hosts = get_hosts()
    table = PrettyTable(["ESXi Host", "VMware Tools VIB Version"])
    for host in hosts:
        ip = host.name
        try:
            print(f"🔄 Connecting to {ip} via SSH...")
            # Ensure SSH is enabled using vCenter API
            enable_ssh(host)
            print()
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=esxi_username, password=esxi_password, timeout=10)

            stdin, stdout, stderr = ssh.exec_command("esxcli software vib list | grep -i tools | awk '{print $2}'")
            version = stdout.read().decode().strip()
            if not version:
                version = "Not Found"
            table.add_row([ip, version])
            ssh.close()
        except Exception as e:
            table.add_row([ip, f"Error: {str(e)}"])
    print(table)



def run_command(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(command)
    return stdout.read().decode().strip()


def install_vmware_tools(ssh, remote_file_path):
    cmd = f"esxcli software vib install --depot=file:{remote_file_path}"
    return run_command(ssh, cmd)

def cleanup_temp_files(ssh, osdata_path):
    cleanup_cmd = f"rm -rf {osdata_path}"
    run_command(ssh, cleanup_cmd)


def upgrade_vmware_tools():
    hosts = get_hosts()
    for host in hosts:
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



def main_menu():
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
            stop_ssh_all()
        elif choice == "0":
            print("👋 Exiting.")
            break
        else:
            print("❌ Invalid choice. Try again.")

if __name__ == "__main__":
    main_menu()

