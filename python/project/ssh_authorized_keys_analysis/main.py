from get_ec2_ip import fetch_instances_info
from verify_authorized_keys_sudoers import verify_authorized_keys_sudoers

def main():
    # Step 1: Fetch EC2 instance information
    print("Fetching EC2 instance information...")
    instances_info = fetch_instances_info()

    if not instances_info:
        print("No running instances found.")
        return

    # Step 2: Verify authorized keys
    print("Verifying authorized keys and sudoers on instances...")
    verify_authorized_keys_sudoers(instances_info)

if __name__ == '__main__':
    main()
