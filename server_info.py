import paramiko
import re
import os
from tabulate import tabulate

def get_device_info(hostname, username, private_key_path):
    try:
        # Establish SSH connection with private key
        private_key = paramiko.RSAKey(filename=private_key_path)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, pkey=private_key)

        # Execute commands to get device information
        stdin, stdout, stderr = ssh.exec_command('df -h /')
        df_output = stdout.read().decode('utf-8')

        stdin, stdout, stderr = ssh.exec_command('top -bn1 | grep "Cpu(s)"')
        cpu_output = stdout.read().decode('utf-8')

        stdin, stdout, stderr = ssh.exec_command('free -h')
        memory_output = stdout.read().decode('utf-8')

        return df_output, cpu_output, memory_output

    except Exception as e:
        return f"Error: {str(e)}"

    finally:
        # Close SSH connection
        ssh.close()

def parse_ssh_config():
    config_path = os.path.expanduser("~/.ssh/config")
    ssh_config = paramiko.SSHConfig()
    ssh_config.parse(open(config_path))

    servers = []

    for host_info in ssh_config.get_hostnames():
        config = ssh_config.lookup(host_info)
        if '*' in host_info:
            continue
        servers.append({
            "servername": host_info,
            "hostname": config.get("hostname"),
            "username": config.get("user", os.getlogin()),
            "private_key_path": config.get("identityfile", [])[0] if config.get("identityfile") else None
        })

    return servers

def main():
    server_configs = parse_ssh_config()
    sorted_configs = sorted(server_configs, key=lambda x: x["servername"])
    table_data = []

    for config in sorted_configs:
        servername = config["servername"]
        hostname = config["hostname"]
        username = config["username"]
        private_key_path = config["private_key_path"]

        df_output, cpu_output, memory_output = get_device_info(hostname, username, private_key_path)

        # Extracting disk information
        df_lines = df_output.split('\n')
        for line in df_lines:
            if '/' in line:
                df_columns = re.split('\s+', line)
                if len(df_columns) >= 5:
                    total_capacity = df_columns[1]
                    current_capacity = df_columns[2]
                    percentage = df_columns[4]

        # Extracting CPU information
        cpu_columns = re.split('\s+', cpu_output)
        cpu_usage = cpu_columns[1]

        # Extracting memory information
        memory_lines = memory_output.split('\n')
        memory_columns = re.split('\s+', memory_lines[1])
        total_memory = memory_columns[1]
        used_memory = memory_columns[2]
        free_memory = memory_columns[3]

        table_data.append([servername, hostname, total_capacity, current_capacity, percentage, cpu_usage, total_memory, used_memory, free_memory])

    headers = ["Server Name", "Host Name", "Total Capacity", "Current Capacity", "Percentage Used", "CPU Usage", "Total Memory", "Used Memory", "Free Memory"]
    print(tabulate(table_data, headers=headers, tablefmt="pretty"))

if __name__ == "__main__":
    main()