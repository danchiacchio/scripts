# 🛠️ ESXi vSAN Traces Handler

This script is a helper utility to connect to a VMware vCenter, list clusters, and work with ESXi hosts, especially in the context of vSAN traces or diagnostics. It is written in Python using `pyVmomi` and `paramiko`.

---

## 🔧 Features

- ✅ View vSAN Traces details
- ✅ Get vSAN Traces Usage
- ✅ Change the vSAN Traces Directory
- ✅ List the most recent vSAN Traces files
- ✅ List all ESXi mount points

---

## 📦 Requirements

- Python 3
- Modules:
  - `pyVmomi`
  - `paramiko`
  - `getpass`
  - `ssl`
  - `os`, `sys`
- vCenter and ESXi credentials

You can install the required modules with:

```bash
pip install pyvmomi paramiko
```

---

## 📝 Script Usage

```bash
python3 pyvSANTracesHandler.py
```
