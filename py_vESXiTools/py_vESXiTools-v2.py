from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import atexit
import getpass
import paramiko
import os
from prettytable import PrettyTable


# Cross-platform screen clear
os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    print("=" * 60)
    print("🔧 VMware Tools ESXi Manager".center(60))
    print("=" * 60)
    print("⚠️  All ESXi hosts must have the SAME root password.")
    print("ℹ️  This script uses SSH to connect to each host.\n")
show_banner()

# Disable SSL certificate verification
context = ssl._create_unverified_context()

# VMware Tools file and temp dir
local_file_path = "VMware-Tools-12.5.2-core-offline-depot-ESXi-all-24697584.zip"
temp_dir_name = "vmware-tools-temp"
file_name = os.path.basename(local_file_path)

# vCenter and ESXi credentials handler
vcenter_address = input("vCenter address: ")
vcenter_username = input("vCenter Username: ")
vcenter_password = getpass.getpass("vCenter Password: ")
esxi_username = input("ESXi Username: ")
esxi_password = getpass.getpass("ESXi Password: ")
print()

# Connect to vCenter
si = SmartConnect(host=vcenter_address, user=vcenter_username, pwd=vcenter_password, sslContext=context)
atexit.register(Disconnect, si)

# Traverse inventory to find all ESXi hosts
content = si.RetrieveContent()
container = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
hosts = container.view
container.Destroy()

# Save hostnames to file
with open("esxi_hosts.txt", "w") as f:
    for host in hosts:
        f.write(host.name + "\n")

print(f"✅ Saved {len(hosts)} ESXi hosts to esxi_hosts.txt")

with open("esxi_hosts.txt", "r") as f:
    hostnames = [line.strip() for line in f if line.strip()]


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



def get_vmware_tools_versions(host, esxi_username, esxi_password):

    print("\n Executing a command on all ESXi hosts....\n")
    results = []

    for host in hostnames:
        print(f"🔄 Connecting to {host} via SSH...")    
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=esxi_username, password=esxi_password, timeout=10)
        
        if ssh:
            stdin, stdout, stderr = ssh.exec_command("esxcli software vib list | grep -i tools | awk '{print$2}'")
            output = stdout.read().decode().strip()
            error_output = stderr.read().decode().strip()            
            version = output.splitlines()[0] if output else "Not found"
            results.append((host, version))
            ssh.close()            

        else:
            results.append((host, "Connection failed"))


# Print results in a table
    table = PrettyTable()
    table.field_names = ["ESXi Host", "VMware Tools Version"]
    for host, version in results:
        table.add_row([host, version])
    print("\n📊 VMware Tools Versions Summary:\n")
    print(table)



def get_osdata_path(ssh):
    cmd = "ls -d /vmfs/volumes/* | grep OSDATA"
    return run_command(ssh, cmd)


def copy_file_to_esxi(host, username, password, osdata_path):
    transport = paramiko.Transport((host, 22))
    transport.connect(username=esxi_username, password=esxi_password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    remote_path = f"{osdata_path}/{temp_dir_name}/{file_name}"
    try:
        sftp.mkdir(f"{osdata_path}/{temp_dir_name}")
    except IOError:
        pass  # Directory might already exist
    print(f"📁 Copying file to {host}:{remote_path}...")
    sftp.put(local_file_path, remote_path)
    sftp.close()
    transport.close()
    return remote_path


def install_vmware_tools(ssh, remote_path):
    cmd = f"esxcli software vib install --depot=file:{remote_path}"
    return run_command(ssh, cmd)


def upgrade_vmware_tools(hosts, esxi_username, esxi_password):
    print("\n🚀 Starting VMware Tools upgrade on all ESXi hosts...\n")
    for host in hostnames:
        print(f"\n🔗 Connecting to {host}...")
        ssh = connect_ssh(host, esxi_username, esxi_password)
        if ssh:
            osdata_path = get_osdata_path(ssh)
            if not osdata_path:
                print("❌ Could not find OSDATA partition.")
                ssh.close()
                continue

            # 🔄 Upload and Install
            remote_path = copy_file_to_esxi(host, esxi_username, esxi_password, osdata_path)
            print("⚙️  Installing VMware Tools VIB...")
            result = install_vmware_tools(ssh, remote_path)
            print(result)

            # 🧹 Clean up temp files and directory
            print(f"🧹 Cleaning up temporary files on {host}...")
            cleanup_temp_files(ssh, osdata_path)

            ssh.close()
        else:
            print(f"❌ Failed to connect to {host}")


def cleanup_temp_files(ssh, osdata_path):
    cleanup_cmd = f"rm -rf {osdata_path}/{temp_dir_name}"
    run_command(ssh, cleanup_cmd)




def main():

    while True:
        print("\n===== VMware Tools ESXi Manager =====")
        print("1. Get VMware Tools version on all ESXi hosts")
        print("2. Upgrade VMware Tools version on all ESXi hosts")
        print("0. Exit")
        choice = input("Choose an option: ")

        if choice == "1":
            get_vmware_tools_versions(host, esxi_username, esxi_password)
        elif choice == "2":
            upgrade_vmware_tools(hosts, esxi_username, esxi_password)
        elif choice == "0":
            print("👋 Exiting.")
            break
        else:
            print("❗ Invalid option. Try again.")

if __name__ == "__main__":
    main()
