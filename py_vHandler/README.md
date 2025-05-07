# 🛠️ py vHandler

A Python script for interacting with your **vSphere environment** using the `pyVmomi` API. Quickly list VMs, check their power state, VMware Tools status, datastore info, and more — all in a user-friendly menu format.

---

## 📦 Features

- 📋 List all VMs
- ⚡ List powered-on VMs
- ⏹️ List powered-off VMs
- 📦 Show VMware Tools status & version
- 🔌 Show disconnected VMs
- 📁 List datastore details
- 💻 Run custom commands on vCenter (coming soon)

---

## ✅ Requirements

- Python **3.x**
- Required Python packages:
  - `pyvim`
  - `pyvmomi`
  - `pyfiglet`
  - `paramiko`

### 🔧 Install Dependencies

Using `pip`:

```bash
pip3 install pyvim pyvmomi pyfiglet paramiko

