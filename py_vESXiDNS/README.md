# ESXi DNS Manager

A Python-based interactive script to manage DNS configurations on multiple connected ESXi hosts via the vSphere API and SSH. This tool simplifies DNS-related operations and general command execution across your environment.

## 🔧 Features

- ✅ View DNS configuration for all ESXi hosts
- 🛠️ Update DNS server IPs
- 🌐 Update DNS domain name
- 🔄 Flush DNS cache remotely via SSH
- 💻 Execute custom commands on all ESXi hosts
- 🚧 Expandable menu for future functionality

---

## 🔐 Requirements

- Python 3.x
- `pyVmomi` for vSphere API interaction
- `paramiko` for SSH command execution
- Access to vCenter/ESXi with valid credentials and permissions
- SSH must be enabled on the ESXi hosts

---

## 🚀 Getting Started

1. Clone the repository or copy the script to your local machine.
2. Install the required Python packages:

```bash
pip install pyvmomi paramiko

