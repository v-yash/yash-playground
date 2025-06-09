import boto3

def fetch_instances_info():
    ec2_client = boto3.client('ec2', region_name='ap-south-1')

    response = ec2_client.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )

    instances_dict = {}

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            private_ip = instance.get('PrivateIpAddress', 'N/A')
            name = 'N/A'

            # Extract 'Name' tag
            for tag in instance.get('Tags', []):
                if tag['Key'] == 'Name':
                    name = tag['Value']
                    break

            # Add instance info to dictionary
            instances_dict[instance_id] = {
                'Private IP': private_ip,
                'Name': name
            }

    return instances_dict

if __name__ == '__main__':
    # Test script independently
    data = fetch_instances_info()
    print(data)
