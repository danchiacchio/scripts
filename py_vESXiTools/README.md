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

## 📋 Requirements

- Python 3.x (I just tested with Python 3.12.3 - I did not test with earlier Python versions)
- `paramiko` library (SSH connections)
- SSH must be enabled on all ESXi hosts
- All ESXi hosts must use the **same root password**

Install `paramiko` if needed:

```bash
pip install paramiko

