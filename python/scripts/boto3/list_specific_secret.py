#import json
import sys
import boto3

def get_secrets(secret_value, region):

    client = boto3.client('secretsmanager', region_name=region)
    secrets = client.list_secrets(
        MaxResults=100,
        SortOrder='asc'
    )
    next_token = True
    total = 0
    found = 0
    while next_token:
        total += len(secrets['SecretList'])
        #print(secrets)
        for secret in secrets['SecretList']:
            try:
                retreived_secret = client.get_secret_value(SecretId=secret["ARN"])
                #print(retreived_secret)
                retreived_secret_value = retreived_secret['Name']
                # print(f'{secret["Name"]} ==> {type(retreived_secret_value)}')
                if secret_value in retreived_secret_value:
                    print(f'{secret["Name"]} ==> {retreived_secret["SecretString"]}')
                    #print(f'{secret["Name"]}')
                    found += 1
                    #print("------------------------------------------------------------------------------------------------------")
            except Exception as e:
                print(e,secret["ARN"])

        if "NextToken" in secrets:
            next_token = secrets["NextToken"]
        else:
            break

        secrets = client.list_secrets(
            NextToken=next_token,
            MaxResults=100,
            SortOrder='asc'
        )
    print(f'Total :{total}')
    print(f'Found :{found}')

stdoutOrigin=sys.stdout 
sys.stdout = open("python/logs/list_specific_secret_backup.txt", "w")
get_secrets("postgres",'ap-southeast-1')
sys.stdout.close()
sys.stdout=stdoutOrigin