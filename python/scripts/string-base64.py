import json
import base64

def get_base64_encoded_json():
    # Collecting input for each key
    username = input("Enter username: ")
    password = input("Enter password: ")
    # host = input("Enter host: ")
    # port = input("Enter port (default 5432): ") or "5432"
    # dbname = input("Enter database name: ")
    # schema_name = input("Enter schema name (default 'public'): ") or "public"
    # rds_host_endpoint = input("Enter RDS host endpoint: ")

    # Constructing the JSON object
    data = {
        "username": username,
        "password": password,
        # "host": host,
        # "port": port,
        # "dbname": dbname,
        # "schema_name": schema_name,
        # "rds_host_endpoint": rds_host_endpoint
    }

    # Convert the dictionary to a JSON string
    json_string = json.dumps(data)

    # Encode the JSON string to Base64
    base64_encoded = base64.b64encode(json_string.encode("utf-8")).decode("utf-8")

    return base64_encoded

if __name__ == "__main__":
    # Get the Base64-encoded string and print it
    base64_string = get_base64_encoded_json()
    print("\nBase64 Encoded String:")
    print(base64_string)