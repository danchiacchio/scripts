# 🔧 py_vESXiCMD

A Python-based utility to run custom shell commands on multiple ESXi hosts via SSH and optionally export the results to a CSV file.

---

## 📋 Features

- Run any shell command on multiple ESXi hosts
- Connects via SSH using the same credentials for all hosts
- Clears the screen and shows a clean banner UI
- Optionally exports output to a CSV file
- Uses `paramiko` for SSH connections

---

## 🚀 Requirements

- Python 3.x
- `paramiko` library

Install the required dependency using pip:

```bash
pip install paramiko

