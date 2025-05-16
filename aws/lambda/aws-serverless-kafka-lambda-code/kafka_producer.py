import json
import os
from kafka import KafkaProducer
from msk_token_provider import MSKTokenProvider

def produce_message(message: dict):
    bootstrap_servers = os.environ["KAFKA_BOOTSTRAP_SERVERS"].split(",")
    topic_name = os.environ.get("TOPIC_NAME", "test-topic")

    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        security_protocol="SASL_SSL",
        sasl_mechanism="OAUTHBEARER",
        sasl_oauth_token_provider=MSKTokenProvider(), 
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    producer.send(topic_name, message)
    producer.flush()
    producer.close()
    print(f"✅ Message sent to '{topic_name}'.")