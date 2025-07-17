# 🛠️ py_vESXiPatcher

A Python-based automation script to patch multiple ESXi hosts using `esxcli`, with full integration to vCenter for proper maintenance mode handling in vSAN environments.

## 🚀 Features

- ✅ Puts hosts into Maintenance Mode via vCenter API (with **vSAN Ensure Accessibility**)
- 📦 Uploads and applies a local ESXi patch depot file (`.zip`) via SSH
- 🔄 Automatically reboots hosts if patch is applied
- 🔁 Waits for host to come back online before exiting maintenance mode
- 🧼 Cleans up patch files from host datastore after patching
- 🧠 Accepts one or multiple ESXi hosts as command-line arguments

---

## 📌 Prerequisites

- Python 3.6+
- Access to:
  - vCenter Server
  - ESXi hosts with SSH enabled
- Patch depot file (e.g. `VMware-ESXi-8.0U3f-24784735-depot.zip`) in the script directory
- Required Python packages:

```bash
pip install pyvmomi paramiko
```

---

## 📝 Script Usage

```bash
./py_vESXiPather.py <ESXi_host1> <ESXi_host2>....<ESXi-host'n'> --patch-file <Patch File> --patch-profile <Patch Profile Name>
```

Example:
```bash
./py_vESXiPather.py dr-esxi-01.lab.local dr-esxi-02.lab.local dr-esxi-03.lab.local --patch-file VMware-ESXi-8.0U3f-24784735-depot.zip --patch-profile ESXi-8.0U3f-24784735-standard
```
