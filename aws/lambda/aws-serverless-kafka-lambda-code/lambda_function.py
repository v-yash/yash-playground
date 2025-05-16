import json
from kafka_producer import produce_message
from create_topic import create_topic

def lambda_handler(event, context):
    action = event.get("action", "produce")

    if action == "create":
        create_topic()
        return {
            "statusCode": 200,
            "body": json.dumps("Topic creation attempted.")
        }
    else:
        message = event.get("message", {"msg": "Hello from Lambda!"})
        produce_message(message)
        return {
            "statusCode": 200,
            "body": json.dumps("Message sent to Kafka.")
        }
