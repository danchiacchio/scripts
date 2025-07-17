#!/usr/bin/env python3

# Import Modules
import paramiko
import time
import os
import getpass
import socket
import ssl
import atexit
import argparse
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
from pyVim.task import WaitForTask

# Parse command line arguments
parser = argparse.ArgumentParser(description="ESXi patch script with vCenter Maintenance Mode")
parser.add_argument('hosts', nargs='+', help='One or more ESXi hostnames or IPs to patch')
parser.add_argument('--patch-file', default='VMware-ESXi-8.0U3f-24784735-depot.zip',
                    help='Path to the ESXi patch ZIP file')
parser.add_argument('--patch-profile', default='ESXi-8.0U3f-24784735-standard',
                    help='Name of the ESXi patch profile inside the depot')
args = parser.parse_args()

esxi_hosts = args.hosts
patch_file = args.patch_file
patch_profile = args.patch_profile


# Clean the screen
os.system('cls' if os.name == 'nt' else 'clear')

# Script Header
print("-"*100)
print("ESXi Host Patcher with vCenter-Aware Maintenance Mode".center(100))
print("-"*100)

# Input credentials
vc_host = input("🌐 vCenter Host (FQDN or IP): ")
vc_user = "administrator@vsphere.local"
vc_user_input = input(f"👤 vCenter Username (default {vc_user}): ")
if vc_user_input:
    vc_user = vc_user_input
vc_password = getpass.getpass("🔐 vCenter Password: ")
esxi_username = "root"
esxi_username_input = input(f"👤 ESXi Username (default: {esxi_username}): ")
if esxi_username_input:
    esxi_username = esxi_username_input
esxi_password = getpass.getpass("🔐 ESXi Password: ")

# Hosts and patch configuration
#esxi_hosts = ['esxi04.lab.local']
#patch_file = "VMware-ESXi-8.0U3f-24784735-depot.zip"
#patch_profile = "ESXi-8.0U3f-24784735-standard"
print(f"\n⚠️  The patch file {patch_file} will be applied on the following ESXi hosts: ")
print(", ".join(esxi_hosts))
print()


def check_and_enable_ssh_on_host(vc_host, vc_user, vc_password, target_host):
    try:
        # Bypass SSL verification (insecure, for lab use)
        context = ssl._create_unverified_context()
        si = SmartConnect(host=vc_host, user=vc_user, pwd=vc_password, sslContext=context)
        content = si.RetrieveContent()

        # Find the ESXi host object
        obj_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
        esxi_host = None
        for host in obj_view.view:
            if host.name == target_host:
                esxi_host = host
                break
        obj_view.Destroy()

        if not host:
            print(f"[!] ESXi host {host} not found in vCenter.")
            Disconnect(si)
            return

        # Get the SSH service
        ssh_service = None
        for svc in host.configManager.serviceSystem.serviceInfo.service:
            if svc.key == "TSM-SSH":
                ssh_service = svc
                break

        if not ssh_service:
            print(f"[!] SSH service not found!")
            Disconnect(si)
            return

        # Check SSH status and enable if not running
        if ssh_service.running:
            print(f"✅ SSH is already running...\n")
        else:
            print(f"⚙️  SSH is stopped. Starting it now...")
            esxi_host.configManager.serviceSystem.StartService(id='TSM-SSH')
            print(f"    ✅ SSH started...\n")

        Disconnect(si)

    except Exception as e:
        print(f"[!] Error checking/enabling SSH: {e}")


# Function to put the host in MM via vCenter - it will trigger the DRS to migrate the VMs (if necessary)
def put_host_in_maintenance_mode_vcenter(vc_host, vc_user, vc_password, target_host):
    context = ssl._create_unverified_context()
    si = SmartConnect(host=vc_host, user=vc_user, pwd=vc_password, sslContext=context)
    atexit.register(Disconnect, si)
    content = si.RetrieveContent()

    host_obj = None
    for datacenter in content.rootFolder.childEntity:
        for host_folder in datacenter.hostFolder.childEntity:
            for host in host_folder.host:
                if host.name == target_host:
                    host_obj = host
                    break

    if not host_obj:
        print(f"[!] Could not find host {target_host} in vCenter.")
        return False

    print(f"    ⚙️  Putting the ESXi host in Maintenance Mode using vCenter (ensureAccessibility)...")
    try:
        task = host_obj.EnterMaintenanceMode_Task(timeout=0,
                                                  evacuatePoweredOffVms=True
                                                  #maintenanceSpec=vim.host.MaintenanceSpec(
                                                  #    vsanMode=vim.vsan.host.DecommissionMode(
                                                  #        objectAction="ensureAccessibility"
                                                      )
                                                  #))
        WaitForTask(task)
        print("         ✅ Host is now in Maintenance Mode!\n")
        return True
    except Exception as e:
        print(f"[!] Failed to put host in Maintenance Mode via vCenter: {e}")
        return False

