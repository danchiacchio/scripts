# 🧰 vSphere VM Snapshot Viewer

This Python script connects to a VMware vCenter server and retrieves detailed information about all snapshots across all virtual machines (VMs). The output is neatly formatted in a human-readable table, showing VM names, snapshot names (with indentation for child snapshots), and creation timestamps.

---

## ✨ Features

- Connects securely to your vCenter using `pyVmomi`
- Lists **all VMs with snapshots**, including child snapshots with indentation
- Displays **snapshot creation time**
- Output is formatted and aligned for easy reading
- Compatible with Python 3

---

## 📦 Requirements

- Python 3.x
- `pyVmomi` library
- vCenter credentials

Install dependencies with:

```bash
pip install pyvmomi
```

---

## 📝 Script Usage

```bash
python3 py_vGetVMSnapshots.py 
```

