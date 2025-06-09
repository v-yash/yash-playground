import paramiko

def establish_ssh_connection(private_ip, username='conman', key_filename='/Users/yash.verma/Documents/conman.pem'):
    """
    Establishes an SSH connection to the given instance.
    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(private_ip, username=username, key_filename=key_filename)
        return ssh
    except Exception as e:
        print(f"Error establishing SSH connection to {private_ip}: {e}")
        return None
