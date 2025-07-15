#!/usr/bin/env python3

import sys
import ssl
import getpass
import os
import subprocess
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

# Function to clear the screen
def screen_clear():
    os.system('cls' if os.name == 'nt' else 'clear')
screen_clear()

print("-" * 80)
print("List VM Snapshots Details".center(80))
print("-" * 80)

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

# Function to get all VM snapshots
def list_vm_snapshots_with_indent(si):
    from datetime import datetime
    content = si.RetrieveContent()
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vms = container.view
    container.Destroy()

    # This empty list will used to store all snapshots details
    snapshot_report = []

    def child_snapshots(snapshots, vm_name, level=0):
        for snap in snapshots:
            snap_name = snap.name
            snap_time = snap.createTime.strftime("%Y-%m-%d %H:%M:%S")
            indent = "    " * level  # 4 spaces per level
            snapshot_report.append((vm_name, indent + snap_name, snap_time))
            # Recurse into child snapshots
            child_snapshots(snap.childSnapshotList, vm_name, level + 1)

    for vm in vms:
        if vm.snapshot is not None:
            root_snapshots = vm.snapshot.rootSnapshotList
            child_snapshots(root_snapshots, vm.name)

    return snapshot_report


# Call and print
snapshots = list_vm_snapshots_with_indent(si)


# This imports defaultdict from the collections module
# defaultdict is like a regular Python dictionary (dict), but with a default value type for missing keys.
# If you try to access a key that doesn't exist, it automatically creates it with a default value (in our case: an empty list []).
from collections import defaultdict


# Group snapshots by VM
snapshots_by_vm = defaultdict(list)
for vm_name, snap_name, snap_time in snapshots:
    snapshots_by_vm[vm_name].append((snap_name, snap_time))

# Print grouped output
for vm_name in sorted(snapshots_by_vm):
    print("-" * 120)
    for snap_name, snap_time in snapshots_by_vm[vm_name]:
        print(f"📦 VM: {vm_name:<25} | 📝 Snapshot: {snap_name:<35} | 📅 Created: {snap_time}")
print("-" * 120)


# Disconnect properly
Disconnect(si)
print(f"🔌 Disconnected from vCenter {vcenter} successfully.")

