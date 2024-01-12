import paramiko
import re
import os

def get_device_capacity(hostname, username, private_key_path):
    try:
        # Establish SSH connection with private key
        private_key = paramiko.RSAKey(filename=private_key_path)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, pkey=private_key)

        # Execute df command to get disk space information
        stdin, stdout, stderr = ssh.exec_command('df -h /')

        # Parse the output to get relevant information
        output = stdout.read().decode('utf-8')
        lines = output.split('\n')

        # Extracting total, used, and percentage information
        for line in lines:
            if '/' in line:
                columns = re.split('\s+', line)
                if len(columns) >= 5:
                    total_capacity = columns[1]
                    current_capacity = columns[2]
                    percentage = columns[4]
                    return total_capacity, current_capacity, percentage

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

    for config in server_configs:
        servername = config["servername"]
        hostname = config["hostname"]
        username = config["username"]
        private_key_path = config["private_key_path"]        
        total, current, percentage = get_device_capacity(hostname, username, private_key_path)
        print(f"{servername}({hostname}) : \t\t |\t{total}\t|\t{current}\t|\t{percentage}\t|")
        #print("=" * 40)

if __name__ == "__main__":
    main()