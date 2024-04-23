import concurrent.futures
import paramiko
import re
import os
from tabulate import tabulate


class ServerInfoRetriever:
    def __init__(self, hostname, username, private_key_path):
        self.hostname = hostname
        self.username = username
        self.private_key_path = private_key_path
        self.ssh = self._establish_ssh_connection()

    def _establish_ssh_connection(self):
        try:
            private_key = paramiko.RSAKey(filename=self.private_key_path)
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.hostname, username=self.username, pkey=private_key)
            return ssh
        except Exception as e:
            print(f"Failed to establish SSH connection: {e}")
            return None

    def _execute_ssh_command(self, command):
        try:
            stdin, stdout, stderr = self.ssh.exec_command(command)
            return stdout.read().decode('utf-8').strip()
        except Exception as e:
            print(f"Failed to execute command '{command}': {e}")
            return None

    def get_device_info(self):
        df_root_output = self._execute_ssh_command('df -h /')
        df_app_output = self._execute_ssh_command('df -h /app')
        df_data_output = self._execute_ssh_command('df -h /data')
        cpu_output = self._execute_ssh_command('top -bn1 | grep "Cpu(s)"')
        memory_output = self._execute_ssh_command('free -h')
        default_interface = self._execute_ssh_command("sudo ip route | grep default | awk '{print $5}'")
        ip_output = self._execute_ssh_command(f"sudo ip addr show {default_interface} | grep 'inet ' | awk '{{print $2}}' | cut -d'/' -f1")

        if None in [df_root_output, df_app_output, df_data_output, cpu_output, memory_output, ip_output]:
            print(f"Error retrieving information for server: {self.hostname}")
            return None

        return df_root_output, df_app_output, df_data_output, cpu_output, memory_output, ip_output

    def close_connection(self):
        if self.ssh:
            self.ssh.close()

def parse_ssh_config():
    config_path = os.path.expanduser("~/.ssh/config_backup")
    ssh_config = paramiko.SSHConfig()
    with open(config_path) as config_file:
        ssh_config.parse(config_file)

    servers = []
    for host_info in ssh_config.get_hostnames():
        if '*' in host_info:
            continue
        config = ssh_config.lookup(host_info)
        servers.append({
            "servername": host_info,
            "hostname": config.get("hostname"),
            "username": config.get("user", os.getlogin()),
            "private_key_path": config.get("identityfile", [])[0] if config.get("identityfile") else None
        })
    return servers

def fetch_server_info(config):
    retriever = ServerInfoRetriever(config["hostname"], config["username"], config["private_key_path"])
    device_info = retriever.get_device_info()
    retriever.close_connection()

    if device_info:
        df_root_output, df_app_output, df_data_output, cpu_output, memory_output, ip_output = device_info
        return config['servername'], config['hostname'], ip_output, df_root_output, df_app_output, df_data_output, cpu_output, memory_output
    else:
        return config['servername'], config['hostname'], 'Error', 'Error', 'Error', 'Error', 'Error', 'Error'

def display_server_info(results, headers):

    header_format = " | ".join([
         "{:<20}",  # servername: 20자
         "{:<15}",  # hostname: 17자
         "{:<15}",  # ip_output: 17자
         "{:<7}",  # root_total_capacity: 11자
         "{:<7}",  # root_current_capacity: 11자
         "{:<7}",  # root_percentage: 11자
         "{:<8}",  # app_total_capacity: 11자
         "{:<8}",  # app_current_capacity: 11자
         "{:<8}",  # app_percentage: 11자
         "{:<9}",  # data_total_capacity: 11자
         "{:<9}",  # data_current_capacity: 11자
         "{:<7}",  # data_percentage: 11자
         "{:<9}",  # cpu_usage: 11자
         "{:<12}",  # total_memory: 11자
         "{:<11}",  # used_memory: 11자
         "{:<11}"   # free_memory: 11자
    ])
