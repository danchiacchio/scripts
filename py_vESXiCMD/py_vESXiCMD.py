import paramiko
import getpass
import os
import csv

# Cross-platform screen clear
os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    print("=" * 60)
    print("🔧 py ESXi Command Runner".center(60))
    print("=" * 60)
    print("⚠️  All ESXi hosts must have the SAME root password.")
    print("ℹ️  This script uses SSH to connect to each host.")
    print("=" * 60)
show_banner()

esxi_username = input("ESXi Username: ")
esxi_password = getpass.getpass("ESXi Password: ")
esxi_command = input("Type the ESXi command: ")
print()


with open("esxi_hosts.txt", "r") as f:
    hostnames = [line.strip() for line in f if line.strip()]


def connect_ssh(host, esxi_username, esxi_password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=esxi_username, password=esxi_password, timeout=10)
        return ssh
    except Exception as e:
        print(f"❌ Connection to {host} failed: {e}")
        return None


def run_command(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(command)
    return stdout.read().decode().strip()


def run_esxi_command(esxi_username, esxi_password):
	results = []
	
	for host in hostnames:
		print(f"\n Connecting to {host}....")
		ssh = connect_ssh(host, esxi_username, esxi_password)
		if ssh:
			cmd = f"{esxi_command}"
			output = run_command(ssh, cmd)
			print(f" {output}")
			ssh.close()
				
			results.append({"Host": host, "Command Output": output})
				
		else:
			print(f"Failed to connect to {host}")
			results.append({"Host": host, "Command Output": "Connection Failed"})

	choice = input("\n 📄 Do you want to export the results to a CSV file? (yes/no): ").strip().lower()
	if choice in ("yes", "y"):
		csv_file = "esxi_cmd_output.csv"
		with open(csv_file, "w", newline="") as f:
			writer = csv.DictWriter(f, fieldnames=["Host", "Command Output"])
			writer.writeheader()
			writer.writerows(results)
		print(f"\n✅ Results exported to '{csv_file}'\n")
	else:
		print("\n👋 No CSV export. All done!\n")
		
		

run_esxi_command(esxi_username, esxi_password)
print()

#def spacer(lines=1):
#    print("\n" * lines)
#spacer()
