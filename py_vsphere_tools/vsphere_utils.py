#!/usr/bin/env python3
import core

core.screen_clear()
print("="*80)
print("py vSphere Utils".center(80))
print("="*80)

si = core.connect_vcenter()

while True:
    print()
    print("-"*20)
    print("📝 Options:")
    print("-"*20)
    print("1) Get all VMs")
    print("2) Get powered on VMs")
    print("3) Get powered off VMs")
    print("4) Power off VMs")
    print("5) Power on VMs")
    print("0) Exit")
    option = input("Enter choice [0-5]: ").strip()
    print()

    if option == "1":
        all_vms = core.get_all_vms(si)
        print(f"\n⚠️  There are {len(all_vms)} VMs.\n")

    elif option == "2":
        on_vms = core.get_poweredon_vms(si)
        print(f"\n✅ There are {len(on_vms)} powered-on VMs.\n")

    elif option == "3":
        off_vms = core.get_poweredoff_vms(si)
        print(f"\n❌ There are {len(off_vms)} powered-off VMs.\n")

    elif option == "4":
        core.poweroff_vms(si)
 
    elif option == "5":
        core.poweron_vms(si)

    elif option == "0":
        break

    else:
        print("Invalid selection. Try again.")

core.disconnect_vcenter(si)