#    header_format = " | ".join("{:<16}" for _ in headers)
    header_line = header_format.format(*headers)
    print(header_line)
    print("-" * len(header_line))

    sorted_result = sorted(results, key=lambda x: x[0])

    for data in sorted_result:
        servername, hostname, ip_output, df_root_output, df_app_output, df_data_output, cpu_output, memory_output = data

        # Extracting disk information
        root_total_capacity = '-'
        root_current_capacity = '-'
        root_percentage = '-'
        
        app_total_capacity = '-'
        app_current_capacity = '-'
        app_percentage = '-'

        data_total_capacity = '-'
        data_current_capacity = '-'
        data_percentage = '-'
        
        df_lines = df_root_output.split('\n')
        for line in df_lines:
            if '/' in line:
                df_columns = re.split('\s+', line)
                if len(df_columns) >= 5:
                    root_total_capacity = df_columns[1]
                    root_current_capacity = df_columns[2]
                    root_percentage = df_columns[4]

        df_lines = df_app_output.split('\n')
        for line in df_lines:
            if '/' in line:
                df_columns = re.split('\s+', line)
                if len(df_columns) >= 5:
                    app_total_capacity = df_columns[1]
                    app_current_capacity = df_columns[2]
                    app_percentage = df_columns[4]

        df_lines = df_data_output.split('\n')
        for line in df_lines:
            if '/' in line:
                df_columns = re.split('\s+', line)
                if len(df_columns) >= 5:
                    data_total_capacity = df_columns[1]
                    data_current_capacity = df_columns[2]
                    data_percentage = df_columns[4]

        # Extracting CPU information
        cpu_columns = re.split('\s+', cpu_output)
        cpu_usage = cpu_columns[1]

        # Extracting memory information
        memory_lines = memory_output.split('\n')
        memory_columns = re.split('\s+', memory_lines[1])
        total_memory = memory_columns[1]
        used_memory = memory_columns[2]
        free_memory = memory_columns[3]

#        data_line = " | ".join("{:<16}" for _ in headers).format(servername, hostname, ip_output, root_total_capacity, root_current_capacity, root_percentage, app_total_capacity, app_current_capacity, app_percentage, data_total_capacity, data_current_capacity, data_percentage, cpu_usage, total_memory, used_memory, free_memory)
        data_line = " | ".join([
            "{:<20}",  # servername: 20자
            "{:<15}",  # hostname: 17자
            "{:<15}",  # ip_output: 17자
            "{:<7}",  # root_total_capacity: 11자
            "{:<7}",  # root_current_capacity: 11자
            "{:<7}",  # root_percentage: 11자
            "{:<8}",  # app_total_capacity: 11자
            "{:<8}",  # app_current_capacity: 11자
            "{:<8}",  # app_percentage: 11자
            "{:<9}",  # data_total_capacity: 11자
            "{:<9}",  # data_current_capacity: 11자
            "{:<7}",  # data_percentage: 11자
            "{:<9}",  # cpu_usage: 11자
            "{:<12}",  # total_memory: 11자
            "{:<11}",  # used_memory: 11자
            "{:<11}"   # free_memory: 11자
        ]).format(servername, hostname, ip_output, root_total_capacity, root_current_capacity, root_percentage, app_total_capacity, app_current_capacity, app_percentage, data_total_capacity, data_current_capacity, data_percentage, cpu_usage, total_memory, used_memory, free_memory)

        print(data_line)

def main():
    server_configs = parse_ssh_config()
    #sorted_configs = sorted(server_configs, key=lambda x: x["servername"])
    headers = ["Server Name", "Host Name", "Internal IP", "/ Tot", "/ Cur", "/ %",'/app Tot','/app Cur','/app %','/data Tot','/data Cur','/data %',"CPU Usage", "Total Memory", "Used Memory", "Free Memory"]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_server = {executor.submit(fetch_server_info, config): config for config in server_configs}
        results = []
        for future in concurrent.futures.as_completed(future_to_server):
            results.append(future.result())
    
    display_server_info(results, headers)

if __name__ == "__main__":
    main()
