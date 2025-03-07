import json
import boto3
import logging

# Configure logging
logging.basicConfig(filename="python/logs/host_endpoint_secrets_update_log.txt",
                    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

AWS_REGION = "ap-southeast-1"

# Mapping of old to new RDS endpoints
RDS_ENDPOINT_MAPPING = {
    "crs-writer": {
        "old": "old host",
        "new": "new host"
    },
    "rms-writer": {
        "old": "old host",
        "new": "new host"
    }
}

def log_message(message):
    """Log message to file and print it."""
    logging.info(message)
    print(message)

def get_secrets(client):
    """Retrieve all secrets that contain 'postgres' in their name."""
    secrets_to_update = []
    next_token = None
    
    while True:
        try:
            params = {"MaxResults": 100, "SortOrder": 'asc'}
            if next_token:
                params["NextToken"] = next_token

            response = client.list_secrets(**params)
            
            for secret in response.get('SecretList', []):
                secret_name = secret.get("Name", "")
                
                if "postgres" in secret_name:
                    try:
                        retrieved_secret = client.get_secret_value(SecretId=secret["ARN"])
                        secret_value = json.loads(retrieved_secret['SecretString'])
                        secrets_to_update.append((secret, secret_value))
                    except Exception as e:
                        log_message(f"Error retrieving secret {secret_name}: {e}")
            
            next_token = response.get("NextToken")
            if not next_token:
                break
        except Exception as e:
            log_message(f"Error listing secrets: {e}")
            break
    
    return secrets_to_update

def update_secrets(client, secrets_to_update):
    """Update secrets' rds_host_endpoint if conditions are met."""
    for secret, secret_value in secrets_to_update:
        secret_name = secret.get("Name", "Unknown")
        host = secret_value.get("host")
        rds_host_endpoint = secret_value.get("rds_host_endpoint")
        
        if not host or not rds_host_endpoint:
            log_message(f"Skipping {secret_name}: Missing required keys 'host' or 'rds_host_endpoint'")
            continue
        
        if host in RDS_ENDPOINT_MAPPING and rds_host_endpoint == RDS_ENDPOINT_MAPPING[host]["old"]:
            new_rds_endpoint = RDS_ENDPOINT_MAPPING[host]["new"]
            log_message(f"Updating {secret_name}: Old RDS Endpoint: {rds_host_endpoint} => New RDS Endpoint: {new_rds_endpoint}")
            
            # Update secret
            secret_value["rds_host_endpoint"] = new_rds_endpoint
            try:
                client.put_secret_value(
                    SecretId=secret["ARN"],
                    SecretString=json.dumps(secret_value)
                )
                log_message(f"Successfully updated {secret_name}.")
            except Exception as e:
                log_message(f"Error updating {secret_name}: {e}")

def main():
    client = boto3.client("secretsmanager", region_name=AWS_REGION)
    secrets_to_update = get_secrets(client)
    update_secrets(client, secrets_to_update)
    log_message("Update complete.")

if __name__ == "__main__":
    main()
