# 🔧 ESXi NTPD Manager

A Python script that automates the process of manager the NTP daemon on connected ESXi hosts.

---

## ✨ Features

- ✅ Secure password prompt for SSO and root credentials
- ✅ Connects to multiple ESXi hosts
- ✅ Retrieves currently NTP client configuration
- ✅ Can stop and start the NTP service on ESXi hosts
- ✅ Can change the NTP client configuration


---

## 📋 Requirements

- Python 3.x (I just tested with Python 3.12.3 - I did not test with earlier Python versions)
- `paramiko` library (SSH connections)
- SSH must be enabled on all ESXi hosts
- All ESXi hosts must use the **same root password**

Install `paramiko` if needed:

```bash
pip install paramiko

