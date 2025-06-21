import sys
import ssl
import getpass
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import time
import os

# Function to clear the screen:
def screen_clear():
    os.system('cls' if os.name == 'nt' else 'clear')
##########END

# Function to connect to the vCenter Server:
def connect_vcenter(port=443):
    vcenter = input(f"🌐 vCenter IP or FQDN: ")
    user = "administrator@vsphere.local"
    user_input = input(f"👤 vCenter SSO Username (default: {user}): ")
    if user_input:
        user = user_input
    pwd = getpass.getpass("🔐 Password: ")
    print()

    context = ssl._create_unverified_context()

    try:
        si = SmartConnect(host=vcenter, user=user, pwd=pwd, port=port, sslContext=context)
        print(f"     ✅ Connected to the vCenter {vcenter} with success!")
        return si
    except vim.fault.InvalidLogin:
        print("❌ Invalid username or password. Please try again.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to connect to vCenter: {e}")
        sys.exit(1)
##########END

# Function to disconnect to the vCenter Server:
def disconnect_vcenter(si):
    Disconnect(si)
    print(f"     ❌ Disconnected to the vCenter with success!\n")
##########END

# Function to print vms in columns:
def print_vms_in_columns(vm_list, columns=3):
    if not vm_list:
        return
    items = [f"{i}) {vm.name}" for i, vm in enumerate(vm_list)]
    rows = (len(items) + columns - 1) // columns  # Ceiling division for rows

    # Calculate max width for padding
    max_len = max(len(item) for item in items) + 4  # Add some space between columns

    for row in range(rows):
        line = ""
        for col in range(columns):
            idx = row + col * rows
            if idx < len(items):
                line += f"{items[idx]:<{max_len}}"
        print(line)
    print()
##########END


# Function to get all VMs into the vCenter Server:
def get_all_vms(si):
    content = si.RetrieveContent()
    container_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vm_list = list(container_view.view)
    container_view.Destroy()
    
    print_vms_in_columns(vm_list, columns=3)
    
    return sorted([vm.name for vm in vm_list], key=str.lower)
    Disconnect(si)
##########END


# Function to get all powered on vms:
def get_poweredon_vms(si):
    content = si.RetrieveContent()
    container_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vm_list = list(container_view.view)
    container_view.Destroy()

    powered_on_vms = []

    for vm in vm_list:
        try:
            vm_name = vm.name
            power_state = vm.runtime.powerState
            connection_state = vm.runtime.connectionState
        
            if power_state == "poweredOn" and connection_state == "connected":
                powered_on_vms.append(vm)
        
        except Exception as e:
            print(f"⚠️  Could not read state for VM object: {e}")

    print_vms_in_columns(powered_on_vms, columns=3)

    return sorted([vm.name for vm in powered_on_vms], key=str.lower)
    Disconnect(si)
##########END

# Function to get all powered off VMs:
def get_poweredoff_vms(si):
    content = si.RetrieveContent()
    container_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vm_list = list(container_view.view)
    container_view.Destroy()

    powered_off_vms = []

    for vm in vm_list:
        try:
            vm_name = vm.name
            power_state = vm.runtime.powerState
            connection_state = vm.runtime.connectionState
        
            if power_state == "poweredOff" and connection_state == "connected":
                powered_off_vms.append(vm)

        except Exception as e:
            print(f"⚠️  Could not read state for VM object: {e}")

    print_vms_in_columns(powered_off_vms, columns=3)
    
    return sorted([vm.name for vm in powered_off_vms], key=str.lower)
    Disconnect(si)
##########END

# Function to parse user selection to power up or power off vms:
def parse_selection_input(input_str, max_len):
    indexes = set()
    parts = input_str.split(',')
    for part in parts:
        if '-' in part:
            start, end = part.split('-')
            start, end = int(start), int(end)
            indexes.update(range(start, end + 1))
        else:
            indexes.add(int(part))
    return sorted(i for i in indexes if 0 <= i < max_len)
##########END

# Function to power off VMs:
def poweroff_vms(si):
    content = si.RetrieveContent()
    container_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vm_list = list(container_view.view)
    container_view.Destroy()

    powered_on_vms = sorted(
        [vm for vm in vm_list if vm.runtime.powerState == "poweredOn" and vm.runtime.connectionState == "connected"],
        key=lambda vm: vm.name.lower()
    )

    if not powered_on_vms:
        print("✅ All VMs are already powered off.")
        return []

    # Show list with indexes
    print("\n🛑 Powered-on VMs:")
    print_vms_in_columns(powered_on_vms, columns=3)
    print()

    # Ask user for range/input
    selection = input("Enter VM numbers to power off (e.g. 0-3,4,6) or 'q' to cancel: ")
    if selection.lower() == 'q':
        return []

    # Parse ranges
    indexes = parse_selection_input(selection, len(powered_on_vms))

    for i in indexes:
        vm = powered_on_vms[i]
        print(f"🔻 Powering off: {vm.name}")
        try:
            if vm.guest.toolsStatus == "toolsOk":
                vm.ShutdownGuest()
            else:
                print("⚠️  VMware Tools not available. Forcing power off.")
                vm.PowerOff()
        except Exception as e:
            print(f"❌ Error shutting down {vm.name}: {e}")
        time.sleep(2)

    return sorted(powered_on_vms, key=lambda vm: vm.name.lower())
    Disconnect(si)
##########END


# Function to power on vms:
def poweron_vms(si):
    content = si.RetrieveContent()
    container_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vm_list = list(container_view.view)
    container_view.Destroy()

    powered_off_vms = sorted(
        [vm for vm in vm_list if vm.runtime.powerState == "poweredOff" and vm.runtime.connectionState == "connected"],
        key=lambda vm: vm.name.lower()
    )

    if not powered_off_vms:
        print("✅ All VMs are already powered on.")
        return []

    # Show list with indexes
    print("\n🛑 Powered-off VMs:")
    print_vms_in_columns(powered_off_vms, columns=3)
    print()

    # Ask user for range/input
    selection = input("Enter VM numbers to power off (e.g. 0-3,4,6) or 'q' to cancel: ")
    if selection.lower() == 'q':
        return []

    # Parse ranges
    indexes = parse_selection_input(selection, len(powered_off_vms))

    for i in indexes:
        vm = powered_off_vms[i]
        print(f"⚡ Powering on: {vm.name}")
        task = vm.PowerOn()
        time.sleep(2)  # Optional delay between power-ons

    return sorted(powered_off_vms, key=lambda vm: vm.name.lower())
    Disconnect(si)
##########END
