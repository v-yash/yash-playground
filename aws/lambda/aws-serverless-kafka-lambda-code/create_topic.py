import os
import boto3
from kafka.admin import KafkaAdminClient, NewTopic
from msk_token_provider import MSKTokenProvider

def create_topic():
    bootstrap_servers = os.environ["KAFKA_BOOTSTRAP_SERVERS"].split(",")
    topic_name = os.environ.get("TOPIC_NAME", "test-topic")
    partitions = int(os.environ.get("PARTITIONS", 1)) 
    
    admin_client = KafkaAdminClient(
        bootstrap_servers=bootstrap_servers,
        security_protocol="SASL_SSL",
        sasl_mechanism="OAUTHBEARER",
        sasl_oauth_token_provider=MSKTokenProvider(),
        client_id="lambda-admin"
    )

    topic = NewTopic(
        name=topic_name,
        num_partitions=partitions,
        replication_factor=1
    )

    try:
        admin_client.create_topics([topic])
        print(f"✅ Topic '{topic_name}' created successfully.")
    except Exception as e:
        print(f"⚠️ Topic creation failed: {e}")
    finally:
        admin_client.close()