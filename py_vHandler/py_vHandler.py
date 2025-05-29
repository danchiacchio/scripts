#!/usr/bin/env python3

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
from pyVmomi import vmodl
import ssl
import getpass
import atexit
import os
from pyfiglet import Figlet
import paramiko

# Cross-platform screen clear
os.system('cls' if os.name == 'nt' else 'clear')

# Fancy banner
f = Figlet(font='doom')
print(f.renderText('py vHandler'))


# Disable SSL certificate verification
context = ssl._create_unverified_context()

# Get credentials
vcenter = input("🌐 vCenter IP/FQDN: ")
username = "administrator@vsphere.local"
username_input = input(f"👤 vCenter SSO Username (default: {username}): ")
if username_input:
    username = username_input
password = getpass.getpass(prompt='🔐 vCenter SSO Password: ')
print()


# Connect to vCenter
try:
    si = SmartConnect(host=vcenter, user=username, pwd=password, sslContext=context)
    atexit.register(Disconnect, si)
except Exception as e:
    print(f"❌ Could not connect to vCenter: {e}")
    exit(1)


# ✅ Define this before get_all_vms
content = si.RetrieveContent()

# Function to get all VMs
def get_all_vms(content):
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )
    vms = container.view
    container.Destroy()
    return vms
# Fetch and print VMs
vms = get_all_vms(content)


def get_powered_on_vms(content):
    """Return a list of tuples with (VM name, Guest IP) for powered-on and connected VMs."""
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )
    powered_on_vms = []

    for vm in container.view:
        if vm.runtime.powerState == "poweredOn" and vm.runtime.connectionState == "connected":
            vm_name = vm.name
            guest_ip = vm.guest.ipAddress if vm.guest is not None else "N/A"
            powered_on_vms.append((vm_name, guest_ip if guest_ip else "N/A"))

    container.Destroy()
    return powered_on_vms



def get_powered_off_vms(content):
    """Return a list of powered-off VMs"""
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )
    powered_off_vms = [vm for vm in container.view if vm.runtime.powerState == "poweredOff"]
    container.Destroy()
    return powered_off_vms


def get_disconnected_vms(content):
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )
    disconnected_vms = [vm for vm in container.view if vm.runtime.connectionState == "disconnected"]
    container.Destroy()
    return disconnected_vms


def get_vmwaretools_status(content):
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )
    vm_tools_status = []

    for vm in container.view:
        vm_name = vm.name
        power_state = vm.runtime.powerState
        connection_state = vm.runtime.connectionState
        tools_status = vm.guest.toolsStatus
        tools_version = vm.guest.toolsVersion
        tools_version_status = vm.guest.toolsVersionStatus2

        # Skip vCLS system VMs
        if vm_name.startswith("vCLS"):
            continue

        if power_state == "poweredOn" and connection_state == "connected":
            vm_tools_status.append((vm_name, tools_status, tools_version, tools_version_status))

    container.Destroy()
    return vm_tools_status


def get_all_datastores(content):
    """Returns a list of all datastores in the vCenter."""
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.Datastore], True
    )
    datastores = container.view
    container.Destroy()

    # Extract and return relevant info
    datastore_info = []
    for ds in datastores:
        name = ds.name
        capacity_gb = round(ds.summary.capacity / (1024**3), 2)
        free_space_gb = round(ds.summary.freeSpace / (1024**3), 2)
        type = ds.summary.type
        accessible = ds.summary.accessible
        datastore_info.append((name, type, capacity_gb, free_space_gb, accessible))

    return datastore_info



def run_vcenter_ssh_command():
    # Prompt for connection details
    hostname = input("🔗 Enter vCenter hostname or IP: ")
    username = input("👤 Enter SSH username (e.g., root): ")
    password = getpass.getpass("🔐 Enter SSH password: ")

    command = input("Enter the command here: ")

    try:
        # Set up SSH connection
        print("\n🔌 Connecting via SSH...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, username=username, password=password)

        # Execute the command
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        client.close()

        # Display output
        if output:
            print("\n📦 Command Output:\n")
            print(output)
        if error:
            print("\n❌ Error Output:\n")
            print(error)

    except Exception as e:
        print(f"\n❗ SSH Connection Failed: {e}")


def get_esxi_hosts_and_ssh_status(content):
    """Retrieve all ESXi hosts and check if SSH service is running and its startup policy."""
    esxi_hosts_info = []

    # Get all ESXi hosts in the vCenter
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.HostSystem], True
    )

    # Iterate over all ESXi hosts
    for host in container.view:
        host_name = host.name

        # Initialize the SSH service status and startup policy
        ssh_service_running = "unknown"
        ssh_startup_policy = "unknown"
        host_status = None  # To track the host's status

        try:
            # Get the service info for the host
            service_info = host.configManager.serviceSystem.serviceInfo

            # Check for the presence of SSH services
            ssh_found = False
            for service in service_info.service:
                if "SSH" in service.key:  # Check if the service key contains SSH
                    ssh_service_running = service.running
                    ssh_startup_policy = service.policy
                    ssh_found = True
                    break

            if not ssh_found:
                # If SSH service is not found
                ssh_service_running = "SSH service not found"
                ssh_startup_policy = "N/A"

        except vmodl.fault.HostCommunication as e:
            # Suppress the error and set the status to unreachable
            host_status = "Host unreachable"

        except Exception as e:
            # General exception handler for other errors, suppressing error details
            host_status = "Unknown error"

        # Determine the correct output
        if host_status == "Host unreachable":
            esxi_hosts_info.append((host_name, "Host unreachable", "N/A"))
        else:
            esxi_hosts_info.append((host_name, ssh_service_running, ssh_startup_policy))

    container.Destroy()
    return esxi_hosts_info