# Function to get the remote datastore path to upload the patch file
def get_remote_datastore(host, username, password):
    try:
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=host, username=username, password=password, timeout=3)

            stdin, stdout, stderr = ssh.exec_command("ls -d /vmfs/volumes/OSDATA*")
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            if error:
                print(f"[!] Error while finding OSDATA datastore: {error}")
                return None

            paths = output.splitlines()
            if not paths:
                print("[!] No OSDATA datastore found.")
                return None

            return paths[0]

    except paramiko.AuthenticationException:
        print("Authentication failed.")
    except Exception as e:
        print(f"SSH error: {e}")

# Function to upload the patch file to the remote host
def upload_patch_file(host, username, password, remote_patch_path):
    try:
        transport = paramiko.Transport((host, 22))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        print(f"    ⚙️  Uploading the file {patch_file} to the remote directory...")
        sftp.put(patch_file, remote_patch_path)
        print("         ✅ Done!\n")

        sftp.close()
        transport.close()
    except Exception as e:
        print(f"SFTP error: {e}")

# Reusable function to run a command over SSH
def run_command(ssh, command, silent=False):
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode()
    error = stderr.read().decode()
    if not silent:
        if output:
            print(output)
        if error:
            print(f"[!] Error: {error}")
    return output.strip(), error.strip()

# Function to wait for host after rebooting it
def wait_for_host(host):
    print(f"        ⚙️  Waiting for the host to come back online...")
    while True:
        try:
            sock = socket.create_connection((host, 22), timeout=5)
            sock.close()
            print(f"            ✅ The host is back online!\n")
            break
        except (socket.timeout, socket.error):
            print(".", end="", flush=True)
            time.sleep(5)

# Function to apply the patch
def applying_esxi_patch(host, username, password, remote_patch_path):
    try:
        if not put_host_in_maintenance_mode_vcenter(vc_host, vc_user, vc_password, host):
            return

        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=host, username=username, password=password, timeout=3)

            print(f"    ⚙️  Installing the patch {patch_file}......")
            stdin, stdout, stderr = ssh.exec_command(
                f'esxcli software profile update -d {remote_patch_path} -p {patch_profile} --no-hardware-warning'
            )
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            patch_applied = False
            patch_already_applied = False

            for line in output.splitlines():
                if "Message: Host is not changed." in line:
                    print(f"         ✅ Patch already applied, skipping reboot.\n")
                    patch_already_applied = True
                    break
                elif "The update completed successfully" in line:
                    print(f"         ✅ Patch applied successfully! Proceeding with reboot...\n")
                    patch_applied = True
                    break

            if error:
                print(f"         ❌ Error: {error}")
                return

        if patch_applied:
            with paramiko.SSHClient() as ssh:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hostname=host, username=username, password=password, timeout=3)
                print(f"    ⚙️  Rebooting the ESXi host...")
                ssh.exec_command("reboot")

            time.sleep(180)
            wait_for_host(host)

            with paramiko.SSHClient() as ssh:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hostname=host, username=username, password=password, timeout=3)
                print(f"    ⚙️  Removing the host from maintenance mode...")
                run_command(ssh, 'esxcli system maintenanceMode set --enable false')
                print("         ✅ Done!\n")

        else:
            print(f"    ⚠️  Skipping reboot due to patch already applied. Check directly on the host!")
            print(f"        ⚙️  Removing the host from maintenance mode...")
            with paramiko.SSHClient() as ssh:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hostname=host, username=username, password=password, timeout=3)
                run_command(ssh, 'esxcli system maintenanceMode set --enable false')
                print("             ✅ Done!\n")

        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=host, username=username, password=password, timeout=3)
            print(f"    ⚙️  Deleting the uploaded file {patch_file}...")
            run_command(ssh, f'rm -f {remote_patch_path}')
            print("         ✅ Done!\n")

    except Exception as e:
        print(f"Applying Patch Error: {e}")

# Main loop
for host in esxi_hosts:
    print("-"*100)
    print(f"🔄 Handling {host}: ")
    print("-"*100)
    check_and_enable_ssh_on_host(vc_host, vc_user, vc_password, host)
    remote_path = get_remote_datastore(host, esxi_username, esxi_password)
    if remote_path:
        remote_patch_path = f"{remote_path}/{patch_file}"
        upload_patch_file(host, esxi_username, esxi_password, remote_patch_path)
        applying_esxi_patch(host, esxi_username, esxi_password, remote_patch_path)
    print("-"*100)
