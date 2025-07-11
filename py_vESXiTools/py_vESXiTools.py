#!/usr/bin/env python3

import paramiko
import getpass
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

def load_hosts(file_path):
    try:
        with open(file_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ Could not find file: {file_path}")
        exit(1)

# 🔧 Configuration
hosts_file = "esxi_hosts.txt"
hosts = load_hosts(hosts_file)
username = "root"
local_file_path = "VMware-Tools-12.5.2-core-offline-depot-ESXi-all-24697584.zip"
temp_dir_name = "vmware-tools-temp"
file_name = os.path.basename(local_file_path)

def get_password():
    return getpass.getpass("🔐 Enter ESXi root password: ")

def connect_ssh(host, username, password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=username, password=password, timeout=10)
        return ssh
    except Exception as e:
        print(f"❌ Connection to {host} failed: {e}")
        return None

def run_command(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(command)
    return stdout.read().decode().strip()

def check_vmware_tools_version(ssh):
    cmd = "esxcli software vib list | grep -i tool | awk '{print$2}'"
    return run_command(ssh, cmd)

def get_vmware_tools_versions(hosts, username, password):
    print("\n📋 Checking VMware Tools version on all ESXi hosts...\n")
    results = []

    for host in hosts:
        print(f"🔗 Connecting to {host}...")
        ssh = connect_ssh(host, username, password)
        if ssh:
            output = check_vmware_tools_version(ssh)
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
    transport.connect(username=username, password=password)
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

#def upgrade_vmware_tools(hosts, username, password):
#    print("\n🚀 Starting VMware Tools upgrade on all ESXi hosts...\n")
#    for host in hosts:
#        print(f"\n🔗 Connecting to {host}...")
#        ssh = connect_ssh(host, username, password)
#        if ssh:
#            osdata_path = get_osdata_path(ssh)
#            if not osdata_path:
#                print("❌ Could not find OSDATA partition.")
#                ssh.close()
#                continue
#
#            remote_path = copy_file_to_esxi(host, username, password, osdata_path)
#            print("⚙️  Installing VMware Tools VIB...")
#            result = install_vmware_tools(ssh, remote_path)
#            print(result)
#            ssh.close()
#        else:
#            print(f"❌ Failed to connect to {host}")

def upgrade_vmware_tools(hosts, username, password):
    print("\n🚀 Starting VMware Tools upgrade on all ESXi hosts...\n")
    for host in hosts:
        print(f"\n🔗 Connecting to {host}...")
        ssh = connect_ssh(host, username, password)
        if ssh:
            osdata_path = get_osdata_path(ssh)
            if not osdata_path:
                print("❌ Could not find OSDATA partition.")
                ssh.close()
                continue

            # 🔄 Upload and Install
            remote_path = copy_file_to_esxi(host, username, password, osdata_path)
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
    show_banner()
    password = get_password()

    while True:
        print("\n===== VMware Tools ESXi Manager =====")
        print("1. Get VMware Tools version on all ESXi hosts")
        print("2. Upgrade VMware Tools version on all ESXi hosts")
        print("0. Exit")
        choice = input("Choose an option: ")

        if choice == "1":
            get_vmware_tools_versions(hosts, username, password)
        elif choice == "2":
            upgrade_vmware_tools(hosts, username, password)
        elif choice == "0":
            print("👋 Exiting.")
            break
        else:
            print("❗ Invalid option. Try again.")

if __name__ == "__main__":
    main()