def show_menu():
    print("="*100)
    print("📋 py vSphere Handler Menu:")
    print("-"*100)

    left_column = [
        f"1. List all VMs",
        f"2. List powered-on VMs",
        f"3. List powered-off VMs",
        f"4. List VMs with VMware Tools",
        f"5. List disconnected"
    ]

    right_column = [
        f"6. List datastores details",
        f"7. Run a command on vCenter",
        f"8. List SSH service status on Hosts",
        f"9. TBD",
        f"0. Exit"
    ]

    # Combine both columns row by row
    for left, right in zip(left_column, right_column):
        print(f"{left:<45} {right}")

    print("="*100)



def get_user_choice():
    valid_choices = [str(i) for i in range(9)]  # "0" through "8"

    while True:
        choice = input("Enter your choice: ").strip()
        if choice in valid_choices:
            return choice
        else:
            print("❌ Invalid choice. Please enter a number between 0 and 7.\n")


#Main loop:
def main():
    while True:
        show_menu()
        choice = get_user_choice()

        if choice == "0":
            print("👋 Exiting.")
            break

        if choice == "1":
            print(f"\n📋 All VMs (Total: {len(vms)}):")
            for vm in vms:
                print("-", vm.name)

        elif choice == "2":
            powered_vms = get_powered_on_vms(content)
            print()
            print(f"\n⚡ Powered-On VMs (Total: {len(powered_vms)}):\n{'-' * 70}")
            for vm_name, ip in get_powered_on_vms(content):
                print(f"{vm_name:<50} IP: {ip}")


        elif choice == "3":
            powered_off_vms = get_powered_off_vms(content)
            print(f"\n⏹️ Powered-Off VMs (Total: {len(powered_off_vms)}):")
            for vm in powered_off_vms:
                print("-", vm.name)
    
        elif choice == "4":
            print("\n📦 Powered-On VMs with VMware Tools Status & Version:\n")

            # Print the header
            print(f"{'VM Name':<30} {'Tools Status':<12} {'Version':<8} {'Version Status'}")
            print("-" * 70)

            for name, status, version, version_status in get_vmwaretools_status(content):
                if status in ["toolsOk", "toolsOld"] and not name.startswith("vCLS"):
                    print(f"{name:<30} {status:<12} {version:<8} {version_status}")

        elif choice == "5":
            disconnected_vms = get_disconnected_vms(content)
            print(f"\n🔌 Disconnected VMs (Total: {len(disconnected_vms)}):")
            for vm in get_disconnected_vms(content):
                print("-", vm.name)

        elif choice == "6":
            print(f"\n📁 Datastores under vCenter {vcenter}:\n")
            datastores = get_all_datastores(content)
        
            print(f"{'Status':<6} {'Datastore Name':<25} {'Type':<10} {'Total(GB)':<12} {'Free(GB)':<12} {'Used %':<6}")
            print("-" * 75)

            for name, type, total, free, accessible in datastores:
                used = total - free
                percent_used = (used / total) * 100 if total > 0 else 0
                status = "✅" if accessible else "❌"
                print(f"{status:<6} {name:<25} {type:<10} {total:<12.2f} {free:<12.2f} {percent_used:<6.1f}")

        elif choice == "7":
            run_vcenter_ssh_command()


        elif choice == "8":
            esxi_hosts_info = get_esxi_hosts_and_ssh_status(content)
            for host, status, policy in esxi_hosts_info:
                print(f"Host: {host}, SSH Running: {status}, SSH Startup Policy: {policy}")


        else:
            print("❗ Invalid choice. Try again.")


main()
