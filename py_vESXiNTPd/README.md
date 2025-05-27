# 🔧 ESXi NTPD Manager

A Python script that automates the process of manager the NTP daemon on connected ESXi hosts.

---

## ✨ Features

- ✅ Secure password prompt for SSO and root credentials
- ✅ Connects to multiple ESXi hosts
- ✅ Retrieves currently NTP client configuration
- ✅ Can stop and start the NTP service on ESXi hosts
- ✅ Can change the NTP client configuration

## Script Versions
py_vESXiNTPd.py
- This is the first script version
- All features are enabled on this version

py_vESXiNTPd-v2.py
- The first version executes all options considering all ESXi in the same vCenter, regardless of the Cluster that they are - this can be bad for large environments with many clusters in the same vCenter
- With this version, you can select which clusters to work for. It provided more flexibility to work in multi-cluster environment

py_vESXiNTPd-v3.py
- This is an enhance version of the previous versions
- We have added new functions to interact with vCenter Server


---

## 📋 Requirements

- Python 3.x (I just tested with Python 3.12.3 - I did not test with earlier Python versions)
- `paramiko` library (SSH connections)
- SSH must be enabled on all ESXi hosts
- All ESXi hosts must use the **same root password**

Install `paramiko` if needed:

```bash
pip install paramiko

