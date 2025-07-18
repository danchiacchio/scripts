# 🔧 VMware Tools ESXi Upgrader

A Python script that automates the process of **checking** and **upgrading VMware Tools** on multiple ESXi hosts via SSH.

---

## ✨ Features

- ✅ Secure password prompt for root credentials
- ✅ Connects to multiple ESXi hosts
- ✅ Retrieves currently installed VMware Tools version
- ✅ Copies offline bundle to `OSDATA` partition on each host
- ✅ Installs new VMware Tools without requiring a reboot
- ✅ Displays results in a clear, formatted table

---

## Script versions:

py_vESXiTools.py
- It is necessary to manually create the esxi_hosts.txt file and add all ESXi hosts into this file.
- If you plan to upgrade VMware Tools on Standalone hosts, you can use this script version.

py_vESXiTools-auto.py
- It's not necessary create a source file with all ESXi hosts.
- With this version, we can select in what vSphere Cluster we must to work on.
- There is a possibility to work on a specific host inside a cluster.

---

## 📋 Requirements

- Python 3.x (I just tested with Python 3.12.3 - I did not test with earlier Python versions)
- `paramiko` library (SSH connections)
- All ESXi hosts must use the **same root password**
- Download the VMware Tools Package (VMware Tools Offline VIB Bundle .zip) and place it on the same script directory
- vCenter and ESXi credentials

Install paramiko and prettytable if needed:

```bash
pip install paramiko
pip install prettytable
```

---

## Script Usage

To use the "manual" version of the script, you should update the following variables with your values:

 27 hosts_file = "esxi_hosts.txt"
 29 username = "root"
 30 local_file_path = "VMware-Tools-12.5.2-core-offline-depot-ESXi-all-24697584.zip"
 31 temp_dir_name = "vmware-tools-temp"

```bash
python3 py_vESXiTools.py
```

To use the "auto" version of the script, you just run the script:

```bash
python3 py_vESXiTools-auto.py
```
