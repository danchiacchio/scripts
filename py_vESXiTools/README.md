# 🔧 VMware Tools ESXi Manager

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
-- This is the first version;
-- It is necessary to manually create the esxi_hosts.txt file and add all ESXi hosts into this file.

py_vESXiTools-v2.py
-- This is the newest version;
-- It can grab all ESXi hosts under the vCenter Server and create the file esxi_hosts.txt with all ESXi hosts.

---

## 📋 Requirements

- Python 3.x (I just tested with Python 3.12.3 - I did not test with earlier Python versions)
- `paramiko` library (SSH connections)
- SSH must be enabled on all ESXi hosts
- All ESXi hosts must use the **same root password**
- Download the VMware Tools Package (VMware Tools Offline VIB Bundle .zip) and place it on the same script directory
- Edit the script to type the correct VMware Tools Offline VIB Bundle name

Install `paramiko` if needed:

```bash
pip install paramiko

