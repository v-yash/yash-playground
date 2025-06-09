from ssh_utils import establish_ssh_connection

def log_output(message, log_file):
    """
    Logs the given message to the log file.
    """
    with open(log_file, 'a') as f:
        f.write(message + "\n")

def verify_authorized_keys_sudoers(instances, log_file="output.log"):
    # List of instance IDs to skip
    excluded_instances = ["i-04e4e826836f051a2", "i-0e3114c3025f0d23a"]

    # Start by logging the start of the process
    log_output("Starting verification of authorized_keys and sudoers for instances...\n", log_file)

    for instance_id, details in instances.items():
        if instance_id in excluded_instances:
            log_output(f"Skipping Instance ID: {instance_id}\n", log_file)
            continue  # Skip this instance

        private_ip = details['Private IP']
        instance_name = details['Name']
        log_output(f"\nChecking authorized_keys for Instance ID: {instance_id}, Name: {instance_name}, IP: {private_ip}", log_file)

        ssh = establish_ssh_connection(private_ip)
        if ssh:
            try:
                # Check authorized_keys
                stdin, stdout, stderr = ssh.exec_command('cat ~/.ssh/authorized_keys')
                authorized_keys_content = stdout.read().decode().strip()
                error_output = stderr.read().decode().strip()

                if authorized_keys_content:
                    log_output(f"Authorized keys for {instance_name}:\n{authorized_keys_content}", log_file)
                else:
                    log_output(f"No authorized keys found for {instance_name}.", log_file)

                if error_output:
                    log_output(f"Error while checking authorized_keys on {instance_name}: {error_output}", log_file)
            except Exception as e:
                log_output(f"Error checking authorized_keys for {private_ip}: {e}", log_file)

        log_output(f"\nChecking /etc/sudoers.d for Instance ID: {instance_id}, Name: {instance_name}, IP: {private_ip}", log_file)
        if ssh:
            try:
                # List files in /etc/sudoers.d
                stdin, stdout, stderr = ssh.exec_command('sudo ls -1 /etc/sudoers.d')
                files_in_sudoers_d = stdout.read().decode().strip().split("\n")
                error_output = stderr.read().decode().strip()

                if files_in_sudoers_d and files_in_sudoers_d[0]:  # Check if the list is not empty
                    log_output(f"Contents of /etc/sudoers.d for {instance_name}:\n", log_file)
                    
                    for file_name in files_in_sudoers_d:
                        log_output(f"--- {file_name} ---", log_file)
                        # Read and print the content of each file
                        stdin, stdout, stderr = ssh.exec_command(f'sudo cat /etc/sudoers.d/{file_name}')
                        file_content = stdout.read().decode().strip()
                        error_output = stderr.read().decode().strip()

                        if file_content:
                            log_output(file_content + "\n", log_file)  # Log file content
                        else:
                            log_output(f"File {file_name} is empty.\n", log_file)

                        if error_output:
                            log_output(f"Error while reading {file_name} on {instance_name}: {error_output}", log_file)
                else:
                    log_output(f"No files found in /etc/sudoers.d for {instance_name}.", log_file)

                if error_output:
                    log_output(f"Error while listing files in /etc/sudoers.d on {instance_name}: {error_output}", log_file)
            except Exception as e:
                log_output(f"Error checking /etc/sudoers.d for {private_ip}: {e}", log_file)
            finally:
                ssh.close()

    log_output("\nVerification completed.\n", log_file)
