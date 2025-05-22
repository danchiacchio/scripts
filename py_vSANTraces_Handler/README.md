# 🛠️ ESXi vSAN Traces Handler

This script is a helper utility to connect to a VMware vCenter, list clusters, and work with ESXi hosts, especially in the context of vSAN traces or diagnostics. It is written in Python using `pyVmomi` and `paramiko`.

---

## 📦 Requirements

- Python 3
- Modules:
  - `pyVmomi`
  - `paramiko`
  - `getpass`
  - `ssl`
  - `os`, `sys`

You can install the required modules with:

```bash
pip install pyvmomi paramiko

